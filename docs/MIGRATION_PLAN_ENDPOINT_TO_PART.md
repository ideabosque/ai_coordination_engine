# Migration Plan: endpoint_id → partition_key (AI Coordination Engine)

> **Migration Status**: Planning Phase
> **Last Updated**: 2025-12-11
> **Target Completion**: TBD
> **Risk Level**: Medium-High (Breaking Change to Coordination Primary Key)

---

## Executive Summary

### What's Changing?

Migrate from single `endpoint_id` to composite `partition_key` pattern to enable multi-tenancy support:

**Current State:**
```
endpoint_id = "acme-corp-prod"  (dual purpose)
```

**Target State:**
```
endpoint_id = "aws-prod-us-east-1"  (platform)
part_id = "acme-corp"               (business)
partition_key = "aws-prod-us-east-1#acme-corp"  (composite, assembled in main.py)
```

### Key Principles

**Single Point of Assembly:**
- `partition_key` is assembled **ONCE** in `main.py` (`ai_coordination_graphql` function)
- Format: `"{endpoint_id}#{part_id}"`
- Passed to all downstream code via context

**Denormalized Attributes + LSI:**
- Store `partition_key` as hash key (affects CoordinationModel)
- Store `endpoint_id` and `part_id` as separate attributes (denormalized)
- Create Local Secondary Indexes (LSI) on `endpoint_id` and `part_id`
- Benefits: Query flexibility, strongly consistent reads, no extra write capacity

**Minimal Code Changes:**
- `/models`: Change function signatures from `endpoint_id` to `partition_key`
- `/queries`: Extract `partition_key` from context instead of `endpoint_id`
- `/mutations`: Extract `partition_key` from context instead of `endpoint_id`
- `/types`: Extract `partition_key` from context instead of `endpoint_id`
- No new utility modules needed

**Backward Compatibility:**
- If `part_id` not provided, defaults to `endpoint_id`
- Fallback logic during transition period

---

## 1. Main Entry Point Changes

### 1.1 main.py - Partition Key Assembly

**File:** `ai_coordination_engine/main.py`

```python
class AICoordinationEngine(Graphql):
    def ai_coordination_graphql(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters before diving in!
        ##<--Testing Data-->##
        if params.get("connection_id") is None:
            params["connection_id"] = self.setting.get("connection_id")
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##

        # NEW: Extract part_id and assemble partition_key
        endpoint_id = params.get("endpoint_id")
        part_id = params.get("part_id")  # From JWT, header, or request body

        # Backward compatibility: if part_id not provided, use endpoint_id
        if not part_id:
            part_id = endpoint_id

        # Assemble composite partition_key ONCE here
        partition_key = f"{endpoint_id}#{part_id}"
        params["partition_key"] = partition_key  # Add to params
        params["endpoint_id"] = endpoint_id       # Keep for backward compatibility
        params["part_id"] = part_id               # Add for handler usage

        schema = Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )
        return self.execute(schema, **params)  # partition_key passed to context
```

**Changes:**
- Extract `part_id` from params
- Assemble `partition_key = f"{endpoint_id}#{part_id}"`
- Add `partition_key`, `endpoint_id`, and `part_id` to params
- Pass to `self.execute()`

---

## 2. Model Changes

### 2.1 Current State Analysis

**Models in ai_coordination_engine:**

| Model | Current Hash Key | Current Range Key | Has endpoint_id | Priority |
|-------|------------------|-------------------|-----------------|----------|
| CoordinationModel | `endpoint_id` | `coordination_uuid` | Yes (hash key) | **CRITICAL** |
| TaskModel | `coordination_uuid` | `task_uuid` | Yes (denormalized) | HIGH |
| SessionModel | `coordination_uuid` | `session_uuid` | Yes (denormalized) | HIGH |
| SessionAgentModel | `session_uuid` | `session_agent_uuid` | No | MEDIUM |
| SessionRunModel | `session_uuid` | `run_uuid` | Yes (denormalized) | HIGH |
| TaskScheduleModel | `task_uuid` | `schedule_uuid` | Yes (denormalized) | HIGH |

### 2.2 CoordinationModel Schema Changes (CRITICAL)

**File:** `ai_coordination_engine/models/coordination.py`

**Before:**
```python
class CoordinationModel(BaseModel):
    class Meta:
        table_name = "aace-coordinations"

    endpoint_id = UnicodeAttribute(hash_key=True)
    coordination_uuid = UnicodeAttribute(range_key=True)
    # ... other attributes
```

**After:**
```python
class EndpointIdIndex(LocalSecondaryIndex):
    """LSI for querying by endpoint_id within same partition."""
    class Meta:
        index_name = "endpoint_id-index"
        projection = AllProjection()

    partition_key = UnicodeAttribute(hash_key=True)
    endpoint_id = UnicodeAttribute(range_key=True)


class PartIdIndex(LocalSecondaryIndex):
    """LSI for querying by part_id within same partition."""
    class Meta:
        index_name = "part_id-index"
        projection = AllProjection()

    partition_key = UnicodeAttribute(hash_key=True)
    part_id = UnicodeAttribute(range_key=True)


class CoordinationModel(BaseModel):
    class Meta:
        table_name = "aace-coordinations"

    # Primary Key (CHANGED)
    partition_key = UnicodeAttribute(hash_key=True)  # Format: "endpoint_id#part_id"
    coordination_uuid = UnicodeAttribute(range_key=True)

    # Denormalized attributes for indexing (NEW)
    endpoint_id = UnicodeAttribute()  # Platform partition
    part_id = UnicodeAttribute()      # Business partition

    # Other attributes
    coordination_name = UnicodeAttribute()
    coordination_description = UnicodeAttribute(null=True)
    agents = ListAttribute(default=list)
    # ... other fields

    # Indexes (NEW)
    endpoint_id_index = EndpointIdIndex()
    part_id_index = PartIdIndex()
```

**Impact:** This is a **BREAKING CHANGE** requiring table recreation or migration script.

### 2.3 Other Models Schema Changes

**Models requiring denormalized endpoint_id/part_id:**
- TaskModel
- SessionModel
- SessionRunModel
- TaskScheduleModel
- SessionAgentModel (optional, inherits from Session)

**Pattern for each:**
```python
# Add to each model class
partition_key = UnicodeAttribute()  # Store for queries
endpoint_id = UnicodeAttribute()    # Denormalized
part_id = UnicodeAttribute()        # Denormalized (NEW)
```

**Note:** These models do NOT change their hash keys, only add denormalized fields.

### 2.4 Function Signature Changes

**Before:**
```python
def get_coordination(logger, endpoint_id: str, coordination_uuid: str):
    coordination = CoordinationModel.get(endpoint_id, coordination_uuid)
    return coordination
```

**After:**
```python
def get_coordination(logger, partition_key: str, coordination_uuid: str):
    coordination = CoordinationModel.get(partition_key, coordination_uuid)
    return coordination
```

**Change:** Replace `endpoint_id` parameter with `partition_key`

**When creating/updating records:**
```python
def insert_update_coordination(logger, partition_key: str, **kwargs):
    # Parse partition_key to extract components
    endpoint_id, part_id = partition_key.split('#', 1)

    coordination = CoordinationModel()
    coordination.partition_key = partition_key
    coordination.endpoint_id = endpoint_id     # Denormalized
    coordination.part_id = part_id             # Denormalized
    coordination.coordination_uuid = kwargs.get("coordination_uuid") or str(uuid.uuid4())
    # ... set other attributes
    coordination.save()
    return coordination
```

### 2.5 Models Requiring Function Updates

Apply signature changes to all functions in these 6 model files:

1. **coordination.py** - `get_coordination`, `insert_update_coordination`, `delete_coordination`, `resolve_coordination`, `resolve_coordination_list`
2. **task.py** - `get_task`, `insert_update_task`, `delete_task`, `resolve_task`, `resolve_task_list`
3. **session.py** - `get_session`, `insert_update_session`, `delete_session`, `resolve_session`, `resolve_session_list`
4. **session_agent.py** - `get_session_agent`, `insert_update_session_agent`, `delete_session_agent`, `resolve_session_agent`, `resolve_session_agent_list`
5. **session_run.py** - `get_session_run`, `insert_update_session_run`, `delete_session_run`, `resolve_session_run`, `resolve_session_run_list`
6. **task_schedule.py** - `get_task_schedule`, `insert_update_task_schedule`, `delete_task_schedule`, `resolve_task_schedule`, `resolve_task_schedule_list`

---

## 3. Query Changes (Minimal)

### 3.1 Extract partition_key from Context

**Before:**
```python
def resolve_coordination(info: ResolveInfo, **kwargs):
    logger = info.context.get("logger")
    endpoint_id = info.context.get("endpoint_id")
    coordination_uuid = kwargs.get("coordination_uuid")

    coordination = get_coordination(logger, endpoint_id, coordination_uuid)
    return CoordinationType(**coordination.attribute_values) if coordination else None
```

**After:**
```python
def resolve_coordination(info: ResolveInfo, **kwargs):
    logger = info.context.get("logger")
    partition_key = info.context.get("partition_key")  # CHANGED
    coordination_uuid = kwargs.get("coordination_uuid")

    coordination = get_coordination(logger, partition_key, coordination_uuid)  # CHANGED
    return CoordinationType(**coordination.attribute_values) if coordination else None
```

**Change:** Replace `endpoint_id` with `partition_key` from context

### 3.2 Query Files Requiring Updates

Apply the same pattern to all 6 query files:

1. `/queries/coordination.py` - `resolve_coordination`, `resolve_coordination_list`
2. `/queries/task.py` - `resolve_task`, `resolve_task_list`
3. `/queries/session.py` - `resolve_session`, `resolve_session_list`
4. `/queries/session_agent.py` - `resolve_session_agent`, `resolve_session_agent_list`
5. `/queries/session_run.py` - `resolve_session_run`, `resolve_session_run_list`
6. `/queries/task_schedule.py` - `resolve_task_schedule`, `resolve_task_schedule_list`

**Note:** All `resolve_*_list` functions already have caching applied (completed earlier).

---

## 4. Mutation Changes (Minimal)

### 4.1 Mutations Pass info Object Directly

**Important:** Mutations in ai_coordination_engine pass the entire `info` object to model functions, NOT extracted parameters.

**Mutation Structure (No Changes Required):**
```python
class InsertUpdateCoordination(Mutation):
    coordination = Field(CoordinationType)

    class Arguments:
        coordination_uuid = String(required=False)
        coordination_name = String(required=False)
        # ... other arguments

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateCoordination":
        try:
            coordination = insert_update_coordination(info, **kwargs)  # Passes info directly
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateCoordination(coordination=coordination)
```

**No changes needed in mutation files** - they already pass `info` to model functions.

**Changes Required in Model Functions:**

**Before:**
```python
@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
    count_funct=get_coordination_count,
    type_funct=get_coordination_type,
)
def insert_update_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    endpoint_id = kwargs.get("endpoint_id")  # OLD: extracted from kwargs
    coordination_uuid = kwargs.get("coordination_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "agents": [],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        # ... set other cols

        CoordinationModel(
            endpoint_id,  # OLD: passed as hash key
            coordination_uuid,
            **cols,
        ).save()
        return
```

**After:**
```python
@insert_update_decorator(
    keys={
        "hash_key": "partition_key",  # CHANGED
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
    count_funct=get_coordination_count,
    type_funct=get_coordination_type,
)
def insert_update_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    partition_key = info.context.get("partition_key")  # CHANGED: extract from context
    endpoint_id, part_id = partition_key.split('#', 1)  # NEW: parse components
    coordination_uuid = kwargs.get("coordination_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "agents": [],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        # ... set other cols

        coordination = CoordinationModel(
            partition_key,  # CHANGED: use partition_key as hash key
            coordination_uuid,
            **cols,
        )
        coordination.endpoint_id = endpoint_id  # NEW: set denormalized
        coordination.part_id = part_id          # NEW: set denormalized
        coordination.save()
        return
```

**Change:**
1. Update decorator's `hash_key` from `"endpoint_id"` to `"partition_key"`
2. Extract `partition_key` from `info.context` instead of `kwargs`
3. Parse `partition_key` to get `endpoint_id` and `part_id`
4. Set denormalized `endpoint_id` and `part_id` fields on model before save

### 4.2 Model Function Updates Required

**NO changes needed in mutation files** (`/mutations/*.py`) - they already pass `info` correctly.

**Changes required in model files** (`/models/*.py`):

1. **coordination.py**
   - Update `@insert_update_decorator` hash_key to `"partition_key"`
   - Extract `partition_key` from `info.context` in `insert_update_coordination`
   - Parse and set denormalized `endpoint_id` and `part_id`
   - Update `@delete_decorator` hash_key to `"partition_key"`
   - Extract `partition_key` from `info.context` in `delete_coordination`

2. **task.py**
   - Update `@insert_update_decorator` to handle `partition_key` in denormalized fields
   - Extract `partition_key` from `info.context` and set on model
   - Update `@delete_decorator` similarly

3. **session.py**
   - Update `@insert_update_decorator` to handle `partition_key` in denormalized fields
   - Extract `partition_key` from `info.context` and set on model
   - Update `@delete_decorator` similarly

4. **session_agent.py**
   - Update `@insert_update_decorator` to handle `partition_key` in denormalized fields
   - Extract `partition_key` from `info.context` and set on model
   - Update `@delete_decorator` similarly

5. **session_run.py**
   - Update `@insert_update_decorator` to handle `partition_key` in denormalized fields
   - Extract `partition_key` from `info.context` and set on model
   - Update `@delete_decorator` similarly

6. **task_schedule.py**
   - Update `@insert_update_decorator` to handle `partition_key` in denormalized fields
   - Extract `partition_key` from `info.context` and set on model
   - Update `@delete_decorator` similarly

---

## 5. Type Changes (Minimal)

### 5.1 Nested Resolvers

**Before:**
```python
class SessionType(graphene.ObjectType):
    def resolve_coordination(self, info: ResolveInfo):
        loaders = get_loaders(info.context)
        endpoint_id = info.context.get("endpoint_id")

        coord_key = (endpoint_id, self.coordination_uuid)
        return loaders.coordination_loader.load(coord_key)
```

**After:**
```python
class SessionType(graphene.ObjectType):
    def resolve_coordination(self, info: ResolveInfo):
        loaders = get_loaders(info.context)
        partition_key = info.context.get("partition_key")  # CHANGED

        coord_key = (partition_key, self.coordination_uuid)  # CHANGED
        return loaders.coordination_loader.load(coord_key)
```

**Change:** Replace `endpoint_id` with `partition_key` from context

### 5.2 Type Files Requiring Updates

Apply the same pattern to all 6 type files:

1. `/types/coordination.py` - CoordinationType (if nested resolvers exist)
2. `/types/task.py` - TaskType
3. `/types/session.py` - SessionType
4. `/types/session_agent.py` - SessionAgentType
5. `/types/session_run.py` - SessionRunType
6. `/types/task_schedule.py` - TaskScheduleType

---

## 6. Batch Loader Changes (Minimal)

### 6.1 Loader Key Format

**Before:**
```python
class CoordinationLoader(SafeDataLoader):
    def batch_load_fn(self, keys: List[Tuple[str, str]]):
        # keys = [(endpoint_id, coordination_uuid), ...]
        for endpoint_id, coordination_uuid in keys:
            coordination = CoordinationModel.get(endpoint_id, coordination_uuid)
```

**After:**
```python
class CoordinationLoader(SafeDataLoader):
    def batch_load_fn(self, keys: List[Tuple[str, str]]):
        # keys = [(partition_key, coordination_uuid), ...]
        for partition_key, coordination_uuid in keys:
            coordination = CoordinationModel.get(partition_key, coordination_uuid)
```

**Change:** Replace `endpoint_id` with `partition_key` in key tuples

### 6.2 Loader Files Requiring Updates

Apply the same pattern to all 7 batch loader files:

1. `/models/batch_loaders/coordination_loader.py`
2. `/models/batch_loaders/task_loader.py`
3. `/models/batch_loaders/session_loader.py`
4. `/models/batch_loaders/session_agent_loader.py`
5. `/models/batch_loaders/session_run_loader.py`
6. `/models/batch_loaders/session_agents_by_session_loader.py`
7. `/models/batch_loaders/session_runs_by_session_loader.py`

---

## 7. Handler Changes

### 7.1 OperationHub and ProcedureHub Updates

**Location:** `ai_coordination_engine/handlers/operation_hub/` and `ai_coordination_engine/handlers/procedure_hub/`

**Pattern:**
```python
# Before
endpoint_id = info.context.get("endpoint_id")

# After
partition_key = info.context.get("partition_key")
endpoint_id = info.context.get("endpoint_id")  # Still available if needed
part_id = info.context.get("part_id")          # New field
```

**Files to Review:**
1. `handlers/operation_hub/operation_hub.py`
2. `handlers/operation_hub/operation_hub_listener.py`
3. `handlers/procedure_hub/procedure_hub.py`
4. `handlers/procedure_hub/session_agent.py`
5. `handlers/procedure_hub/action_function.py`
6. `handlers/procedure_hub/user_in_the_loop.py`
7. `handlers/procedure_hub/procedure_hub_listener.py`

**Search for:** All occurrences of `endpoint_id` extraction and usage

---

## 8. Cache Configuration Updates

### 8.1 Config.py Entity Relationships

**File:** `ai_coordination_engine/handlers/config.py`

**Current:**
```python
CACHE_RELATIONS = {
    "Coordination": ["Session", "Task", "TaskSchedule"],
    "Session": ["SessionAgent"],
    "SessionAgent": ["SessionRun"],
    "Task": ["Session"],
}
```

**No changes required** - relationships remain the same.

### 8.2 Cache Key Pattern Update

**Before:**
```python
# Cache keys use endpoint_id
cache_key = f"{endpoint_id}:{coordination_uuid}"
```

**After:**
```python
# Cache keys use partition_key
cache_key = f"{partition_key}:{coordination_uuid}"
```

**Impact:** Cache invalidation required during migration.

---

## 9. Migration Phases

### Phase 1: Code Changes (Week 1-2)
- [ ] Update `main.py` to assemble `partition_key`
- [ ] Update CoordinationModel schema (hash key rename)
- [ ] Add denormalized `endpoint_id`, `part_id` to all models
- [ ] Update model functions (insert_update_* and delete_* functions)
- [ ] Update queries (context extraction)
- [ ] Update types (nested resolvers)
- [ ] Update batch loaders (key format)
- [ ] Update handlers (operation_hub, procedure_hub)

### Phase 2: Data Migration (Week 3-4)
- [ ] Create migration script for CoordinationModel
- [ ] Backfill `partition_key` for existing records
- [ ] Backfill `part_id` for all models
- [ ] Validate data integrity
- [ ] Test queries with new indexes

### Phase 3: Testing (Week 5-6)
- [ ] Unit tests for partition_key assembly
- [ ] Unit tests for model CRUD operations
- [ ] Integration tests for GraphQL queries/mutations
- [ ] Load tests with LSI queries
- [ ] Cache invalidation tests

### Phase 4: Deployment (Week 7-8)
- [ ] Deploy to dev environment
- [ ] Monitor metrics and errors
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Deploy to production (staged rollout)

---

## 10. File Change Summary

### Files Requiring Changes

**Main Entry Point (1 file):**
- `main.py` - Add partition_key assembly

**Models (6 files):**
- `models/coordination.py` - Change hash key + signatures
- `models/task.py` - Add denormalized fields + signatures
- `models/session.py` - Add denormalized fields + signatures
- `models/session_agent.py` - Add denormalized fields + signatures
- `models/session_run.py` - Add denormalized fields + signatures
- `models/task_schedule.py` - Add denormalized fields + signatures

**Queries (6 files):**
- `queries/coordination.py`
- `queries/task.py`
- `queries/session.py`
- `queries/session_agent.py`
- `queries/session_run.py`
- `queries/task_schedule.py`

**Mutations (0 files - NO CHANGES NEEDED):**
- Mutation files already pass `info` object correctly to model functions
- All mutation changes are handled in the model layer

**Types (6 files):**
- `types/coordination.py`
- `types/task.py`
- `types/session.py`
- `types/session_agent.py`
- `types/session_run.py`
- `types/task_schedule.py`

**Batch Loaders (7 files):**
- `models/batch_loaders/coordination_loader.py`
- `models/batch_loaders/task_loader.py`
- `models/batch_loaders/session_loader.py`
- `models/batch_loaders/session_agent_loader.py`
- `models/batch_loaders/session_run_loader.py`
- `models/batch_loaders/session_agents_by_session_loader.py`
- `models/batch_loaders/session_runs_by_session_loader.py`

**Handlers (7+ files):**
- `handlers/operation_hub/operation_hub.py`
- `handlers/operation_hub/operation_hub_listener.py`
- `handlers/procedure_hub/procedure_hub.py`
- `handlers/procedure_hub/session_agent.py`
- `handlers/procedure_hub/action_function.py`
- `handlers/procedure_hub/user_in_the_loop.py`
- `handlers/procedure_hub/procedure_hub_listener.py`

**Configuration (1 file):**
- `handlers/config.py` - Cache relationships (minor updates)

**Total: ~37 files** (6 mutation files do NOT need changes)

---

## 11. Testing Strategy

### Unit Tests

```python
def test_partition_key_assembly():
    engine = AICoordinationEngine(logger, **settings)
    params = {"endpoint_id": "aws-prod", "part_id": "acme-corp"}

    # Mock execute to capture params
    with patch.object(engine, 'execute') as mock_execute:
        engine.ai_coordination_graphql(**params)

        # Verify partition_key was assembled
        call_args = mock_execute.call_args
        assert call_args[1]["partition_key"] == "aws-prod#acme-corp"
        assert call_args[1]["endpoint_id"] == "aws-prod"
        assert call_args[1]["part_id"] == "acme-corp"
```

### Integration Tests

```python
def test_coordination_crud_with_partition_key():
    partition_key = "aws-prod#acme-corp"

    # Create
    coordination = insert_update_coordination(
        logger,
        partition_key,
        coordination_name="test-coordination"
    )
    assert coordination.partition_key == partition_key
    assert coordination.endpoint_id == "aws-prod"
    assert coordination.part_id == "acme-corp"

    # Read
    fetched = get_coordination(logger, partition_key, coordination.coordination_uuid)
    assert fetched.coordination_name == "test-coordination"

    # Delete
    result = delete_coordination(logger, partition_key, coordination.coordination_uuid)
    assert result is True
```

### GraphQL Query Tests

```python
def test_graphql_query_with_partition_key():
    query = """
    query {
        coordination(coordination_uuid: "test-uuid") {
            coordination_name
            endpoint_id
            part_id
        }
    }
    """

    context = {
        "logger": logger,
        "partition_key": "aws-prod#acme-corp",
        "endpoint_id": "aws-prod",
        "part_id": "acme-corp"
    }

    result = schema.execute(query, context=context)
    assert result.errors is None
    assert result.data["coordination"]["endpoint_id"] == "aws-prod"
```

---

## 12. Data Migration Script

### Migration Script Template

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migration script: endpoint_id → partition_key for ai_coordination_engine
"""

import logging
from typing import List
from ai_coordination_engine.models.coordination import CoordinationModel

logger = logging.getLogger(__name__)


def migrate_coordination_table():
    """
    Migrate CoordinationModel from endpoint_id to partition_key.

    Steps:
    1. Scan all existing records
    2. For each record:
       - Read current endpoint_id (old hash key)
       - Create new record with partition_key = f"{endpoint_id}#{endpoint_id}" (backward compat)
       - Set denormalized endpoint_id and part_id fields
       - Save to new table
    3. Validate migration
    """
    logger.info("Starting CoordinationModel migration...")

    migrated_count = 0
    error_count = 0

    # Scan all records from old table
    for old_coordination in CoordinationModel.scan():
        try:
            # Extract old endpoint_id (was hash key)
            old_endpoint_id = old_coordination.endpoint_id
            coordination_uuid = old_coordination.coordination_uuid

            # For backward compatibility, use endpoint_id as part_id initially
            partition_key = f"{old_endpoint_id}#{old_endpoint_id}"

            # Create new record with partition_key
            new_coordination = CoordinationModel()
            new_coordination.partition_key = partition_key
            new_coordination.coordination_uuid = coordination_uuid
            new_coordination.endpoint_id = old_endpoint_id  # Denormalized
            new_coordination.part_id = old_endpoint_id      # Denormalized (same as endpoint_id)

            # Copy all other attributes
            new_coordination.coordination_name = old_coordination.coordination_name
            new_coordination.coordination_description = old_coordination.coordination_description
            new_coordination.agents = old_coordination.agents
            # ... copy other fields

            new_coordination.save()
            migrated_count += 1

            if migrated_count % 100 == 0:
                logger.info(f"Migrated {migrated_count} coordinations...")

        except Exception as e:
            logger.error(f"Failed to migrate coordination {coordination_uuid}: {e}")
            error_count += 1

    logger.info(f"Migration complete: {migrated_count} migrated, {error_count} errors")
    return migrated_count, error_count


def validate_migration():
    """Validate that all records have partition_key and denormalized fields."""
    logger.info("Validating migration...")

    validation_errors = []

    for coordination in CoordinationModel.scan():
        if not coordination.partition_key:
            validation_errors.append(f"Missing partition_key: {coordination.coordination_uuid}")
        if not coordination.endpoint_id:
            validation_errors.append(f"Missing endpoint_id: {coordination.coordination_uuid}")
        if not coordination.part_id:
            validation_errors.append(f"Missing part_id: {coordination.coordination_uuid}")

    if validation_errors:
        logger.error(f"Validation failed with {len(validation_errors)} errors:")
        for error in validation_errors[:10]:  # Show first 10
            logger.error(f"  - {error}")
        return False

    logger.info("Validation successful!")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Run migration
    migrated, errors = migrate_coordination_table()

    # Validate
    if validate_migration():
        logger.info("Migration and validation completed successfully!")
    else:
        logger.error("Migration validation failed!")
```

### Migration for Other Models

For Task, Session, SessionRun, TaskSchedule, SessionAgent:
- These models DO NOT change their hash keys
- Only need to add `partition_key`, `endpoint_id`, `part_id` as denormalized attributes
- Simpler migration: update records in-place

```python
def migrate_task_table():
    """Add partition_key, part_id to existing Task records."""
    for task in TaskModel.scan():
        # Task already has endpoint_id as denormalized attribute
        endpoint_id = task.endpoint_id

        # For backward compatibility, use endpoint_id as part_id
        task.partition_key = f"{endpoint_id}#{endpoint_id}"
        task.part_id = endpoint_id

        task.save()
```

---

## 13. Rollback Plan

### Immediate Rollback

1. **Code Rollback:**
   - Revert deployment to previous version
   - Restore old schema definitions
   - Clear cache to prevent stale data

2. **Data Rollback:**
   - If migration was destructive, restore from DynamoDB backup
   - If migration was additive (new table), point code to old table

3. **Monitoring:**
   - Monitor error rates
   - Check query latencies
   - Verify data integrity

### Rollback Checklist

- [ ] Stop new deployments
- [ ] Revert code to previous version
- [ ] Clear application cache
- [ ] Verify old table is still accessible
- [ ] Test queries against old schema
- [ ] Notify stakeholders
- [ ] Document rollback reason

---

## 14. Risk Assessment

### High Risk Areas

1. **CoordinationModel Primary Key Change**
   - **Risk:** Breaking change to hash key
   - **Mitigation:** Create new table, migrate data, validate, then switch
   - **Rollback:** Keep old table for 30 days

2. **Cache Invalidation**
   - **Risk:** Stale cache with old keys
   - **Mitigation:** Full cache purge during deployment
   - **Rollback:** Clear cache again on rollback

3. **Batch Loader Key Format**
   - **Risk:** N+1 queries if keys mismatch
   - **Mitigation:** Unit tests for all loaders
   - **Rollback:** Revert code deployment

### Medium Risk Areas

1. **Context Extraction Changes**
   - **Risk:** Null partition_key if main.py fails to assemble
   - **Mitigation:** Backward compatibility fallback
   - **Rollback:** Logs will show null errors

2. **LSI Query Performance**
   - **Risk:** Slower queries than GSI
   - **Mitigation:** Load testing before production
   - **Rollback:** Revert schema changes

### Low Risk Areas

1. **Handler Updates**
   - **Risk:** Minor logic changes
   - **Mitigation:** Unit tests
   - **Rollback:** Code revert

---

## 15. Dependencies

### Upstream Dependencies

- **ai_agent_core_engine**: If this module is migrated first, follow the same pattern
- **silvaengine_dynamodb_base**: Ensure BaseModel supports partition_key pattern
- **silvaengine_utility**: Ensure caching supports new key format

### Downstream Dependencies

- **External Clients**: GraphQL clients should be unaffected (transparent change)
- **AI Agent Handlers**: May need updates if they query coordination data

---

## 16. Success Criteria

### Functional Requirements

- [ ] All 6 models support partition_key
- [ ] All queries return correct data with partition_key
- [ ] All mutations write data with partition_key + denormalized fields
- [ ] Batch loaders use partition_key tuples
- [ ] LSI queries return correct results

### Performance Requirements

- [ ] Query latency unchanged or improved
- [ ] Write latency unchanged
- [ ] Cache hit rate maintained
- [ ] No N+1 query regressions

### Data Integrity Requirements

- [ ] 100% of records have partition_key
- [ ] 100% of records have denormalized endpoint_id and part_id
- [ ] No data loss during migration
- [ ] All foreign key relationships intact

---

## 17. Document Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-11 | Initial migration plan for ai_coordination_engine based on ai_agent_core_engine pattern |

---

**End of Document**
