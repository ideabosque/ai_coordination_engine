# Phase 0: Entity Inventory — Dual-Backend Field Mapping

> Project: `ai_coordination_engine`
> Created: 2026-06-29
> Covers the 6 entities. All 6 tables have RLS policies (migration 0007).

## 1. Coordination (`ace-coordinations` → `ace_coordinations`)

| Field | DynamoDB Type | PostgreSQL Column | Notes |
| --- | --- | --- | --- |
| `partition_key` | UnicodeAttribute (hash) | String(128), PK | Tenant key |
| `coordination_uuid` | UnicodeAttribute (range) | UUID(as_uuid=True), PK | `uuid_generate_v4()` default |
| `endpoint_id` | UnicodeAttribute | String, NOT NULL | |
| `part_id` | UnicodeAttribute | String, NOT NULL | |
| `coordination_name` | UnicodeAttribute | String, NOT NULL | |
| `coordination_description` | UnicodeAttribute | Text | |
| `agents` | ListAttribute(of=MapAttribute) | JSONB | List of agent dicts |
| `updated_by` | UnicodeAttribute | String, NOT NULL | |
| `created_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |
| `updated_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |

Indexes: `(partition_key, updated_at)`

## 2. Session (`ace-sessions` → `ace_sessions`)

| Field | DynamoDB Type | PostgreSQL Column | Notes |
| --- | --- | --- | --- |
| `coordination_uuid` | UnicodeAttribute (hash) | UUID(as_uuid=True), PK | Non-partition-key hash |
| `session_uuid` | UnicodeAttribute (range) | UUID(as_uuid=True), PK | `uuid_generate_v4()` default |
| `partition_key` | UnicodeAttribute | String(128), NOT NULL | For RLS |
| `task_uuid` | UnicodeAttribute(null) | UUID(as_uuid=True), nullable | LSI range in DDB |
| `user_id` | UnicodeAttribute(null) | String, nullable | LSI range in DDB |
| `task_query` | UnicodeAttribute(null) | Text, nullable | |
| `input_files` | ListAttribute(of=MapAttribute) | JSONB | |
| `iteration_count` | NumberAttribute(default=0) | Integer | |
| `subtask_queries` | ListAttribute(of=MapAttribute) | JSONB | |
| `status` | UnicodeAttribute(default="initial") | String | |
| `logs` | UnicodeAttribute(null) | Text, nullable | |
| `updated_by` | UnicodeAttribute | String, NOT NULL | |
| `created_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |
| `updated_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |

Indexes: `(coordination_uuid, user_id)`, `(coordination_uuid, task_uuid)`, `(partition_key, updated_at)`

## 3. SessionAgent (`ace-session_agents` → `ace_session_agents`)

| Field | DynamoDB Type | PostgreSQL Column | Notes |
| --- | --- | --- | --- |
| `session_uuid` | UnicodeAttribute (hash) | UUID(as_uuid=True), PK | Non-partition-key hash |
| `session_agent_uuid` | UnicodeAttribute (range) | UUID(as_uuid=True), PK | `uuid_generate_v4()` default |
| `partition_key` | **— (not in DynamoDB)** | String(128), NOT NULL | **Added in PG for RLS**; populated from parent session |
| `coordination_uuid` | UnicodeAttribute | UUID(as_uuid=True), NOT NULL | |
| `agent_uuid` | UnicodeAttribute | String, NOT NULL | |
| `agent_action` | MapAttribute(null) | JSONB, nullable | GIN index for nested filtering |
| `user_input` | UnicodeAttribute(null) | Text, nullable | |
| `agent_input` | UnicodeAttribute(null) | Text, nullable | |
| `agent_output` | UnicodeAttribute(null) | Text, nullable | |
| `in_degree` | NumberAttribute(default=0) | Integer | |
| `state` | UnicodeAttribute(default="initial") | String | |
| `notes` | UnicodeAttribute(null) | Text, nullable | |
| `updated_by` | UnicodeAttribute | String, NOT NULL | |
| `created_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |
| `updated_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |

Indexes: `(session_uuid, updated_at)`, `(partition_key, updated_at)`, `(coordination_uuid)`, `(agent_uuid)`, GIN on `agent_action`

> **Note**: `partition_key` is **not present in the DynamoDB model** — it is added
> in PostgreSQL to enable uniform RLS across all 6 tables. It is populated from
> the parent session's `partition_key` on insert.

> **Note**: `agent_action` is a JSONB column with a GIN index
> (`ix_ace_session_agents_action_gin`) to support nested map filtering by
> `primary_path`, `user_in_the_loop`, and `predecessors`.

## 4. SessionRun (`ace-session_runs` → `ace_session_runs`)

| Field | DynamoDB Type | PostgreSQL Column | Notes |
| --- | --- | --- | --- |
| `session_uuid` | UnicodeAttribute (hash) | UUID(as_uuid=True), PK | Non-partition-key hash |
| `run_uuid` | UnicodeAttribute (range) | UUID(as_uuid=True), PK | `uuid_generate_v4()` default |
| `partition_key` | UnicodeAttribute(null) | String(128), nullable | Nullable in both backends; populated from parent session |
| `thread_uuid` | UnicodeAttribute | UUID(as_uuid=True), NOT NULL | LSI range in DDB |
| `agent_uuid` | UnicodeAttribute | String, NOT NULL | LSI range in DDB |
| `coordination_uuid` | UnicodeAttribute | UUID(as_uuid=True), NOT NULL | |
| `async_task_uuid` | UnicodeAttribute | String, NOT NULL | |
| `session_agent_uuid` | UnicodeAttribute(null) | UUID(as_uuid=True), nullable | |
| `updated_by` | UnicodeAttribute | String, NOT NULL | |
| `created_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |
| `updated_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |

Indexes: `(session_uuid, thread_uuid)`, `(session_uuid, agent_uuid)`, `(partition_key, updated_at)`, `(coordination_uuid)`

## 5. Task (`ace-tasks` → `ace_tasks`)

| Field | DynamoDB Type | PostgreSQL Column | Notes |
| --- | --- | --- | --- |
| `coordination_uuid` | UnicodeAttribute (hash) | UUID(as_uuid=True), PK | Non-partition-key hash |
| `task_uuid` | UnicodeAttribute (range) | UUID(as_uuid=True), PK | `uuid_generate_v4()` default |
| `partition_key` | UnicodeAttribute | String(128), NOT NULL | For RLS |
| `task_name` | UnicodeAttribute | String, NOT NULL | |
| `task_description` | UnicodeAttribute(null) | Text, nullable | |
| `initial_task_query` | UnicodeAttribute | Text, NOT NULL | |
| `subtask_queries` | ListAttribute(of=MapAttribute) | JSONB | |
| `agent_actions` | MapAttribute() | JSONB | Dict of agent_uuid → action |
| `updated_by` | UnicodeAttribute | String, NOT NULL | |
| `created_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |
| `updated_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |

Indexes: `(partition_key, updated_at)`

## 6. TaskSchedule (`ace-task_schedules` → `ace_task_schedules`)

| Field | DynamoDB Type | PostgreSQL Column | Notes |
| --- | --- | --- | --- |
| `task_uuid` | UnicodeAttribute (hash) | UUID(as_uuid=True), PK | Non-partition-key hash |
| `schedule_uuid` | UnicodeAttribute (range) | UUID(as_uuid=True), PK | `uuid_generate_v4()` default |
| `coordination_uuid` | UnicodeAttribute | UUID(as_uuid=True), NOT NULL | |
| `partition_key` | UnicodeAttribute | String(128), NOT NULL | For RLS |
| `schedule` | UnicodeAttribute | String, NOT NULL | Cron expression |
| `status` | UnicodeAttribute(default="initial") | String | |
| `updated_by` | UnicodeAttribute | String, NOT NULL | |
| `created_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |
| `updated_at` | UTCDateTimeAttribute | TIMESTAMP(timezone=True) | `NOW()` default |

Indexes: `(partition_key, updated_at)`, `(coordination_uuid)`

## RLS Coverage

All 6 tables have Row-Level Security policies applied (migration `0007`):

| Table | RLS Policy |
| --- | --- |
| `ace_coordinations` | `tenant_isolation` on `partition_key` |
| `ace_sessions` | `tenant_isolation` on `partition_key` |
| `ace_session_agents` | `tenant_isolation` on `partition_key` (added in PG) |
| `ace_session_runs` | `tenant_isolation` on `partition_key` |
| `ace_tasks` | `tenant_isolation` on `partition_key` |
| `ace_task_schedules` | `tenant_isolation` on `partition_key` |

Policy: `USING (partition_key = current_setting('app.tenant_id', true))`

## JSONB Fields Summary

| Entity | Field | DynamoDB Type | Notes |
| --- | --- | --- | --- |
| Coordination | `agents` | ListAttribute(of=MapAttribute) | List of agent dicts |
| Session | `input_files` | ListAttribute(of=MapAttribute) | |
| Session | `subtask_queries` | ListAttribute(of=MapAttribute) | |
| SessionAgent | `agent_action` | MapAttribute(null) | **GIN index** for nested filtering |
| Task | `subtask_queries` | ListAttribute(of=MapAttribute) | |
| Task | `agent_actions` | MapAttribute() | Dict of agent_uuid → action |

## Notes

- DynamoDB models are under `models/dynamodb/` with compatibility shims at `models/*.py`.
- PostgreSQL models are under `models/postgresql/` with repositories at `models/repositories/postgresql/`.
- All 6 entities have SQLAlchemy models, PG repositories, Alembic migrations (0001–0007), and PG batch loaders.
- `SessionAgent.partition_key` is the only field that exists in PostgreSQL but not in DynamoDB.
- The `agent_action` JSONB column on `ace_session_agents` has a GIN index for efficient nested key filtering (`primary_path`, `user_in_the_loop`, `predecessors`).
- Hash keys in DynamoDB that are not `partition_key` (e.g. `coordination_uuid`, `session_uuid`, `task_uuid`) are mapped to UUID primary keys in PostgreSQL, with `partition_key` as a separate indexed column for RLS.