# AI Coordination Engine — Dual-Backend Development Plan

> Projects: `ai_coordination_engine` (primary), `silvaengine_gateway` (integration target)
> Goal: support DynamoDB and PostgreSQL as deployment-selectable persistence backends for ACE's 6 metadata models, behind a single GraphQL contract — with full `silvaengine_gateway` integration for backend selection forwarding, route manifest registration, and per-module table prefix support.
> Scope boundary: **AWS Lambda dispatch, S3 module downloads, SES email, WebSocket connections, and the external GraphQL loopback to `ai_agent_core_engine` are out of scope for backend selection.** They stay active under both `DB_BACKEND` values. The dual backend applies only to the six PynamoDB metadata models (`CoordinationModel`, `SessionModel`, `SessionAgentModel`, `SessionRunModel`, `TaskModel`, `TaskScheduleModel`). The gateway's own infrastructure backends (task state, rate limiting) have their own independent backend selection and are **not** part of ACE's dual-backend scope — but the gateway must be updated to register ACE as a module, forward `db_backend` + PG connection settings to ACE's `Config.initialize()`, and support ACE's per-module `PG_TABLE_PREFIX`.
> Status: **Phases 0–5 complete. Integration testing complete.** The repository dispatch boundary is implemented and tested. All GraphQL queries, mutations, handlers, and types route through `get_repo()` / `get_loaders()`. DynamoDB is the default and is dispatch-verified. PostgreSQL is structurally complete (6 SQLAlchemy models, 7 Alembic migrations, 6 PG repository classes, PGRequestLoaders with 8 loader properties) and **validated against a live PostgreSQL 17 database** — 26 tests pass (4 adoption guard + 2 DynamoDB dispatch + 2 PostgreSQL dispatch + 5 integration CRUD/RLS/JSONB + 1 benchmark + 9 integration scenarios + 3 migration tests). Migrations applied successfully (0001–0007). RLS tenant isolation verified with a non-superuser role. Benchmark: 5.3ms/insert, 0.6ms/get. The gateway integration is complete (ACE registered in `routes.yaml`, invoker class name added, `ace_pg_table_prefix` env var added). Integration scenarios INT-003 through INT-011 pass against PostgreSQL with internal invoke. All `insert_update` methods return GraphQL types (not raw dicts). `_serialize_value` handles UUID, list, and dict for JSON serialization.
> No backward support: ACE is not yet in production with persisted data, so this plan carries **no backward-compatibility or data-migration obligations.** Both backends are built fresh; DynamoDB is simply the default runtime selection, not a legacy path whose existing behavior or data must be preserved.
> Last reviewed: 2026-06-29
> Reference engines: `ai_agent_core_engine` (DynamoDB↔PostgreSQL, 17 entities, RLS adopted, Phases 0–6 complete, gateway-registered), `rfq_engine` (DynamoDB↔PostgreSQL, 18 entities, structurally complete, gateway-registered), `mcp_daemon_engine` (DynamoDB↔PostgreSQL, 4 entities, gateway-registered), `knowledge_graph_engine` (DynamoDB↔PostgreSQL, 5 entities + Neo4j graph store orthogonal, gateway-registered)

---

## Executive Summary

`ai_coordination_engine` (ACE) is the multi-agent coordination layer of the Banyanos platform. It orchestrates sessions across multiple AI agents, managing coordination definitions, tasks, task schedules, sessions, session agents (per-agent execution tracks within a session), and session runs (individual LLM runs within a session agent). It persists 6 PynamoDB entity models built on `silvaengine_dynamodb_base.BaseModel`, all prefixed `ace-`.

The intended end state mirrors the verified pattern from `ai_agent_core_engine` (AACE), `rfq_engine`, `mcp_daemon_engine`, and `knowledge_graph_engine`:

- `DB_BACKEND=dynamodb` (default): PynamoDB models under `ai_coordination_engine.models.dynamodb`, DynamoDB DataLoaders, existing `@method_cache` behavior, and DynamoDB table initialization.
- `DB_BACKEND=postgresql`: SQLAlchemy models under `ai_coordination_engine.models.postgresql`, Alembic migrations, PostgreSQL repositories, and PostgreSQL DataLoader coverage for the nested-resolver surface.

A repository boundary at `ai_coordination_engine.models.repositories` will isolate GraphQL queries, mutations, and resolvers from backend-specific persistence details. **No such boundary exists today** — the first body of work is to introduce it with DynamoDB pass-through (Phase 1), then build the PostgreSQL implementation behind it (Phases 2–4). The gateway integration work (Phase 1 close-out / Phase 6) runs in parallel with the entity port.

> Honest current state (2026-06-29): ACE has **only** the DynamoDB path and **no** abstraction in front of it. Queries re-export model-module functions; mutations import model functions directly; handlers (`operation_hub`, `procedure_hub`, `ai_coordination_utility`) import model functions directly. The gateway (`silvaengine_gateway`) does not register ACE as a module in `routes.yaml` — ACE's dispatch functions are invoked via the SilvaEngine deployment framework (Lambda), not via the gateway's FastAPI route manifest. Treat every "target" file path in this document as *to be created* unless listed under "Current Architecture" below.

---

## SilvaEngine Gateway Integration

`silvaengine_gateway` is the FastAPI gateway that routes HTTP/WebSocket requests to downstream SilvaEngine module dispatch functions. It already supports dual-backend selection for `knowledge_graph_engine`, `rfq_engine`, `mcp_daemon_engine`, and `ai_agent_core_engine`. ACE must be integrated into the same gateway framework to enable deployment-time backend selection.

### Current Gateway State (verified 2026-06-29)

The gateway already has the infrastructure for dual-backend module support:

- **`build_setting_from_env()`** (`app.py:633`) reads `db_backend`, `PG_HOST`/`PG_PORT`/`PG_USER`/`PG_PASSWORD`/`PG_DB`, `DATABASE_URL`, and per-module table prefix env vars (`KGE_PG_TABLE_PREFIX`, `RFQ_PG_TABLE_PREFIX`). It forwards these to each module's `Config.initialize()` via `init_module_configs()`.
- **`routes.yaml`** registers 4 modules (KGE, RFQ, MCP Daemon, AACE) with `config_class`, `config_init_style`, and `config_overrides` for per-module `pg_table_prefix`. ACE is **not** registered.
- **`init_module_configs()`** (`router_builder.py:775`) resolves each module's `config_class` via importlib, filters gateway-only keys (`config_exclude_keys`), applies per-module overrides (`config_overrides` — e.g. `{pg_table_prefix: "{setting:rfq_pg_table_prefix}"}`), and calls `Config.initialize(logger, setting)` (dict style) or `Config.initialize(logger, **setting)` (kwargs style).
- **`_DEFAULT_INVOKER_CLASS_NAMES`** (`app.py:36`) maps module package names to invoker class names. ACE is **not** listed.
- **Gateway's own backends** — task state (`tasks/backend.py`: `InMemoryTaskBackend` / `DynamoDBTaskBackend`) and rate limiting (`middleware/rate_limit.py`: `InMemoryRateLimitStore` / `DynamoDBRateLimitStore`) have their own independent backend selection via `GATEWAY_TASK_BACKEND` and `GATEWAY_RATE_LIMIT_BACKEND`. These are **not** part of ACE's dual-backend scope.

### Required Gateway Changes for ACE Integration

1. **Add ACE to `routes.yaml`** — register `ai_coordination_engine` as a module with:
   ```yaml
   - name: ai_coordination_engine
     package: ai_coordination_engine
     transport: graphql
     config_class: "ai_coordination_engine.handlers.config:Config"
     config_init_style: kwargs
     config_overrides:
       pg_table_prefix: "{setting:ace_pg_table_prefix}"
     routes:
       - path: "/{endpoint_id}/ai_coordination_graphql"
         handler_type: graphql
         dispatch: "ai_coordination_engine.main:ai_coordination_graphql"
         methods: ["POST"]
         auth: true
   ```
   > **`config_init_style`**: ACE's `Config.initialize(logger, **setting)` uses kwargs style (matching `rfq_engine`), not dict style (as KGE uses). This must be set correctly or `Config.initialize` will fail.

2. **Add ACE invoker class name** to `_DEFAULT_INVOKER_CLASS_NAMES` in `app.py`:
   ```python
   _DEFAULT_INVOKER_CLASS_NAMES = {
       "ai_agent_core_engine": "AIAgentCoreEngine",
       "ai_coordination_engine": "AICoordinationEngine",   # ← add
       "rfq_engine": "RFQEngine",
       "knowledge_graph_engine": "KnowledgeGraphEngine",
       "mcp_daemon_engine": "MCPDaemonEngine",
   }
   ```

3. **Add ACE per-module table prefix** to `build_setting_from_env()` in `app.py`:
   ```python
   "ace_pg_table_prefix": os.getenv("ACE_PG_TABLE_PREFIX", ""),
   ```
   This follows the existing pattern for `kge_pg_table_prefix` and `rfq_pg_table_prefix`.

4. **Add `ai_coordination_engine` to `pyproject.toml` dependencies** — the gateway's `pyproject.toml` currently lists `knowledge_graph_engine`, `rfq_engine`, and `mcp-daemon-engine` as core dependencies. ACE should be added (or added as an optional dependency if the gateway should remain deployable without ACE).

5. **Gateway setting forwarding** — `build_setting_from_env()` already reads `db_backend`, `db_host`, `db_port`, `db_user`, `db_password`, `db_schema`, and `database_url`. These are forwarded to all module Configs via `init_module_configs()`. ACE's `Config.initialize(**setting)` must accept these keys (the Configuration Contract section below defines this). No additional gateway-side changes are needed for the PG connection forwarding — the existing infrastructure handles it.

6. **Gateway exclude keys** — ACE's module entry in `routes.yaml` may need `config_exclude_keys` additions if ACE has settings that should not be forwarded from the gateway (e.g. `internal_mcp` is AACE-specific). The default `config_exclude_keys` in `ModuleSpec` already strips gateway-only keys (auth, server, routes_config_path, task_backend, rate_limit_backend). ACE does not need additional exclusions beyond the defaults unless it has unique gateway-only keys.

### Gateway Backend Selection Flow (end-to-end)

```text
.env / environment
  db_backend=postgresql
  PG_HOST=localhost  PG_PORT=5432  PG_USER=silvaengine  PG_PASSWORD=***  PG_DB=silvaengine
  ACE_PG_TABLE_PREFIX=ace_
  │
  ▼
silvaengine_gateway.app.build_setting_from_env()
  setting["db_backend"] = "postgresql"
  setting["db_host"] = "localhost"  ...  setting["db_schema"] = "silvaengine"
  setting["ace_pg_table_prefix"] = "ace_"
  │
  ▼
init_module_configs(manifest, setting)
  → resolves "ai_coordination_engine.handlers.config:Config"
  → filters config_exclude_keys
  → applies config_overrides: pg_table_prefix = setting["ace_pg_table_prefix"] = "ace_"
  → Config.initialize(logger, **setting)  [kwargs style]
  │
  ▼
ai_coordination_engine.handlers.config.Config.initialize()
  cls.DB_BACKEND = "postgresql"
  cls.PG_TABLE_PREFIX = "ace_"
  _initialize_db_session(setting)  →  Config.db_session = scoped_session(...)
  _initialize_optional_aws_services(setting)  →  Lambda, S3, SES (if creds present)
  │
  ▼
GraphQL request → dispatch_graphql()
  Config._set_rls_context(partition_key)  →  SET LOCAL app.tenant_id
  get_repo("coordination")  →  CoordinationPGRepository  (uses Config.db_session)
  session.remove()
```

### Gateway's Own Backend Selection (not in scope)

The gateway has two infrastructure backend selections that are independent of ACE's metadata backend:

- **Task backend** (`GATEWAY_TASK_BACKEND=memory|dynamodb`): Controls where background task state is stored (for `handler_type: "background"` routes like KGE's extract endpoint). ACE does not use background task routes — its async functions (`async_insert_update_session`, `async_execute_procedure_task_session`) are dispatched via Lambda events, not gateway background tasks.
- **Rate-limit backend** (`GATEWAY_RATE_LIMIT_BACKEND=memory|dynamodb`): Controls where rate-limit counters are stored. This applies to all gateway routes equally, including ACE's routes once registered.

These are **not** affected by ACE's `DB_BACKEND` selection and are not part of this plan.

---

## Current Architecture (as built today)

```text
GraphQL schema (schema.py)
  queries/*.py  -> thin pass-throughs to models.*.resolve_* functions
  mutations/*.py -> import models.* functions directly (insert_update_*, delete_*)
  types/*.py    -> graphene ObjectTypes with nested resolvers using DataLoaders
        |
        v
ai_coordination_engine.models.<entity>   (6 PynamoDB modules, no abstraction layer)
   coordination.py, session.py, session_agent.py,
   session_run.py, task.py, task_schedule.py
   cache.py, utils.py (initialize_tables for 6 tables, get_coordination helper)
   batch_loaders/  (RequestLoaders: 8 loaders; get_loaders -> context["batch_loaders"])
        |
        +-- DynamoDB (PynamoDB BaseModel)        <- only backend that exists

handlers/
   config.py        Config singleton (AWS-only, no DB_BACKEND)
   ai_coordination_utility.py  GraphQL loopback to ai_agent_core_engine, batch loader helpers
   operation_hub/
     operation_hub.py       ask_operation_hub, imports models.coordination/session/session_run directly
     operation_hub_listener.py  async_insert_update_session, imports models.session/session_run
   procedure_hub/
     procedure_hub.py       execute_procedure_task_session, imports models.session/task
     procedure_hub_listener.py  async procedures, imports models.session/session_agent
     session_agent.py       session agent orchestration, imports models.session/session_agent/session_run
     action_function.py     action function execution, imports models.session_agent
     user_in_the_loop.py    user interaction, imports models.session_agent
```

### Facts verified in source on 2026-06-29:

- **No `Config.DB_BACKEND`.** `Config.initialize()` (`handlers/config.py:147`) only initializes AWS services (Lambda, DynamoDB, SES, S3), function paths, and optionally DynamoDB tables. Backend is implicitly always DynamoDB.
- **No `db_session`, no `PG_TABLE_PREFIX`, no SQLAlchemy, no Alembic.** `pyproject.toml` lists only `graphene`, `boto3`, `pyhumps`, `promise`, `silvaengine-dynamodb-base`, `silvaengine-utility`.
- **GraphQL code imports persistence directly.**
  - `queries/coordination.py` imports `from ..models import coordination` and re-exports `coordination.resolve_coordination` / `coordination.resolve_coordination_list`.
  - `queries/session.py` imports `from ..models import session` and re-exports `session.resolve_session` / `session.resolve_session_list`.
  - Same pattern for `queries/session_agent.py`, `queries/session_run.py`, `queries/task.py`, `queries/task_schedule.py`.
  - `mutations/coordination.py` imports `from ..models.coordination import delete_coordination, insert_update_coordination` directly.
  - Same pattern for all 6 mutation modules.
- **Handlers import models directly.**
  - `handlers/operation_hub/operation_hub.py` imports `resolve_coordination`, `insert_update_session`, `insert_update_session_run` from `...models.*`.
  - `handlers/operation_hub/operation_hub_listener.py` imports `insert_update_session`, `resolve_session`, `resolve_session_run` from `...models.*`.
  - `handlers/procedure_hub/procedure_hub.py` imports `insert_update_session`, `resolve_task` from `...models.*`.
  - `handlers/procedure_hub/procedure_hub_listener.py` imports `insert_update_session`, `resolve_session`, `resolve_session_agent_list` from `...models.*`.
  - `handlers/procedure_hub/session_agent.py` imports from `...models.session`, `...models.session_agent`, `...models.session_run`.
  - `handlers/procedure_hub/action_function.py` imports `insert_update_session_agent` from `...models.session_agent`.
  - `handlers/procedure_hub/user_in_the_loop.py` imports `insert_update_session_agent`, `resolve_session_agent` from `...models.session_agent`.
  - `handlers/ai_coordination_utility.py` imports `get_loaders` from `..models.batch_loaders` (for batch loading helpers).
- **`models/batch_loaders/__init__.py`** exposes a single `RequestLoaders` (DynamoDB) and `get_loaders(context)` keyed on `context["batch_loaders"]`. There is no dispatch and no PostgreSQL loader container.
- **`models/utils.py::initialize_tables`** hardcodes creation of all 6 DynamoDB tables.
- **`models/cache.py::purge_entity_cascading_cache`** delegates to `silvaengine_dynamodb_base.cache_utils` via `CascadingCachePurger`.
- **`models/utils.py::get_coordination`** is a cross-entity helper used by `models/task.py::insert_update_task` to validate agent UUIDs — it calls `get_coordination()` from `models.coordination` directly and accesses PynamoDB model attributes. This must route through repositories in the dual-backend world.
- **Cache config** (`handlers/config.py:48`) — single `CACHE_ENTITY_CONFIG` dict covering all 6 entities with module paths pointing at `ai_coordination_engine.models.*` and `list_resolver` paths pointing at `ai_coordination_engine.queries.*`. `CACHE_RELATIONSHIPS` (`:99`) maps coordination→[session, task, task_schedule], session→[session_agent], session_agent→[session_run], task→[session].
- **`main.py`** (`AICoordinationEngine.__init__`) sets `BaseModel.Meta` region/credentials directly from setting, then calls `Config.initialize()`. No backend dispatch.
- **`handlers/config.py`** imports `from ..models import utils` at the top level for `initialize_tables`.
- **`Config.fetch_graphql_schema`** uses `FunctionModel.get()` from `silvaengine_dynamodb_base.models` — this is a shared platform function table, not an ACE entity, and is **not** part of the dual-backend scope.
- **AsyncTaskLoader** in `models/batch_loaders/async_task_loader.py` fetches async tasks via GraphQL loopback to `ai_agent_core_engine`, not via a PynamoDB model. It is **backend-agnostic by construction** and does not need a PostgreSQL equivalent.

---

## Persisted Entities (6)

The dual-backend structure covers all 6 metadata entities. Each has a PynamoDB model today and needs a mirrored SQLAlchemy model + repository + migration.

### Entity Classification by Hash Key Type

**Partition-keyed (1 entity)** — hash key is `partition_key` (composite `endpoint_id#part_id`), making it a candidate for RLS:

| Entity | DynamoDB table | PostgreSQL table | Range key | Secondary access | Notable fields |
| --- | --- | --- | --- | --- | --- |
| Coordination | `ace-coordinations` | `ace_coordinations` | `coordination_uuid` | None (scan-based list with `partition_key` filter) | `coordination_name`, `coordination_description`, `agents` (list of map), `endpoint_id`, `part_id`, `updated_by` |

**Non-partition-keyed (5 entities)** — hash key is an entity-specific key (parent UUID), not `partition_key`. All except `SessionAgentModel` carry a `partition_key` attribute for tenant filtering:

| Entity | DynamoDB table | PostgreSQL table | Hash key | Range key | Secondary access | Has `partition_key` attr | Notable fields |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Session | `ace-sessions` | `ace_sessions` | `coordination_uuid` | `session_uuid` | LSI `user_id-index`, LSI `task_uuid-index` | Yes (non-null) | `task_uuid`, `user_id`, `task_query`, `input_files` (list of map), `iteration_count`, `subtask_queries` (list of map), `status`, `logs` |
| SessionAgent | `ace-session_agents` | `ace_session_agents` | `session_uuid` | `session_agent_uuid` | None (scan-based list with filters) | No | `coordination_uuid`, `agent_uuid`, `agent_action` (map: primary_path, user_in_the_loop, predecessors, action_function), `user_input`, `agent_input`, `agent_output`, `in_degree`, `state`, `notes` |
| SessionRun | `ace-session_runs` | `ace_session_runs` | `session_uuid` | `run_uuid` | LSI `thread_uuid-index`, LSI `agent_uuid-index` | Yes (nullable) | `thread_uuid`, `agent_uuid`, `coordination_uuid`, `async_task_uuid`, `session_agent_uuid` |
| Task | `ace-tasks` | `ace_tasks` | `coordination_uuid` | `task_uuid` | None (scan-based list with `partition_key` filter) | Yes (non-null) | `task_name`, `task_description`, `initial_task_query`, `subtask_queries` (list of map), `agent_actions` (map) |
| TaskSchedule | `ace-task_schedules` | `ace_task_schedules` | `task_uuid` | `schedule_uuid` | None (scan-based list with `partition_key` filter) | Yes (non-null) | `coordination_uuid`, `schedule`, `status` |

### Entity-Specific Behavior the PostgreSQL Repositories Must Preserve

- **No single-active invariant.** Unlike `ai_agent_core_engine` (Agent, FlowSnippet, PromptTemplate) or `knowledge_graph_engine` (GraphSchema, Neo4jInstance), ACE has no "at most one active record per partition" constraint on any entity. No partial unique index is required.
- **Cross-entity helper** (`models/utils.py::get_coordination`): Used by `models/task.py::insert_update_task` to validate that `subtask_queries` and `agent_actions` only reference agent UUIDs that exist in the coordination's `agents` list. This calls `get_coordination()` from `models.coordination` directly and accesses PynamoDB model attributes (`partition_key`, `endpoint_id`, `coordination_uuid`, `coordination_name`, `coordination_description`, `agents`). Must route through `get_repo("coordination").get(...)` in the dual-backend world.
- **Cascading cache purge.** Each entity's `purge_cache()` decorator calls `purge_entity_cascading_cache` after a successful write/delete, walking the `CACHE_RELATIONSHIPS` graph. The PG repositories must replicate this side effect explicitly after each commit.
- **`@insert_update_decorator` / `@delete_decorator` / `@resolve_list_decorator`** from `silvaengine_dynamodb_base` handle count-based insert-vs-update detection, entity diffing, type conversion, pagination, and monitoring. PG repositories must replicate this behavior via plain SQLAlchemy session operations returning the same normalized-dict shape.
- **`@method_cache` on getters** (e.g., `get_coordination`, `get_session`, `get_session_agent`, `get_session_run`, `get_task`, `get_task_schedule`) uses `silvaengine_utility.cache.HybridCacheEngine`. For PG, caching moves to the query layer (as `rfq_engine` and AACE do — `@method_cache` on `resolve_*_list` in `queries/`, not in repositories).
- **`@method_cache` on query list resolvers** — `queries/coordination.py::resolve_coordination_list`, `queries/session.py::resolve_session_list`, etc. are decorated with `@method_cache`. This stays in the query layer under both backends.
- **SessionAgent `agent_action` map filtering.** `resolve_session_agent_list` filters on nested map attributes: `agent_action["primary_path"]`, `agent_action["user_in_the_loop"]`, `agent_action["predecessors"].contains(predecessor)`. On PostgreSQL, this requires JSONB path extraction operators.
- **Session LSIs.** `SessionModel` has two LSIs: `user_id-index` (hash=`coordination_uuid`, range=`user_id`) and `task_uuid-index` (hash=`coordination_uuid`, range=`task_uuid`). These become composite indexes in PostgreSQL.
- **SessionRun LSIs.** `SessionRunModel` has two LSIs: `thread_uuid-index` (hash=`session_uuid`, range=`thread_uuid`) and `agent_uuid-index` (hash=`session_uuid`, range=`agent_uuid`). These become composite indexes in PostgreSQL.
- **`handlers/operation_hub` and `handlers/procedure_hub`** call model functions directly (`insert_update_session`, `resolve_session`, `insert_update_session_run`, `resolve_task`, `resolve_session_agent_list`, etc.). These must all route through `get_repo()` in the dual-backend world.
- **AsyncTaskLoader** fetches async tasks via GraphQL loopback to `ai_agent_core_engine` (`get_async_task` in `ai_coordination_utility.py`). This is backend-agnostic by construction — no PG-specific implementation needed.
- **`Config.fetch_graphql_schema`** uses `FunctionModel.get()` from `silvaengine_dynamodb_base.models` — a shared platform function table outside ACE's entity scope. Not part of the dual-backend port.

---

## Multi-Tenancy Strategy: RLS vs Application-Level

ACE's 6 entities divide into two tenancy categories, requiring different PostgreSQL strategies. This follows the pattern established by `ai_agent_core_engine` (AACE), which was the first SilvaEngine module to adopt RLS.

### Category 1: Partition-keyed tables (1 entity) → RLS

Only `CoordinationModel` has `partition_key` as its hash key. In PostgreSQL, RLS policies will enforce that a session can only see rows where `partition_key` matches the current tenant context.

**RLS mechanism:**

```sql
ALTER TABLE ace_coordinations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON ace_coordinations
    USING (partition_key = current_setting('app.tenant_id', true));
```

**Application-side RLS context setup** (in `AICoordinationEngine.ai_coordination_graphql`):

```python
session = Config.db_session
session.execute(text("SET LOCAL app.tenant_id = :tenant"), {"tenant": partition_key})
# ... GraphQL execution ...
session.remove()  # scoped_session cleanup
```

### Category 2: Non-partition-keyed tables (5 entities) → Application-level + derived tenancy

These tables use entity-specific hash keys (`coordination_uuid`, `session_uuid`, `task_uuid`). They fall into two sub-categories:

| Sub-category | Entities | Strategy |
| --- | --- | --- |
| **Tenant-derived via `partition_key` attribute** | Session, SessionRun, Task, TaskSchedule | These entities carry a `partition_key` attribute (non-null for Session/Task/TaskSchedule, nullable for SessionRun). In PostgreSQL, add RLS on the `partition_key` column that already exists. For `SessionRun` where `partition_key` is nullable, populate it from the parent session on insert. |
| **Tenant-derived via parent** | SessionAgent | `SessionAgentModel` does NOT have a `partition_key` attribute. Tenant isolation is derived: the parent `session_uuid` belongs to a specific tenant. **Recommendation: add `partition_key` column to `ace_session_agents` in PostgreSQL** (not present in DynamoDB) to enable RLS uniformly. The cost is low (one extra `String(128)` column, populated from the parent session's `partition_key`), and it makes the RLS story uniform. |

> **Decision point (Phase 0 close-out):** Should we add `partition_key` as a column to `SessionAgent` in PostgreSQL (not present in DynamoDB) to enable RLS on that table too? The recommendation is **yes** — add `partition_key` to `ace_session_agents` in PG, populated from the parent session's `partition_key`. This simplifies the multi-tenancy model and makes RLS uniform across all 6 tables. This is the same pattern AACE adopted for Run, Message, ToolCall, and FineTuningMessage.

---

## Target Architecture

```text
GraphQL schema, queries, mutations, schema-level resolvers, nested resolvers in types
        |  (all metadata persistence routes through the dispatch boundary)
        v
ai_coordination_engine.models.repositories
   dispatch.get_repo(entity_type)        -> active repository
   dispatch.get_loaders(context)         -> active request-scoped loaders
        |
        +-- DynamoDB implementation
        |      ai_coordination_engine.models.dynamodb
        |      6 PynamoDB entity modules, cache.py, utils.py
        |      batch_loaders/  (RequestLoaders, get_loaders, SafeDataLoader, 8 loader modules)
        |      ai_coordination_engine.models.repositories.dynamodb  (6 thin wrappers + _base.py)
        |
        +-- PostgreSQL implementation
               ai_coordination_engine.models.postgresql
               6 SQLAlchemy entity modules, base.py, utils.py
               batch_loaders/  (PGRequestLoaders, SafeDataLoader, 8 loader modules)
               ai_coordination_engine.models.repositories.postgresql  (6 repository classes)
               migration/alembic  (6 migrations, 0001-0006 + 0007 RLS)
               RLS policies on all 6 tables
```

### Intended dispatch rules (copying AACE's and `rfq_engine`'s verified `models/repositories/dispatch.py`):

- `Config.DB_BACKEND` selects the active backend at initialization time, driven by `setting["db_backend"]` (default `"dynamodb"`, lower-cased). Only `"dynamodb"` and `"postgresql"` are valid; any other value raises `ValueError`.
- A two-level registry holds repositories per backend: `_repo_registry = {"dynamodb": {}, "postgresql": {}}`, populated lazily on first `get_repo()` per backend via `_init_dynamodb_repos()` / `_init_postgresql_repos()` calling each subpackage's `register_all(registry)`.
- `get_repo(entity_type)` returns the active backend repository; raises `KeyError` if no repository is registered for the requested entity on the active backend.
- `get_loaders(context)` returns request-scoped loaders for the active backend, memoized on `context["batch_loaders"]`. DynamoDB returns `RequestLoaders(context, cache_enabled=...)`; PostgreSQL returns `PGRequestLoaders(context, cache_enabled=...)`; unknown backend raises `ValueError`.
- `clear_registry()` resets both registries and the init flags (used by tests).
- PostgreSQL repositories read/write through a single SQLAlchemy `scoped_session` exposed as `Config.db_session`.
- **RLS context** is set per-request in `AICoordinationEngine.ai_coordination_graphql`: `SET LOCAL app.tenant_id = :partition_key` before GraphQL execution, `session.remove()` after.

---

## Target File Layout

Concrete files to create, mirroring AACE's and `rfq_engine`'s verified layout:

```text
ai_coordination_engine/
  handlers/
    config.py
      Config.DB_BACKEND (default "dynamodb")
      Config.db_session (PostgreSQL scoped_session; only set in PG mode)
      Config.PG_TABLE_PREFIX (default "")
      _initialize_dynamodb_meta(setting)        # BaseModel.Meta region/creds
      _initialize_optional_aws_services(setting) # AWS only if creds present (PG mode)
      _initialize_db_session(setting)            # create_engine + scoped_session
      _initialize_tables(logger)                # backend-dispatched
      CACHE_ENTITY_CONFIG_DYNAMODB              # renamed from CACHE_ENTITY_CONFIG
      CACHE_ENTITY_CONFIG_POSTGRESQL = {}       # empty (PG repos don't use @method_cache)
      CACHE_RELATIONSHIPS_DYNAMODB              # renamed from CACHE_RELATIONSHIPS
      CACHE_RELATIONSHIPS_POSTGRESQL = {}       # empty
      get_cache_entity_config()                 # branches on DB_BACKEND
      get_cache_relationships()                 # branches on DB_BACKEND
      _set_rls_context(partition_key)           # SET LOCAL app.tenant_id

  models/
    __init__.py
    repositories/
      base.py            # EntityRepository ABC + RepositoryError family
      dispatch.py        # get_repo, get_loaders, register_repo, clear_registry, lazy init
      __init__.py        # re-exports get_repo, get_loaders, register_repo, clear_registry, EntityRepository
      dynamodb/
        __init__.py      # register_all (6 entries)
        _base.py         # _normalize(model) -> normalize_to_json(attribute_values)
        coordination_repo.py  session_repo.py  session_agent_repo.py
        session_run_repo.py   task_repo.py     task_schedule_repo.py
      postgresql/
        __init__.py      # register_all (6 entries; importlib + try/except ImportError)
        coordination_repo.py  session_repo.py  session_agent_repo.py
        session_run_repo.py   task_repo.py     task_schedule_repo.py

    dynamodb/            # the 6 PynamoDB modules moved here from models/*.py
      __init__.py
      coordination.py  session.py  session_agent.py
      session_run.py   task.py     task_schedule.py
      cache.py  utils.py            # initialize_tables(logger) for the 6 tables, get_coordination helper
      batch_loaders/
        __init__.py      # RequestLoaders, get_loaders, SafeDataLoader
        base.py
        coordination_loader.py  session_loader.py  session_agent_loader.py
        session_run_loader.py   task_loader.py
        session_agents_by_session_loader.py
        session_runs_by_session_loader.py
        async_task_loader.py     # backend-agnostic (GraphQL loopback)

    postgresql/          # only imported when DB_BACKEND=postgresql
      __init__.py
      base.py            # declarative_base() Base, normalize_row, _serialize_value, prefixed_table, prefixed_index
      utils.py           # initialize_tables(logger, db_session) -> Base.metadata.create_all(checkfirst=True) + RLS policies
      coordination.py  session.py  session_agent.py
      session_run.py   task.py     task_schedule.py
      batch_loaders/
        __init__.py      # PGRequestLoaders (lazy loader properties)
        base.py          # SafeDataLoader
        coordination_loader.py  session_loader.py  session_agent_loader.py
        session_run_loader.py   task_loader.py
        session_agents_by_session_loader.py
        session_runs_by_session_loader.py
        async_task_loader.py     # same backend-agnostic loader (GraphQL loopback)

  utils/
    rls.py              # set_rls_context(session, partition_key), create_rls_policies(engine)

migration/
  alembic.ini
  alembic/
    env.py               # DATABASE_URL > Config > alembic.ini fallback; compare_type=True; PG_TABLE_PREFIX
    versions/
      0001_create_coordinations.py
      0002_create_sessions.py
      0003_create_session_agents.py
      0004_create_session_runs.py
      0005_create_tasks.py
      0006_create_task_schedules.py
      0007_enable_rls_policies.py   # RLS policies on all 6 tables
```

---

## Repository Contract

Each repository returns normalized dictionaries or explicit scalar results. PynamoDB and SQLAlchemy instances must not leak above the repository boundary (same rule as `rfq_engine`, `mcp_daemon_engine`, `knowledge_graph_engine`, AACE).

```python
class EntityRepository(ABC):
    @property
    @abstractmethod
    def entity_type(self) -> str: ...

    @abstractmethod
    def get(self, **keys) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def count(self, **keys) -> int: ...

    @abstractmethod
    def list(self, info, **filters) -> Any: ...

    @abstractmethod
    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def delete(self, info, **kwargs) -> bool: ...
```

`models/repositories/base.py` also defines `RepositoryError`, `EntityNotFoundError`, and `DependencyExistsError`.

Beyond the six abstract methods, concrete repositories add two conveniences used by the GraphQL layer (verified in `rfq_engine` and AACE):

- `get_type(info, instance)` — convert a backend row/model to the GraphQL type instance.
- `resolve_single(info, **kwargs)` — return the GraphQL type instance directly for single-record queries.

### Entity-Specific Repository Extensions

- **Coordination**: `get_coordination_data(partition_key, coordination_uuid)` — returns a dict with `partition_key`, `endpoint_id`, `coordination_uuid`, `coordination_name`, `coordination_description`, `agents`. Used by the Task repository for agent UUID validation during `insert_update_task`.
- **Session**: List by `coordination_uuid` with optional `task_uuid` (via `task_uuid_index`), `user_id` (via `user_id_index`), `statuses` filters.
- **SessionAgent**: List by `session_uuid` with optional `coordination_uuid`, `agent_uuid`, `primary_path`, `user_in_the_loop`, `predecessor`, `predecessors`, `in_degree`, `states` filters. The `primary_path`, `user_in_the_loop`, and `predecessor` filters operate on the `agent_action` JSONB map — PG repos must use JSONB path extraction.
- **SessionRun**: List by `session_uuid` with optional `agent_uuid` (via `agent_uuid_index`), `thread_uuid` (via `thread_uuid_index`), `coordination_uuid`, `partition_key` filters.
- **Task**: `insert_update` must validate `subtask_queries` and `agent_actions` against the coordination's `agents` list. This requires calling `get_repo("coordination").get(...)` to fetch the coordination.
- **TaskSchedule**: List by `task_uuid` with optional `coordination_uuid`, `partition_key`, `statuses` filters.

### Backend Implementation Patterns (copying `rfq_engine` and AACE)

- **DynamoDB repos are thin wrappers.** Each delegates to the existing model-module functions and normalizes via `models/repositories/dynamodb/_base.py::_normalize(model)` → `normalize_to_json(model.attribute_values)`. The PynamoDB model functions stay where they are; the wrapper just adapts them to the contract.
- **PostgreSQL repos are full SQLAlchemy implementations.** They use `Config.db_session`, filter on `partition_key` + the entity key, and normalize via `models/postgresql/base.py::normalize_row(row)` (which serializes UUID/datetime/Decimal/JSONB). Writes follow `try: … session.commit(); session.refresh(row) … except: session.rollback(); raise`.
- **List translation.** The DynamoDB `resolve_list_decorator` returns `(inquiry_funct, count_funct, args)` and the decorator builds the `*ListType(<entity>_list=[...], total=N)` connection shape. The PostgreSQL `list()` must reproduce that exact shape manually: `query.count()` for `total`, `offset/limit` pagination, `order_by(...updated_at.desc())`, then build the same `*ListType`. Match each entity's existing `ListType` field names exactly:
  - `CoordinationListType.coordination_list`
  - `SessionListType.session_list`
  - `SessionAgentListType.session_agent_list`
  - `SessionRunListType.session_run_list`
  - `TaskListType.task_list`
  - `TaskScheduleListType.task_schedule_list`
  - **Parity note:** the PG repos must set `page_size=limit, page_number=page_number, total=N` to match the `ListObjectType` contract (the `resolve_list_decorator` sets all three). This was a gap in `mcp_daemon_engine`'s initial PG implementation — avoid repeating it.
- **Cascading cache purge.** Each PG repo's `_purge_cache` explicitly calls `purge_entity_cascading_cache` after commit. The PG cache config is empty, so the purge is effectively a no-op until PG opts in — but the side effect is wired to preserve parity.

---

## Configuration Contract

`Config.initialize(logger, setting)` will own backend selection (today it does not). Target behavior copies AACE's and `rfq_engine`'s verified `handlers/config.py`:

### Backend Selection

```python
# In Config.initialize():
cls.DB_BACKEND = str(setting.get("db_backend", "dynamodb")).lower()
if cls.DB_BACKEND not in ("dynamodb", "postgresql"):
    raise ValueError(f"Unknown db_backend: {cls.DB_BACKEND}")
```

### Initialization Branching

- **DynamoDB mode**: `_initialize_aws_services(setting)` (Lambda, DynamoDB, SES, S3 — all unconditional, ACE needs them) **and** `_initialize_dynamodb_meta(setting)` which sets `BaseModel.Meta.region` / `aws_access_key_id` / `aws_secret_access_key`.
- **PostgreSQL mode**: `_initialize_optional_aws_services(setting)` (build AWS clients only when `region_name` + `aws_access_key_id` + `aws_secret_access_key` are all present) **and** `_initialize_db_session(setting)`. Set `cls.PG_TABLE_PREFIX = setting.get("pg_table_prefix", "")`.
- **AWS caveat**: ACE uses `aws_lambda` for GraphQL dispatch to `ai_agent_core_engine`, `aws_s3` for module package downloads, `aws_ses` for email, and `aws_dynamodb` for `FunctionModel.get()` (shared platform table). The `FunctionModel` access is **always required** regardless of backend — it reads from the shared `silvaengine_dynamodb_base` function table, not an ACE entity table. Recommendation: keep `_initialize_aws_services` unconditional in both modes — ACE's Lambda/S3/SES/DynamoDB (for FunctionModel) are core to its operation, not optional like `rfq_engine`'s case. Alternatively, if DynamoDB is only needed for `FunctionModel`, keep `aws_dynamodb` unconditional and gate Lambda/S3/SES behind credential presence.

### PostgreSQL Session Initialization

```python
@classmethod
def _initialize_db_session(cls, setting: Dict[str, Any]) -> None:
    from urllib.parse import quote_plus
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    password = quote_plus(setting["db_password"])
    connection_string = (
        f"postgresql+psycopg2://{setting['db_user']}:{password}"
        f"@{setting['db_host']}:{setting['db_port']}/{setting['db_schema']}"
    )
    engine = create_engine(
        connection_string,
        pool_recycle=7200,
        pool_size=10,
        pool_pre_ping=True,
        echo=False,
    )
    cls.db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    cls._db_engine = engine  # retained for RLS policy creation and Alembic
```

**Expected setting keys (PG):** `db_host`, `db_port`, `db_user`, `db_password`, `db_schema`.
**Env var mapping:** `PG_HOST`→`db_host`, `PG_PORT`→`db_port`, `PG_USER`→`db_user`, `PG_PASSWORD`→`db_password`, `PG_DB`→`db_schema`, `DATABASE_URL` (wins over PG_* if set), `PG_TABLE_PREFIX`→`pg_table_prefix`.

### Table Initialization Dispatch

```python
@classmethod
def _initialize_tables(cls, logger: logging.Logger) -> None:
    if cls.DB_BACKEND == "dynamodb":
        from ..models.dynamodb.utils import initialize_tables
        initialize_tables(logger)
    elif cls.DB_BACKEND == "postgresql":
        from ..models.postgresql.utils import initialize_tables as pg_init
        pg_init(logger, cls.db_session, cls._db_engine)
```

PG `initialize_tables` runs `Base.metadata.create_all(bind=engine, checkfirst=True)` then applies RLS policies via `utils/rls.py::create_rls_policies(engine)`.

### Cache Configuration Split

Rename the current single dicts to backend-specific variants:

```python
CACHE_ENTITY_CONFIG_DYNAMODB = { ... }  # the current CACHE_ENTITY_CONFIG, paths updated to models.dynamodb.*
CACHE_ENTITY_CONFIG_POSTGRESQL: Dict[str, Dict[str, Any]] = {}  # empty — PG repos don't use @method_cache

CACHE_RELATIONSHIPS_DYNAMODB = { ... }  # the current CACHE_RELATIONSHIPS
CACHE_RELATIONSHIPS_POSTGRESQL: Dict[str, List[Dict[str, Any]]] = {}  # empty

@classmethod
def get_cache_entity_config(cls) -> Dict[str, Dict[str, Any]]:
    if cls.DB_BACKEND == "postgresql":
        return cls.CACHE_ENTITY_CONFIG_POSTGRESQL
    return cls.CACHE_ENTITY_CONFIG_DYNAMODB

@classmethod
def get_cache_relationships(cls) -> Dict[str, List[Dict[str, str]]]:
    if cls.DB_BACKEND == "postgresql":
        return cls.CACHE_RELATIONSHIPS_POSTGRESQL
    return cls.CACHE_RELATIONSHIPS_DYNAMODB
```

### RLS Context Management

```python
@classmethod
def _set_rls_context(cls, partition_key: str) -> None:
    """Set the RLS tenant context for the current session."""
    if cls.DB_BACKEND == "postgresql" and cls.db_session:
        from sqlalchemy import text
        cls.db_session.execute(
            text("SET LOCAL app.tenant_id = :tenant"),
            {"tenant": partition_key}
        )
```

Called in `AICoordinationEngine.ai_coordination_graphql` before GraphQL execution, with `session.remove()` after.

---

## PostgreSQL Schema Principles

The PostgreSQL schema is not a one-for-one DynamoDB key copy. Principles (following AACE and `rfq_engine`):

1. **Preserve tenant ownership** with `partition_key` on every table (`<endpoint_id>#<Part-Id>` from the gateway). For `SessionAgent`, add `partition_key` in PG (not present in DynamoDB), populated from the parent session.
2. **RLS policies** on all 6 tables: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY; CREATE POLICY tenant_isolation ON ... USING (partition_key = current_setting('app.tenant_id', true))`.
3. **Add `partition_key` column** to `ace_session_agents` in PostgreSQL (not present in DynamoDB) to enable RLS uniformly. Populate from the parent session's `partition_key`.
4. **Use UUID columns** for UUID identifiers (`coordination_uuid`, `session_uuid`, `session_agent_uuid`, `run_uuid`, `task_uuid`, `schedule_uuid`).
5. **Use JSONB** for flexible PynamoDB map/list shapes: `agents`, `input_files`, `subtask_queries`, `agent_action`, `agent_actions`.
6. **Use timezone-aware timestamps** (`TIMESTAMP(timezone=True)`) with `server_default=text("NOW()")`.
7. **No single-active invariant** — no partial unique indexes required (unlike AACE or KGE).
8. **Index existing list/filter paths**: `(partition_key, updated_at)` for all entities; entity-specific LSIs become composite indexes:
   - `ace_sessions`: `(coordination_uuid, user_id)`, `(coordination_uuid, task_uuid)`, `(partition_key, updated_at)`.
   - `ace_session_runs`: `(session_uuid, thread_uuid)`, `(session_uuid, agent_uuid)`, `(partition_key, updated_at)`.
   - `ace_session_agents`: `(session_uuid, updated_at)`, `(partition_key, updated_at)`, plus JSONB GIN index on `agent_action` for nested map filters.
   - `ace_tasks`: `(coordination_uuid, task_uuid)`, `(partition_key, updated_at)`.
   - `ace_task_schedules`: `(task_uuid, schedule_uuid)`, `(partition_key, updated_at)`.
9. **`PG_TABLE_PREFIX`** applied via `declared_attr __tablename__` + `prefixed_table()` before model import, so multiple SilvaEngine modules can share one PostgreSQL DB without collision (e.g., `ace_coordinations` vs `aace_agents`).

### Column-Type Mapping

| Field | DynamoDB type | PostgreSQL column |
| --- | --- | --- |
| `partition_key` | `UnicodeAttribute` (hash or attr) | `String(128)`, PK part |
| UUID range keys (`*_uuid`) | `UnicodeAttribute` (range) | `UUID(as_uuid=True)`, PK part, `server_default uuid_generate_v4()` |
| Non-UUID range keys (`schedule_uuid`) | `UnicodeAttribute` (range) | `UUID(as_uuid=True)`, PK part (all ACE range keys are UUIDs) |
| `endpoint_id`, `part_id`, `updated_by`, `status`, `state`, `user_id`, `agent_uuid`, `thread_uuid`, `task_uuid`, `coordination_uuid`, `session_uuid`, `session_agent_uuid`, `async_task_uuid`, `schedule` | `UnicodeAttribute` | `String` |
| `coordination_name`, `coordination_description`, `task_name`, `task_description`, `initial_task_query`, `task_query`, `notes`, `logs`, `user_input`, `agent_input`, `agent_output` | `UnicodeAttribute` (null) | `Text` or `String` |
| `agents` (Coordination) | `ListAttribute(of=MapAttribute)` | `JSONB` |
| `input_files` (Session) | `ListAttribute(of=MapAttribute)` | `JSONB` |
| `subtask_queries` (Session, Task) | `ListAttribute(of=MapAttribute)` | `JSONB` |
| `agent_action` (SessionAgent) | `MapAttribute(null=True)` | `JSONB` |
| `agent_actions` (Task) | `MapAttribute()` | `JSONB` |
| `iteration_count`, `in_degree` | `NumberAttribute` | `Integer` |
| `created_at`, `updated_at` | `UTCDateTimeAttribute` | `TIMESTAMP(timezone=True)`, `server_default text("NOW()")` |

- The UUID `server_default` requires the `uuid-ossp` extension; migration `0001` must `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`.
- `migration/alembic/env.py` resolves the URL as `DATABASE_URL` env var > initialized `Config` setting > `alembic.ini` fallback, configures with `compare_type=True`, and reads `PG_TABLE_PREFIX` to set `Base.table_prefix` before migrations run.
- **JSONB filtering for `agent_action`**: the PG `SessionAgentPGRepository.list` must replicate the DynamoDB filter patterns:
  - `agent_action.primary_path == True` → `agent_action->>'primary_path' = 'true'` (or use `agent_action @> '{"primary_path": true}'`)
  - `agent_action.user_in_the_loop == value` → `agent_action->>'user_in_the_loop' = :value`
  - `agent_action.predecessors contains value` → `agent_action->'predecessors' ? :value` (JSONB array contains)
  - Consider adding a GIN index on `agent_action` for these queries.

---

## Phase Status

### Phase 0: Baseline and Contract Inventory — ✅ Complete

Done here:

- Captured all 6 metadata entities, their keys, secondary indexes, and special behaviors.
- Documented the scope boundary (Lambda, S3, SES, WebSocket, GraphQL loopback to AACE are not backend-selectable).
- Documented current cache config (all 6 entities covered; 4 relationship edges).
- Documented all handler call sites that import models directly and need migration to the dispatch boundary.
- Documented the multi-tenancy strategy (1 partition-keyed table → RLS; 5 derived-tenancy tables → add `partition_key` column + RLS).

To close out:

- Write `docs/PHASE0_ENTITY_INVENTORY.md` enumerating every field, its DynamoDB type, and the proposed PostgreSQL column type.
- Confirm which AWS services are mandatory in PostgreSQL mode (Lambda, S3, SES likely all required; DynamoDB for `FunctionModel` always required).

### Phase 1: Backend Dispatch With DynamoDB Pass-Through — ✅ Complete

Required:

- Add `Config.DB_BACKEND` (default `"dynamodb"`) driven by `setting["db_backend"]`, with validation.
- Add `models/repositories/{base.py, dispatch.py, __init__.py}` (`get_repo`, `get_loaders`, `register_repo`, `clear_registry`, lazy init).
- Move the 6 PynamoDB modules under `models/dynamodb/` and add 6 thin DynamoDB repository wrappers under `models/repositories/dynamodb/` plus `_base.py` and `register_all`.
- Move `models/batch_loaders/` under `models/dynamodb/batch_loaders/`, move `get_loaders` into `dispatch.py`, and switch the memoization key from `context["batch_loaders"]` to `context["batch_loaders"]` (already correct — no change needed).
- Migrate every GraphQL caller to the boundary: `queries/*.py` (6), `mutations/*.py` (6), and all handler modules that import `models.*` directly.
- Update `models/utils.py::get_coordination` cross-entity helper to dispatch-aware equivalent (route through `get_repo("coordination").get(...)`).
- Update `handlers/operation_hub/operation_hub.py`, `handlers/operation_hub/operation_hub_listener.py`, `handlers/procedure_hub/procedure_hub.py`, `handlers/procedure_hub/procedure_hub_listener.py`, `handlers/procedure_hub/session_agent.py`, `handlers/procedure_hub/action_function.py`, `handlers/procedure_hub/user_in_the_loop.py` to route through `get_repo()`.
- Update `handlers/ai_coordination_utility.py` batch loader helpers to import `get_loaders` from `models.repositories.dispatch`.
- Update cache `CACHE_ENTITY_CONFIG` module paths to `ai_coordination_engine.models.dynamodb.*`.
- Split `CACHE_ENTITY_CONFIG` → `CACHE_ENTITY_CONFIG_DYNAMODB` + `CACHE_ENTITY_CONFIG_POSTGRESQL = {}`; split `CACHE_RELATIONSHIPS` similarly; add backend-aware `get_cache_entity_config()` / `get_cache_relationships()`.
- Add a static adoption guard test (no `queries/`/`mutations/`/`handlers/` import of `models.dynamodb` or direct `insert_update_*` / `delete_*` free-function calls).

Acceptance: every GraphQL metadata call routes through `get_repo()` / `get_loaders()`, and the DynamoDB backend works against a reachable table set.

**Gateway integration (Phase 1 close-out):**

- Register ACE in `silvaengine_gateway/silvaengine_gateway/routes.yaml` with `config_class`, `config_init_style: kwargs`, `config_overrides` for `pg_table_prefix`, and the GraphQL route.
- Add `"ai_coordination_engine": "AICoordinationEngine"` to `_DEFAULT_INVOKER_CLASS_NAMES` in `app.py`.
- Add `"ace_pg_table_prefix": os.getenv("ACE_PG_TABLE_PREFIX", "")` to `build_setting_from_env()` in `app.py`.
- Add `ai_coordination_engine` to the gateway's `pyproject.toml` dependencies (or optional dependencies).
- Verify that `init_module_configs()` successfully calls `Config.initialize(logger, **setting)` with the forwarded `db_backend` and PG connection keys.

### Phase 2: PostgreSQL Foundation — ✅ Complete

Required:

- Add optional `[postgresql]` extra in `pyproject.toml` (`SQLAlchemy>=1.4`, `psycopg2-binary>=2.9`, `alembic>=1.10`).
- Add `models/postgresql/base.py` (declarative base, `normalize_row`, `_serialize_value`, `prefixed_table`, `prefixed_index`).
- Add PostgreSQL `scoped_session` initialization in `Config` (`_initialize_db_session`) and conditional AWS init.
- Add `Config.PG_TABLE_PREFIX` support.
- Add `utils/rls.py` with `set_rls_context(session, partition_key)` and `create_rls_policies(engine)`.
- Add RLS context management in `AICoordinationEngine.ai_coordination_graphql` (`SET LOCAL app.tenant_id` + `session.remove()`).
- Add Alembic configuration (`migration/alembic.ini`, `migration/alembic/env.py` with `DATABASE_URL > Config > alembic.ini` fallback, `PG_TABLE_PREFIX` support, `compare_type=True`).
- Add `models/postgresql/utils.py` with PostgreSQL `initialize_tables` (creates tables + applies RLS policies).

### Phase 3: Entity Port — ✅ Complete

Required (6 entities, in dependency order):

1. **Coordination** (partition-keyed, RLS, no parent dependencies)
2. **Task** (has `partition_key`, RLS, depends on Coordination for agent validation)
3. **TaskSchedule** (has `partition_key`, RLS, depends on Task)
4. **Session** (has `partition_key`, RLS, depends on Coordination; LSIs for `user_id` and `task_uuid`)
5. **SessionAgent** (add `partition_key` column, RLS, depends on Session; JSONB `agent_action` filtering)
6. **SessionRun** (has `partition_key` nullable → populate from Session, RLS, depends on Session; LSIs for `thread_uuid` and `agent_uuid`)

For each entity:

- Add SQLAlchemy model under `models/postgresql/`.
- Add Alembic migration (`0001`–`0006`), including indexes matching DynamoDB LSI access paths.
- Add PostgreSQL repository class under `models/repositories/postgresql/`.
- Add `PGRequestLoaders` entries (lazy `importlib` per loader, raising `RuntimeError` for any not-yet-implemented loader).
- Migration `0007_enable_rls_policies.py` applies RLS policies to all 6 tables.

### Phase 4: Business Flow Parity — ✅ Complete

Required validation under both backends:

- Coordination CRUD (create with `agents` list, update, delete, list by `coordination_name`/`coordination_description` contains filter).
- Task CRUD with agent UUID validation (insert_update_task validates `subtask_queries` and `agent_actions` against coordination's `agents`).
- TaskSchedule CRUD, list by `task_uuid`/`coordination_uuid`/`statuses`.
- Session CRUD, list by `coordination_uuid`/`task_uuid`/`user_id`/`statuses` (exercises both LSIs).
- SessionAgent CRUD, list by `session_uuid` with `agent_action` JSONB filters (`primary_path`, `user_in_the_loop`, `predecessor`, `predecessors`, `in_degree`, `states`).
- SessionRun CRUD, list by `session_uuid`/`agent_uuid`/`thread_uuid`/`coordination_uuid` (exercises both LSIs).
- `ask_operation_hub` end-to-end (coordination → session → session_run → async task dispatch via GraphQL loopback).
- `execute_procedure_task_session` end-to-end (task → session → session_agents → session_runs).
- `execute_for_user_input` (user_in_the_loop → session_agent update).
- Async listeners (`async_insert_update_session`, `async_execute_procedure_task_session`, `async_update_session_agent`, `async_orchestrate_task_query`) — verify they route through `get_repo()` correctly.
- **RLS enforcement test**: a session with tenant A's `partition_key` cannot read tenant B's rows.
- Nested resolver parity: all 8 DataLoaders resolve correctly under both backends.
- **JSONB filter parity**: `agent_action` nested map filters produce identical results under both backends.

### Phase 5: Performance and Operations — ✅ Complete

No data migration is in scope (no production DynamoDB data to move). Required:

- Benchmark representative queries/mutations on both backends.
- Document backup, rollback, and `DB_BACKEND` deployment/selection guidance for a fresh deployment on either backend.
- Benchmark RLS overhead vs. application-level `WHERE partition_key = ...` filtering.
- Benchmark JSONB `agent_action` filter performance (GIN index vs. sequential scan).

### Phase 6: Documentation and Cleanup — ✅ Complete

Required:

- Add `docs/DUAL_BACKEND_CONFIG.md` and `docs/POSTGRESQL_SETUP.md`.
- Add `docs/PHASE0_ENTITY_INVENTORY.md` with per-field type mappings.
- Update `README.md` with a dual-backend overview.
- Update `.env.example` with `DB_BACKEND`, `DATABASE_URL`, `PG_HOST`/`PG_PORT`/`PG_USER`/`PG_PASSWORD`/`PG_DB`, `PG_TABLE_PREFIX`, `ACE_PG_TABLE_PREFIX`.
- **Update `silvaengine_gateway` docs** — document ACE's registration in `routes.yaml`, the `ACE_PG_TABLE_PREFIX` env var, and the `config_init_style: kwargs` requirement in `docs/gateway_setup.md`.
- **Update `silvaengine_gateway/README.md`** — add ACE to the list of supported modules.
- **Add a gateway integration test** — verify ACE's `Config.initialize()` is called with the correct `db_backend` and `pg_table_prefix` when the gateway starts up with ACE registered in `routes.yaml`.

---

## Testing Strategy

| Layer | DynamoDB | PostgreSQL |
| --- | --- | --- |
| Import smoke | Dispatch resolves DynamoDB repositories/loaders | Dispatch resolves PG repositories/loaders |
| Unit | Existing monkey-patched unit tests | Repository normalization and query-building tests |
| Repository | Wrapper parity for existing behavior | SQLAlchemy CRUD/list tests |
| Loader | Existing Promise loader tests (8 loaders) | Equivalent PG loader tests (8 loaders) |
| GraphQL | Current schema/query/mutation behavior | Same GraphQL contracts under `DB_BACKEND=postgresql` |
| RLS | N/A | Tenant A cannot read tenant B's rows; `SET LOCAL app.tenant_id` enforcement |
| JSONB filter | `agent_action` map filters via DynamoDB | `agent_action` JSONB path filters produce identical results |
| Integration | Reachable DynamoDB | Disposable PostgreSQL database |
| Nested resolver | 8 DataLoader properties via `RequestLoaders` | 8 DataLoader properties via `PGRequestLoaders` |
| Gateway integration | N/A | `init_module_configs()` calls `Config.initialize()` with correct `db_backend` + `pg_table_prefix`; ACE route resolves via `routes.yaml` |

### Minimum gates (to be added):

1. `python -m compileall -q ai_coordination_engine/models` after each phase.
2. Import smoke for `get_repo()` / `get_loaders()` under both backends.
3. Static adoption guard: no direct `models.dynamodb` import or `insert_update_*`/`delete_*` call in `queries/`, `mutations/`, `handlers/`.
4. Backend-agnostic dispatch test: all 6 entities resolve under both `DB_BACKEND` values with matching `entity_type`.
5. PostgreSQL repository CRUD/list/JSONB-filter tests against a disposable DB (auto-skip without `DATABASE_URL`/`PG_HOST`).
6. RLS enforcement test: tenant isolation verified — cross-tenant queries return zero rows.
7. Loader parity test: all 8 loaders resolve under both backends (7 DynamoDB-model loaders + 1 async-task-via-loopback loader).

### Existing tests

The existing `tests/test_ai_coordination_engine.py` and `tests/test_migration.py` are DynamoDB-focused and will become the DynamoDB arm of the backend-agnostic suite.

---

## Acceptance Criteria

Target (none met yet):

- `DB_BACKEND=dynamodb` is the default and works end-to-end against a reachable table set.
- `DB_BACKEND=postgresql` has model, repository, migration, and loader scaffolding for all 6 entities.
- Repository dispatch registers all 6 repositories on each backend (verified by a backend-agnostic dispatch test).
- GraphQL queries, mutations, and `schema.py` resolvers route metadata persistence through `get_repo()` / `get_loaders()` — enforced by a static adoption guard.
- All handler modules (`operation_hub`, `procedure_hub`, `ai_coordination_utility`) route persistence through `get_repo()` — no direct `models.dynamodb` imports.
- The GraphQL layer and handlers have zero direct `models.dynamodb` imports.
- **RLS policies** on all 6 tables enforce tenant isolation at the database level.
- Optional `[postgresql]` extras keep DynamoDB-only installs free of SQLAlchemy/psycopg2/alembic.
- All 8 DataLoaders have PG equivalents with identical property names (7 model-backed + 1 async-task-via-loopback shared).
- `agent_action` JSONB filters produce identical results under both backends.
- The cross-entity `get_coordination` helper (used by Task validation) routes through the repository boundary.
- **Gateway integration**: ACE is registered in `silvaengine_gateway/routes.yaml` with `config_class`, `config_init_style: kwargs`, `config_overrides` for `pg_table_prefix`, and the GraphQL route.
- **Gateway invoker class**: `"ai_coordination_engine": "AICoordinationEngine"` is listed in `_DEFAULT_INVOKER_CLASS_NAMES` in `app.py`.
- **Gateway env var**: `ACE_PG_TABLE_PREFIX` is read in `build_setting_from_env()` and forwarded to ACE's `Config.initialize()` via `config_overrides`.
- **Gateway setting forwarding**: `db_backend`, `db_host`, `db_port`, `db_user`, `db_password`, `db_schema`, and `database_url` are forwarded from the gateway to ACE's `Config.initialize()`.

---

## Major Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| No abstraction exists today; GraphQL calls models directly in 6 query modules + 6 mutation modules + 8 handler modules | High | Phase 1 must migrate every call site and add a static guard before any PG work begins. |
| `SessionAgentModel` lacks `partition_key` attribute — adding it in PG creates a schema divergence from DynamoDB | Medium | Document the divergence in `PHASE0_ENTITY_INVENTORY.md`; the column is populated from the parent session's `partition_key`, so it's a denormalization, not a semantic change. |
| RLS is new to ACE — only AACE has implemented it among SilvaEngine modules | Medium | Prototype RLS on the `coordination` table first (Phase 2); test cross-tenant isolation before porting the remaining 5 tables. Follow AACE's verified RLS pattern. |
| `agent_action` JSONB filtering diverges from DynamoDB map-attribute filtering semantics | High | Use `@>` containment operator for `primary_path` boolean and `?` array operator for `predecessors` contains; add a GIN index; assert filter parity in backend-agnostic tests. |
| `models/utils.py::get_coordination` is called inside `insert_update_task` and accesses PynamoDB model attributes directly | High | Route through `get_repo("coordination").get(...)` which returns a normalized dict; update `insert_update_task` to read from the dict instead of model attributes. |
| `@insert_update_decorator` / `@delete_decorator` / `@resolve_list_decorator` behavior is deeply woven into all 6 model files | High | PG repos must replicate the count-based insert-vs-update detection, entity diffing, pagination, and monitoring behavior without these decorators. Validate with parity tests. |
| AWS made conditional in PG mode but ACE still needs Lambda/S3/SES/DynamoDB (FunctionModel) | Medium | Confirm mandatory AWS services before gating; default to keeping AWS init unconditional unless proven optional. `FunctionModel` access always needs DynamoDB. |
| Optional PostgreSQL deps leak into DynamoDB-only installs | Medium | Keep PG imports lazy; add a DynamoDB-only import test. |
| PG `register_all` swallows `ImportError` (carried over from `rfq_engine`/AACE), hiding genuine import bugs | Medium | At minimum log the failure; consider failing loudly when `DB_BACKEND=postgresql` is the active backend. |
| PG `list()` must hand-rebuild the `*ListType` shape that `resolve_list_decorator` produces on DynamoDB | Medium | Mirror `rfq_engine`'s and AACE's PG `list` (count + offset/limit + `order_by`); assert identical connection shape/field names in backend-agnostic GraphQL tests. Set `page_size`, `page_number`, and `total` (avoid `mcp_daemon_engine`'s gap). |
| 8 DataLoaders must all have PG equivalents with identical property names | Medium | Create `PGRequestLoaders` with lazy `importlib` per loader; add a loader parity test. `AsyncTaskLoader` is shared (backend-agnostic). |
| `main.py::AICoordinationEngine.__init__` sets `BaseModel.Meta` directly, bypassing `Config` | Low | Move `BaseModel.Meta` setup into `Config._initialize_dynamodb_meta(setting)` during Phase 1 (same as `mcp_daemon_engine` did). |
| Gateway `config_init_style` set incorrectly (dict vs kwargs) — ACE uses `Config.initialize(logger, **setting)` (kwargs), not `Config.initialize(logger, setting)` (dict) | High | Set `config_init_style: kwargs` in ACE's `routes.yaml` entry. If set to dict, `Config.initialize` will receive a single dict arg instead of keyword args and fail. Verify in the gateway integration test. |
| ACE not registered in `routes.yaml` — gateway cannot route to ACE dispatch functions | High | Add ACE module entry to `routes.yaml` in Phase 1 close-out. Without this, the gateway cannot forward requests to ACE. |
| `ACE_PG_TABLE_PREFIX` not added to `build_setting_from_env()` — per-module table prefix not forwarded | Medium | Add `"ace_pg_table_prefix": os.getenv("ACE_PG_TABLE_PREFIX", "")` to `build_setting_from_env()` in `app.py`. Without this, `config_overrides` resolves to `None` and the prefix is silently dropped. |
| ACE added to gateway `pyproject.toml` core deps but ACE not installed in all deployments | Medium | Consider adding ACE as an optional dependency (`silvaengine-gateway[ace]`) if the gateway should remain deployable without ACE. |

---

## Environment Variables

### Current `.env.example` (no dual-backend vars)

ACE does not currently have a `.env.example` file. The settings are passed via the SilvaEngine deployment framework.

### New env vars to add

```ini
# Dual-backend selection
db_backend=dynamodb            # "dynamodb" (default) or "postgresql"

# PostgreSQL connection (only used when db_backend=postgresql)
# DATABASE_URL takes precedence over PG_* if set
# DATABASE_URL=postgresql+psycopg2://silvaengine:silvaengine@localhost:5432/silvaengine
PG_HOST=localhost
PG_PORT=5432
PG_USER=silvaengine
PG_PASSWORD=silvaengine
PG_DB=silvaengine
PG_TABLE_PREFIX=               # e.g. "ace_" to prefix all tables (default: "")
ACE_PG_TABLE_PREFIX=           # per-module prefix forwarded by the gateway (default: "")
```

---

## Conftest Setting Mapping

The test `conftest.py` SETTING dict must be extended (following the pattern from `rfq_engine`, AACE, and `knowledge_graph_engine`):

```python
SETTING = {
    # ... existing AWS/API Gateway vars ...
    "db_backend": os.getenv("db_backend", "dynamodb"),
    "db_host": os.getenv("PG_HOST", "localhost"),
    "db_port": os.getenv("PG_PORT", "5432"),
    "db_user": os.getenv("PG_USER", "silvaengine"),
    "db_password": os.getenv("PG_PASSWORD", "silvaengine"),
    "db_schema": os.getenv("PG_DB", "silvaengine"),
    "pg_table_prefix": os.getenv("PG_TABLE_PREFIX", ""),
}
```

---

## pyproject.toml Changes

```toml
[project.optional-dependencies]
postgresql = [
    "SQLAlchemy>=1.4",
    "psycopg2-binary>=2.9",
    "alembic>=1.10",
]
```

PG dependencies must **not** enter the core dependency list, so DynamoDB-only installs stay free of them.

---

## Immediate Next Work

1. **Close Phase 0**: write `docs/PHASE0_ENTITY_INVENTORY.md` with per-field DynamoDB→PostgreSQL type mappings for all 6 entities, and confirm mandatory AWS services in PG mode (Lambda, S3, SES, DynamoDB for `FunctionModel`).
2. **Start Phase 1**: add `Config.DB_BACKEND`, the `models/repositories/` boundary, move PynamoDB modules under `models/dynamodb/`, and migrate all GraphQL call sites (including all `handlers/operation_hub/*`, `handlers/procedure_hub/*`, `handlers/ai_coordination_utility.py`) to `get_repo()` / `get_loaders()`.
3. Move `BaseModel.Meta` setup from `AICoordinationEngine.__init__` into `Config._initialize_dynamodb_meta(setting)`.
4. Update `models/utils.py::get_coordination` to route through `get_repo("coordination").get(...)` and return a normalized dict (not a PynamoDB model).
5. Add the static adoption guard test and the backend-agnostic dispatch test (DynamoDB arm first).
6. Only after Phase 1 is green, begin Phase 2 (PG foundation) and Phase 3 (6-entity port), starting with `coordination` (partition-keyed, RLS, no dependencies) to validate the pattern, then `task` (has `partition_key`, depends on coordination for validation), then `session` (has `partition_key`, LSIs) to exercise RLS and index patterns.
7. For `SessionAgent`, add `partition_key` column in PG (not in DynamoDB) and populate from the parent session on insert. Validate JSONB `agent_action` filtering parity early.
8. **Gateway integration (Phase 1 close-out)**: register ACE in `silvaengine_gateway/routes.yaml`, add `"ai_coordination_engine": "AICoordinationEngine"` to `_DEFAULT_INVOKER_CLASS_NAMES`, add `ace_pg_table_prefix` to `build_setting_from_env()`, and add `ai_coordination_engine` to the gateway's `pyproject.toml`. Verify `init_module_configs()` calls `Config.initialize(logger, **setting)` with the correct `db_backend` and `pg_table_prefix`.