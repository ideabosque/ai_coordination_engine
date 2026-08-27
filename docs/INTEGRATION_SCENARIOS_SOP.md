# Continuous Integration Scenarios SOP — AI Coordination Engine

> **How to use this SOP.** This Standard Operating Procedure tells the
> Autonomous Integration Testing Specialist *what* to test, *in what order*,
> *against which environment*, and *what "done" means* for `ai_coordination_engine`.
>
> This document was drafted from project discovery on 2026-06-29.
> Fields marked `<pending confirmation>` require explicit user approval
> before any test execution begins.

---

## 1. Document Control

| Field | Value |
|---|---|
| SOP title | AI Coordination Engine Dual-Backend Integration Certification SOP |
| Version | 1.0.0-draft |
| Owner / contact | `bibow` |
| Last updated | 2026-06-29 |
| Business domain | `ai_coordination` (multi-agent orchestration / session coordination) |
| Target environment | `local dev` (PostgreSQL-first for this certification) |
| Approval status | `approved` |

### Confirmed Defaults (2026-06-29)

| # | Item | Confirmed value |
|---|---|---|
| 1 | Target environment | local dev for both backends (PostgreSQL-first for this certification) |
| 2 | AACE loopback | mock `ai_agent_core_engine` calls; test handler logic in-process |
| 3 | Async Lambda dispatch | use internal invoke (`execute_mode=local_for_all`, `functs_on_local` mapping) instead of AWS Lambda |
| 4 | Provisioning policy | auto-provision PG schema (`alembic upgrade head` or `Base.metadata.create_all`) |
| 5 | SOP owner | user (bibow) |
| 6 | CI cadence | PR-block: INT-001/002/003/006 smoke; Nightly: full suite; Pre-release: full + resilience + reconciliation |
| 7 | Distribution | project docs + test owner |
| 8 | Sign-off roles | test owner: bibow; others: pending |
| 9 | AACE loopback scope | mocked — handler logic tested in-process; live AACE calls out of scope |
| 10 | Async Lambda scope | internal invoke pattern (`functs_on_local` + `execute_mode=local_for_all`) — no Lambda deployment needed |

## 2. Purpose and Scope

> **Why now.** The repository dispatch boundary adoption is complete and
> enforced by a static adoption guard. DynamoDB is exercised end-to-end.
> PostgreSQL is structurally complete (6 SQLAlchemy models, 7 Alembic
> migrations, 6 PG repository classes, PGRequestLoaders with 8 loader
> properties) and validated against a live PostgreSQL 17 database (14 tests
> pass). This SOP certifies dual-backend runtime parity so PostgreSQL can
> move from "implementation-ready" to "production-ready."

- **In scope:**
  - All 6 persisted entities across both `DB_BACKEND` values (`dynamodb`, `postgresql`).
  - **All test operations (create, update, delete, query, list, validate) must be executed through the GraphQL engine** — `AICoordinationEngine.ai_coordination_graphql(query=..., variables=..., endpoint_id=..., part_id=...)` — with `DB_BACKEND` set to the selected backend. No direct database access (SQLAlchemy queries, PynamoDB model calls, or repository-level method calls) is permitted for transaction testing or validation, except for:
    - **Schema provisioning** (Phase 3: `alembic upgrade head`, `Base.metadata.create_all`).
    - **Asset validation gate** (Phase 7-8: row counts, FK orphan checks — these are reconciliation queries, not business operations).
    - **Reconciliation** (Phase 12: referential integrity, cross-system consistency, count verification — same exception as the gate).
  - GraphQL queries, mutations, and nested resolvers routing through `models.repositories` dispatch.
  - Batch loaders (`RequestLoaders` / `PGRequestLoaders`) for the 8-property nested-resolver surface.
  - RLS (Row-Level Security) enforcement on all 6 tables.
  - Operation Hub workflow: `askOperationHub` query (coordination → session → session_run → async task dispatch).
  - Procedure Hub workflow: `executeProcedureTaskSession` mutation (task → session → session_agents → session_runs).
  - User-in-the-loop workflow: `executeForUserInput` mutation (session_agent state update).
  - JSONB `agent_action` filtering on SessionAgent (primary_path, user_in_the_loop, predecessors, states).
  - Alembic migrations `0001`-`0007` apply cleanly to a disposable PostgreSQL schema.
  - Cache invalidation behavior after mutations (DynamoDB cache config; PG cache config empty by design).
  - Static adoption guard (no `models.dynamodb` imports in `queries/` / `mutations/` / `types/` / `handlers/`).
- **Out of scope:**
  - The `ai_agent_core_engine` companion service (separate engine, separate certification; ACE invokes it via GraphQL loopback for `ask_model` / `get_async_task`).
  - Live external LLM calls (AI *decision-making* is not; prompt *storage* and *retrieval* via coordination `agents` list is in scope).
  - AWS Lambda async dispatch (`async_insert_update_session`, `async_execute_procedure_task_session`, `async_update_session_agent`, `async_orchestrate_task_query`) — these are event-driven Lambda invocations, not synchronous GraphQL operations. The handler logic is in scope; the Lambda invocation mechanism is not.
  - Performance benchmarking beyond a smoke-level timing check (Phase 5 benchmark work is tracked separately in `DUAL_BACKEND_DEVELOPMENT_PLAN.md`).
  - DynamoDB-to-PostgreSQL data migration (no production DynamoDB data exists; both backends start empty).
  - The `silvaengine_gateway` HTTP routing layer (separate service; ACE is tested via in-process GraphQL engine invocation).
- **System(s) under test:** `ai_coordination_engine` GraphQL engine and its persistence layer (`models/dynamodb`, `models/postgresql`, `models/repositories`), running on AWS Lambda-style invocation against DynamoDB and/or PostgreSQL.

## 3. Environment and Access

| Item | Value / source |
|---|---|
| Environment target | `local dev` for both backends (PostgreSQL-first; DynamoDB via localstack or AWS dev) |
| Base URLs / endpoints | GraphQL schema invoked in-process via `AICoordinationEngine` + `Graphql.fetch_graphql_schema`; no HTTP gateway in scope |
| Credential source | `tests/.env` at repo root for local runs (`aws_access_key_id`, `aws_secret_access_key`, `region_name`, `endpoint_id`, `part_id`, `execute_mode`); `DATABASE_URL` or `PG_HOST`/`PG_PORT`/`PG_USER`/`PG_PASSWORD`/`PG_DB` for PostgreSQL |
| Required env vars | `region_name`, `aws_access_key_id`, `aws_secret_access_key`, `endpoint_id`, `part_id`, `execute_mode` (DynamoDB path); `DATABASE_URL` or `PG_*` (PostgreSQL path); `db_backend` (optional, defaults to `dynamodb`); `cache_enabled` (optional) |
| Data stores | DynamoDB (default; 6 tables `ace-*`); PostgreSQL (6 tables; SQLAlchemy + Alembic) |
| Messaging / events | AWS Lambda async dispatch (out of scope); AWS SES email (out of scope); WebSocket connections (out of scope) |
| Access constraints | AWS credentials scoped to the target DynamoDB tables; PostgreSQL credentials scoped to the disposable `ai_coordination_engine` test schema |
| Provisioning policy | Auto-provision the disposable PostgreSQL schema (`Base.metadata.drop_all` + `create_all` or `alembic upgrade head`) and DynamoDB test tables when safe; manual approval required for any cloud credential scope change or production access |

> **Names and sources only — never paste secrets, tokens, or connection strings.**

## 4. Dependency Readiness Requirements

> Each dependency must reach all four readiness states before testing begins:
> `available -> configured -> initialized -> operational`.

| Dependency | Type | Health check | Required readiness | Owner |
|---|---|---|---|---|
| DynamoDB (`ace-*` tables) | infrastructure | `initialize_tables(logger)` succeeds; `CoordinationModel.exists()` | operational | `bibow` |
| PostgreSQL (disposable schema) | infrastructure | `DATABASE_URL` reachable; `SELECT 1`; `alembic upgrade head` or `Base.metadata.create_all` | initialized | `bibow` |
| AWS credentials (Lambda, S3, SES) | infrastructure | `boto3.client("lambda").list_functions()` (or scoped equivalent) | configured | `<pending>` |
| `silvaengine_dynamodb_base` | internal (library) | import + `BaseModel` meta initialized | operational | SilvaEngine team |
| `silvaengine_utility` | internal (library) | import + `HybridCacheEngine` instantiable | operational | SilvaEngine team |
| `silvaengine_constants` | internal (library) | import + `InvocationType` accessible | operational | SilvaEngine team |
| `graphene` / `promise` | internal (library) | import + schema builds | operational | open-source |
| `tenacity` | internal (library) | import + retry decorator works | operational | open-source |
| `SQLAlchemy>=1.4` / `psycopg2-binary` / `alembic` | internal (library, PG-only) | import; installed via `ai-coordination-engine[postgresql]` extras | configured | open-source |
| Repository dispatch boundary | internal (module) | `get_repo("coordination")` resolves under both backends; `get_loaders({})` returns correct loader type | operational | ACE team |
| Alembic migration set `0001`-`0007` | internal (module) | `alembic upgrade head` applies cleanly to empty schema | initialized | ACE team |
| `ai_agent_core_engine` (loopback) | external (service) | GraphQL loopback for `invoke_ask_model` / `get_async_task` reachable | configured | AACE team |

## 5. Test Data Requirements

| Asset type | Count | Notes / constraints |
|---|---|---|
| Coordinations | 3 | One with 2 task agents + 1 triage agent; one with 1 decompose agent + 2 task agents; one with 1 planning agent + 5 task agents |
| Tasks | 3 | One per coordination; each with `initial_task_query`, `subtask_queries`, `agent_actions` (predecessor graph) |
| Task schedules | 2 | One `active`, one `initial`; both linked to the same task |
| Sessions | 5 | One per operation_hub call + one per procedure_hub call + one for user-in-the-loop |
| Session agents | 6+ | At least 2 per procedure session; cover in_degree=0 (root) and in_degree>0 (dependent); cover states: initial, pending, executing, completed, failed, wait_for_user_input |
| Session runs | 4+ | At least one per session_agent execution; cover thread_uuid linkage |
| Users / roles | 2 | Admin (`admin@company.com`), user (`user@company.com`) — used as `updated_by` / `user_id` |

- **Load order:** master data (coordination) → task → task_schedule → session → session_agent → session_run.
- **Data source:** generated by test scripts that drive data through the GraphQL engine via the repository dispatch boundary — the same mutations production traffic uses. Scripts are backend-agnostic: `DB_BACKEND=dynamodb` or `DB_BACKEND=postgresql` (plus `PG_*` env vars) controls which backend receives the data.

### Seed Script Execution Sequence

| Step | Script | Reads | Writes | Entities created |
|---|---|---|---|---|
| 1 | `prepare_coordinations.py` | — | `coordinations.json` | Coordination (3, with agents lists) |
| 2 | `prepare_tasks.py` | `coordinations.json` | `tasks.json` | Task (3, with subtask_queries + agent_actions) |
| 3 | `prepare_task_schedules.py` | `tasks.json` | `task_schedules.json` | TaskSchedule (2) |
| 4 | `prepare_sessions.py` | `coordinations.json` + `tasks.json` | `sessions.json` | Session (5) |
| 5 | `prepare_session_agents.py` | `sessions.json` + `tasks.json` | `session_agents.json` | SessionAgent (6+, with agent_action predecessor graph) |
| 6 | `prepare_session_runs.py` | `sessions.json` + `session_agents.json` | `session_runs.json` | SessionRun (4+, with thread_uuid + async_task_uuid) |

**Backend selection** (env vars):
- `DB_BACKEND=dynamodb` (default) — uses `region_name` / `aws_access_key_id` / `aws_secret_access_key` from `tests/.env`
- `DB_BACKEND=postgresql` — uses `PG_HOST` / `PG_PORT` / `PG_USER` / `PG_PASSWORD` / `PG_DB` (or `DATABASE_URL`) from `tests/.env`

**Prerequisites:**
- `tests/.env` configured with `endpoint_id`, `part_id`, `execute_mode=local_for_all`, and backend-specific credentials
- For PostgreSQL: `alembic -c migration/alembic.ini upgrade head` applied first (schema must exist before data loading)

## 6. Execution Order

> Dependency-driven order derived from the entity relationship matrix
> (parent → child, and the dispatch boundary as the entry point).

### 6.1 Model Dependency Matrix

Every entity has soft foreign keys (UUID strings; not enforced by DynamoDB,
enforced by application logic). A child entity cannot be created until its
parent exists.

| # | Child entity | Parent entity | FK field on child | Notes |
|---|---|---|---|---|
| 1 | Coordination | — (root) | — | Tenant-partitioned (hash=partition_key); contains `agents` list |
| 2 | Task | Coordination | `coordination_uuid` | Hash=coordination_uuid; has `partition_key` for RLS; validates `subtask_queries` + `agent_actions` against coordination's `agents` |
| 3 | TaskSchedule | Task | `task_uuid` | Hash=task_uuid; has `partition_key` + `coordination_uuid` |
| 4 | Session | Coordination | `coordination_uuid` | Hash=coordination_uuid; has `partition_key` for RLS; optional `task_uuid` |
| 5 | SessionAgent | Session | `session_uuid` | Hash=session_uuid; `partition_key` ADDED in PG for RLS; `agent_action` JSONB with predecessor graph |
| 6 | SessionRun | Session | `session_uuid` | Hash=session_uuid; `partition_key` nullable; `thread_uuid` + `agent_uuid` + `async_task_uuid`; optional `session_agent_uuid` |

**Cascading delete protection** (parent cannot be deleted while children exist):
- Coordination ← Session, Task, TaskSchedule
- Task ← TaskSchedule, Session (via task_uuid)
- Session ← SessionAgent, SessionRun

**Cross-entity validation:**
- `Task.insert_update` validates `subtask_queries` and `agent_actions` agent UUIDs against the coordination's `agents` list (via `get_repo("coordination").get()`)
- `SessionAgent.list` filters on `agent_action` JSONB fields: `primary_path`, `user_in_the_loop`, `predecessors`

### 6.2 Execution Sequence

The certification run proceeds in two phases: **asset loading** (Phase 7 + Phase 8) and **transaction testing** (Phase 9 + Phase 10). **All test assets must be loaded and validated before any transaction scenario executes.**

#### Phase A: Asset Loading (must complete before Phase B)

```text
1. Schema provisioning
   -> alembic upgrade head (PostgreSQL) or initialize_tables (DynamoDB)

2. Seed scripts in dependency order (Section 5 seed-script sequence):
   prepare_coordinations.py      -> Coordination (3)
   prepare_tasks.py              -> Task (3)
   prepare_task_schedules.py     -> TaskSchedule (2)
   prepare_sessions.py           -> Session (5)
   prepare_session_agents.py     -> SessionAgent (6+)
   prepare_session_runs.py       -> SessionRun (4+)

3. Asset validation gate:
   -> row counts per table > 0 for all loaded entities
   -> referential integrity clean (no orphaned children)
   -> coordination.agents populated for all coordinations
   -> task.agent_actions and task.subtask_queries populated
   -> session_agent.agent_action populated with predecessor graph
```

#### Phase B: Transaction Testing (executes after Phase A gate passes)

```text
4. Backend parity smoke (INT-001, INT-002)
   -> dispatch resolves all 6 entities under both backends
   -> static adoption guard: 0 violations

5. Entity CRUD scenarios (INT-003 through INT-008)
   -> coordination, task, task_schedule, session, session_agent, session_run

6. Workflow scenarios (INT-009 through INT-012)
   -> operation hub, procedure hub, user-in-the-loop, async listeners

7. Backend parity (INT-013)
   -> same GraphQL workflow under PostgreSQL

8. Infrastructure scenarios (INT-014, INT-015)
   -> Alembic migrations, RLS enforcement

9. Resilience scenarios (Section 8)
   -> missing data, invalid data, API failures, cache failures

10. Reconciliation (Section 9)
    -> referential integrity, count consistency, backend parity
```

### 6.3 Transaction Scenario Dependency Graph

```text
INT-001 (dispatch smoke) -----> INT-013 (backend parity)
INT-002 (adoption guard) -----> INT-013
     |
     v
INT-003 (coordination CRUD) ---> INT-009 (operation hub)
     |                      ---> INT-011 (procedure hub)
     v
INT-004 (task CRUD) ---------> INT-011 (procedure hub)
     |
     v
INT-005 (task_schedule CRUD)
     |
INT-006 (session CRUD) ------> INT-009 (operation hub)
     |                      ---> INT-011 (procedure hub)
     v
INT-007 (session_agent CRUD) -> INT-011 (procedure hub)
     |                       ---> INT-012 (user-in-the-loop)
     v
INT-008 (session_run CRUD) --> INT-009 (operation hub)
     |
INT-009 (operation hub) -----> INT-013 (backend parity)
INT-010 (JSONB filter)
INT-011 (procedure hub) -----> INT-013 (backend parity)
INT-012 (user-in-the-loop) --> INT-013 (backend parity)
INT-014 (alembic migrations)
INT-015 (RLS enforcement)
```

## 7. Integration Scenarios

### INT-001 — Repository dispatch smoke test

| Field | Value |
|---|---|
| **ID** | INT-001 |
| **Name** | `get_repo()` resolves all 6 entities under both backends |
| **Priority** | P1 |
| **Type** | smoke |
| **CI trigger** | on pull request |
| **Preconditions** | `Config.DB_BACKEND` settable; both backend registries importable |
| **Dependencies** | Repository dispatch boundary |
| **Test data** | none |
| **Steps** | 1. Set `Config.DB_BACKEND="dynamodb"`. 2. `get_repo("coordination")` → verify `entity_type == "coordination"`. 3. Repeat for all 6 entities. 4. Set `Config.DB_BACKEND="postgresql"`. 5. Repeat all 6. 6. Verify both backends register identical entity sets. |
| **Expected behavior** | All 6 entities resolve with matching `entity_type` under both backends |
| **Validation points** | dynamodb_resolves, postgresql_resolves, identical_entity_sets |
| **Cross-system checks** | `set(ddb_registry) == set(pg_registry) == {coordination, session, session_agent, session_run, task, task_schedule}` |

### INT-002 — Static adoption guard

| Field | Value |
|---|---|
| **ID** | INT-002 |
| **Name** | No `models.dynamodb` imports in GraphQL layer |
| **Priority** | P1 |
| **Type** | static analysis |
| **CI trigger** | on pull request |
| **Preconditions** | None |
| **Dependencies** | `test_dual_backend_guard.py` |
| **Test data** | none |
| **Steps** | 1. Run `test_dual_backend_guard.py::TestAdoptionGuard` for `queries`, `mutations`, `types`, `handlers`. 2. Verify 0 violations across all 4 directories. |
| **Expected behavior** | Zero forbidden imports or free-function calls |
| **Validation points** | queries_clean, mutations_clean, types_clean, handlers_clean |
| **Cross-system checks** | Violation count == 0 |

### INT-003 — Coordination CRUD

| Field | Value |
|---|---|
| **ID** | INT-003 |
| **Name** | Create, read, update, delete a coordination through GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end |
| **CI trigger** | on pull request |
| **Preconditions** | Schema provisioned; `Config.initialize` succeeds |
| **Dependencies** | `coordination` repository |
| **Test data** | 1 coordination with 3 agents |
| **Steps** | 1. `mutation insertUpdateCoordination` with `coordinationName`, `coordinationDescription`, `agents` (list of 3 agent maps with `agent_uuid`, `agent_name`, `agent_type`, `agent_description`). 2. `query coordination(coordinationUuid: ...)` verify all fields. 3. `mutation insertUpdateCoordination` update `coordinationName`. 4. `query coordination` verify updated name. 5. `query coordinationList` verify `total >= 1`. 6. `mutation deleteCoordination` verify `ok == true`. 7. `query coordination` verify `null`. |
| **Expected behavior** | Insert returns coordination type; get returns all fields; update changes name; list returns correct total; delete returns true; post-delete get returns null |
| **Validation points** | insert_returns_type, get_returns_fields, update_changes_name, list_returns_total, delete_returns_true, post_delete_null |
| **Cross-system checks** | `agents` list length == 3; `updated_at` advances on update |

### INT-004 — Task CRUD with agent validation

| Field | Value |
|---|---|
| **ID** | INT-004 |
| **Name** | Create, read, update, delete a task with agent UUID validation |
| **Priority** | P1 |
| **Type** | end-to-end |
| **CI trigger** | nightly |
| **Preconditions** | INT-003 coordination exists |
| **Dependencies** | `task` repository, `coordination` repository (for validation) |
| **Test data** | 1 task with subtask_queries and agent_actions |
| **Steps** | 1. `mutation insertUpdateTask` with `coordinationUuid`, `taskName`, `taskDescription`, `initialTaskQuery`, `subtaskQueries` (list of maps with `agent_uuid` + `subtask_query`), `agentActions` (map of agent_uuid → action with predecessors). 2. `query task(coordinationUuid: ..., taskUuid: ...)` verify all fields. 3. `mutation insertUpdateTask` with invalid `agent_uuid` in `subtaskQueries` → verify filtered out. 4. `query taskList(coordinationUuid: ...)` verify `total >= 1`. 5. `mutation deleteTask` verify `ok == true`. |
| **Expected behavior** | Insert returns task type; agent UUIDs validated against coordination's agents; invalid UUIDs filtered from subtask_queries and agent_actions; list returns correct total |
| **Validation points** | insert_returns_type, agent_validation_filters, list_returns_total, delete_returns_true |
| **Cross-system checks** | `subtask_queries` only contains agent_uuids from coordination's agents list |

### INT-005 — TaskSchedule CRUD

| Field | Value |
|---|---|
| **ID** | INT-005 |
| **Name** | Create, read, update, delete a task schedule |
| **Priority** | P2 |
| **Type** | end-to-end |
| **CI trigger** | nightly |
| **Preconditions** | INT-004 task exists |
| **Dependencies** | `task_schedule` repository |
| **Test data** | 2 schedules (active + initial) |
| **Steps** | 1. `mutation insertUpdateTaskSchedule` with `taskUuid`, `coordinationUuid`, `schedule` (cron expression), `status="initial"`. 2. `query taskSchedule(taskUuid: ..., scheduleUuid: ...)` verify fields. 3. `mutation insertUpdateTaskSchedule` update `status="active"`. 4. `query taskScheduleList(taskUuid: ...)` verify `total >= 1`. 5. `mutation deleteTaskSchedule` verify `ok == true`. |
| **Expected behavior** | Insert returns schedule type; status update works; list filters by task_uuid; delete returns true |
| **Validation points** | insert_returns_type, status_update, list_filters, delete_returns_true |
| **Cross-system checks** | `schedule_uuid` present; `status` transitions initial → active |

### INT-006 — Session CRUD

| Field | Value |
|---|---|
| **ID** | INT-006 |
| **Name** | Create, read, update, delete a session |
| **Priority** | P1 |
| **Type** | end-to-end |
| **CI trigger** | on pull request |
| **Preconditions** | INT-003 coordination exists |
| **Dependencies** | `session` repository |
| **Test data** | 1 session with status, task_query, user_id |
| **Steps** | 1. `mutation insertUpdateSession` with `coordinationUuid`, `userId`, `taskQuery`, `status="initial"`. 2. `query session(coordinationUuid: ..., sessionUuid: ...)` verify all fields including `partitionKey`. 3. `mutation insertUpdateSession` update `status="active"`, `iterationCount=1`. 4. `query sessionList(coordinationUuid: ...)` verify `total >= 1`. 5. `mutation insertUpdateSession` update `logs` (JSON string). 6. `mutation deleteSession` verify `ok == true`. |
| **Expected behavior** | Insert returns session type; `partition_key` populated from context; status update works; list filters by coordination_uuid; logs update works; delete returns true |
| **Validation points** | insert_returns_type, partition_key_populated, status_update, list_filters, logs_update, delete_returns_true |
| **Cross-system checks** | `partition_key == endpoint_id#part_id` from context |

### INT-007 — SessionAgent CRUD with JSONB agent_action

| Field | Value |
|---|---|
| **ID** | INT-007 |
| **Name** | Create, read, update, delete a session agent with agent_action JSONB |
| **Priority** | P1 |
| **Type** | end-to-end |
| **CI trigger** | nightly |
| **Preconditions** | INT-006 session exists |
| **Dependencies** | `session_agent` repository |
| **Test data** | 2 session agents with agent_action (primary_path, predecessors, user_in_the_loop) |
| **Steps** | 1. `mutation insertUpdateSessionAgent` with `sessionUuid`, `coordinationUuid`, `agentUuid`, `agentAction` (map: `primary_path=true`, `user_in_the_loop=null`, `predecessors=[]`, `action_function={}`). 2. `query sessionAgent(sessionUuid: ..., sessionAgentUuid: ...)` verify `agentAction` map. 3. `mutation insertUpdateSessionAgent` update `state="executing"`, `inDegree=1`. 4. `query sessionAgentList(sessionUuid: ...)` verify `total >= 1`. 5. `mutation deleteSessionAgent` verify `ok == true`. |
| **Expected behavior** | Insert returns session agent type; `agent_action` JSONB populated with default merge; state/in_degree update works; list filters by session_uuid; delete returns true |
| **Validation points** | insert_returns_type, agent_action_populated, state_update, in_degree_update, list_filters, delete_returns_true |
| **Cross-system checks** | `agent_action.primary_path == true`; `partition_key` populated in PG (not in GraphQL type) |

### INT-008 — SessionRun CRUD

| Field | Value |
|---|---|
| **ID** | INT-008 |
| **Name** | Create, read, update, delete a session run |
| **Priority** | P1 |
| **Type** | end-to-end |
| **CI trigger** | nightly |
| **Preconditions** | INT-006 session exists |
| **Dependencies** | `session_run` repository |
| **Test data** | 1 session run with thread_uuid, agent_uuid, async_task_uuid |
| **Steps** | 1. `mutation insertUpdateSessionRun` with `sessionUuid`, `runUuid`, `threadUuid`, `agentUuid`, `coordinationUuid`, `asyncTaskUuid`, `updatedBy="operation_hub"`. 2. `query sessionRun(sessionUuid: ..., runUuid: ...)` verify all fields. 3. `query sessionRunList(sessionUuid: ...)` verify `total >= 1`. 4. `mutation deleteSessionRun` verify `ok == true`. |
| **Expected behavior** | Insert returns session run type; all FK fields populated; list filters by session_uuid; delete returns true |
| **Validation points** | insert_returns_type, fk_fields_populated, list_filters, delete_returns_true |
| **Cross-system checks** | `thread_uuid` and `async_task_uuid` present; `partition_key` populated from context |

### INT-009 — Operation Hub workflow (askOperationHub)

| Field | Value |
|---|---|
| **ID** | INT-009 |
| **Name** | `askOperationHub` creates session, invokes AI model, records session run |
| **Priority** | P1 |
| **Type** | end-to-end (workflow) |
| **CI trigger** | pre-release |
| **Preconditions** | INT-003 coordination exists with agents; `ai_agent_core_engine` loopback reachable (or mocked) |
| **Dependencies** | `coordination`, `session`, `session_run` repositories; `handlers.operation_hub`; `ai_coordination_utility.invoke_ask_model` |
| **Test data** | 1 coordination with triage + task agents |
| **Steps** | 1. `query askOperationHub(coordinationUuid: ..., userId: ..., userQuery: "test query", stream: false)` . 2. Verify response contains `sessionUuid`, `runUuid`, `threadUuid`, `agentUuid`, `asyncTaskUuid`. 3. `query session(coordinationUuid: ..., sessionUuid: ...)` verify `status` advanced from `initial`. 4. `query sessionRun(sessionUuid: ..., runUuid: ...)` verify `threadUuid` and `agentUuid` match response. 5. Verify async Lambda dispatch triggered for `async_insert_update_session`. |
| **Expected behavior** | Coordination resolved; session created/updated; triage or specified agent selected; AI model invoked via loopback; session_run recorded; async update dispatched |
| **Validation points** | coordination_resolved, session_created, agent_selected, ask_model_invoked, session_run_recorded, async_dispatched |
| **Cross-system checks** | `session_run.agent_uuid` matches selected agent from coordination's agents list |

### INT-010 — SessionAgent JSONB filter parity

| Field | Value |
|---|---|
| **ID** | INT-010 |
| **Name** | `sessionAgentList` JSONB filtering (primary_path, user_in_the_loop, predecessors, states) |
| **Priority** | P1 |
| **Type** | end-to-end (filter parity) |
| **CI trigger** | nightly |
| **Preconditions** | INT-007 session agents exist with varied `agent_action` |
| **Dependencies** | `session_agent` repository |
| **Test data** | 3+ session agents with different `primary_path`, `predecessors`, `state` |
| **Steps** | 1. `query sessionAgentList(sessionUuid: ..., primaryPath: true)` → verify only agents with `agent_action.primary_path == true` returned. 2. `query sessionAgentList(sessionUuid: ..., states: ["initial", "pending"])` → verify only agents in those states. 3. `query sessionAgentList(sessionUuid: ..., predecessor: "agent-uuid-1")` → verify only agents whose `agent_action.predecessors` contains that UUID. 4. `query sessionAgentList(sessionUuid: ..., predecessors: ["uuid-1", "uuid-2"])` → verify only agents whose `agent_uuid` is in the list. 5. `query sessionAgentList(sessionUuid: ..., inDegree: 0)` → verify only root agents. |
| **Expected behavior** | JSONB filters return correct subsets; combination of filters narrows correctly; results match between DynamoDB and PostgreSQL |
| **Validation points** | primary_path_filter, states_filter, predecessor_filter, predecessors_filter, in_degree_filter |
| **Cross-system checks** | Filter result counts identical between DynamoDB and PostgreSQL for the same data |

### INT-011 — Procedure Hub workflow (executeProcedureTaskSession)

| Field | Value |
|---|---|
| **ID** | INT-011 |
| **Name** | `executeProcedureTaskSession` creates session, initializes session agents, dispatches orchestration |
| **Priority** | P1 |
| **Type** | end-to-end (workflow) |
| **CI trigger** | pre-release |
| **Preconditions** | INT-004 task exists with subtask_queries and agent_actions; `ai_agent_core_engine` loopback reachable (or mocked) |
| **Dependencies** | `task`, `session`, `session_agent` repositories; `handlers.procedure_hub`; `session_agent.init_session_agents`, `init_in_degree` |
| **Test data** | 1 task with 2 task agents and predecessor graph |
| **Steps** | 1. `mutation executeProcedureTaskSession(coordinationUuid: ..., taskUuid: ..., taskQuery: "test")`. 2. Verify response contains `sessionUuid`, `taskUuid`, `taskQuery`. 3. `query session(coordinationUuid: ..., sessionUuid: ...)` verify `status` is `dispatched` or `in_transit`. 4. `query sessionAgentList(sessionUuid: ...)` verify session agents initialized for each task agent. 5. Verify each session agent has `in_degree` set (0 for root, >0 for dependent). 6. Verify async Lambda dispatch triggered for `async_execute_procedure_task_session`. |
| **Expected behavior** | Task resolved; session created; session agents initialized for each task agent in the coordination; in_degree computed from predecessor graph; async orchestration dispatched |
| **Validation points** | task_resolved, session_created, agents_initialized, in_degree_computed, async_dispatched |
| **Cross-system checks** | `session_agent.in_degree` matches predecessor graph: root agents have 0, dependent agents have count of predecessors |

### INT-012 — User-in-the-loop workflow (executeForUserInput)

| Field | Value |
|---|---|
| **ID** | INT-012 |
| **Name** | `executeForUserInput` updates session agent with user input and triggers next iteration |
| **Priority** | P2 |
| **Type** | end-to-end (workflow) |
| **CI trigger** | nightly |
| **Preconditions** | INT-011 procedure session exists with a session agent in `wait_for_user_input` state |
| **Dependencies** | `session_agent` repository; `handlers.procedure_hub.user_in_the_loop` |
| **Test data** | 1 session agent in `wait_for_user_input` state |
| **Steps** | 1. `mutation executeForUserInput(sessionUuid: ..., sessionAgentUuid: ..., userInput: "user response")`. 2. Verify `ok == true`. 3. `query sessionAgent(sessionUuid: ..., sessionAgentUuid: ...)` verify `userInput` updated. 4. Verify `state` transitioned to `pending` (if action_function) or `completed` (if no action_function). 5. Verify `handle_session_agent_completion` decrements successor in_degree if completed. |
| **Expected behavior** | User input recorded; state transitions based on action_function presence; completion cascades to successors; next iteration invoked |
| **Validation points** | user_input_recorded, state_transitioned, completion_cascaded, next_iteration_invoked |
| **Cross-system checks** | If state == `completed`, successor agents' `in_degree` decremented |

### INT-013 — Backend parity: same GraphQL workflow under PostgreSQL

| Field | Value |
|---|---|
| **ID** | INT-013 |
| **Name** | INT-003 through INT-012 pass identically under `DB_BACKEND=postgresql` |
| **Priority** | P1 |
| **Type** | end-to-end (backend parity) |
| **CI trigger** | pre-release |
| **Preconditions** | PostgreSQL disposable schema provisioned; `alembic upgrade head` applied |
| **Dependencies** | All entity repositories (PG), `PGRequestLoaders` |
| **Test data** | Same fixtures as DynamoDB scenarios |
| **Steps** | 1. `Config.initialize(db_backend="postgresql", ...)`. 2. Run INT-003 through INT-012 via `AICoordinationEngine.ai_coordination_graphql` against PostgreSQL. 3. Compare GraphQL responses field-by-field with the DynamoDB run. |
| **Expected behavior** | Identical GraphQL responses (within numeric tolerance); same status transitions; same JSONB filter results |
| **Validation points** | pg_crud_matches, pg_workflow_matches, pg_jsonb_filter_matches |
| **Cross-system checks** | Per-field diff between DynamoDB and PostgreSQL outputs == 0 (numeric tolerance 0.01) |

### INT-014 — Alembic migrations apply to empty PostgreSQL

| Field | Value |
|---|---|
| **ID** | INT-014 |
| **Name** | `alembic upgrade head` creates all 6 tables + RLS policies cleanly |
| **Priority** | P1 |
| **Type** | database |
| **CI trigger** | pre-release |
| **Preconditions** | Empty PostgreSQL schema; `DATABASE_URL` set |
| **Dependencies** | `migration/alembic/`, all 7 migration files |
| **Test data** | none |
| **Steps** | 1. Drop all ACE tables. 2. `alembic -c migration/alembic.ini upgrade head`. 3. Verify all 6 tables exist (`ace_coordinations`, `ace_sessions`, `ace_session_agents`, `ace_session_runs`, `ace_tasks`, `ace_task_schedules`). 4. Verify `ace_alembic_version` table at `0007`. 5. Verify RLS policies on all 6 tables (`SELECT tablename, policyname FROM pg_policies WHERE tablename LIKE 'ace_%'`). 6. `alembic downgrade -1`; verify last migration reversed. 7. `alembic upgrade head`; verify restored. |
| **Expected behavior** | All migrations apply forward and reverse without error; final revision `0007`; RLS policies on all 6 tables |
| **Validation points** | migrations_applied, revision_correct, rls_policies_created, downgrade_works |
| **Cross-system checks** | Table count == 6; RLS policy count == 6; `ace_alembic_version.version_num == "0007"` |

### INT-015 — RLS tenant isolation enforcement

| Field | Value |
|---|---|
| **ID** | INT-015 |
| **Name** | Non-superuser session with tenant A's partition_key cannot read tenant B's rows |
| **Priority** | P1 |
| **Type** | security |
| **CI trigger** | pre-release |
| **Preconditions** | PostgreSQL with RLS enabled; non-superuser role `aace_app` created and granted table access |
| **Dependencies** | RLS policies (migration `0007`); `Config._set_rls_context` |
| **Test data** | 2 coordinations in different tenants |
| **Steps** | 1. Insert coordination for tenant A (`partition_key = "endpoint_a#part_a"`) as admin (superuser). 2. Insert coordination for tenant B (`partition_key = "endpoint_b#part_b"`) as admin. 3. Switch to non-superuser session (`aace_app` role). 4. `SET LOCAL app.tenant_id = 'endpoint_a#part_a'`. 5. `get_repo("coordination").get(partition_key="endpoint_a#part_a", coordination_uuid=...)` → verify returns data. 6. `get_repo("coordination").get(partition_key="endpoint_b#part_b", coordination_uuid=...)` → verify returns `None` (RLS blocks). 7. Repeat for all 6 entity tables (create cross-tenant records, verify RLS blocks cross-tenant reads). |
| **Expected behavior** | Non-superuser can read own tenant's data; cannot read other tenant's data; superuser bypasses RLS |
| **Validation points** | own_tenant_readable, cross_tenant_blocked, rls_enforced_on_all_tables |
| **Cross-system checks** | Cross-tenant `get()` returns `None` for all 6 entity types |

## 8. Failure and Resilience Scenarios

| Scenario | Injected fault | Expected behavior |
|---|---|---|
| missing_data | Query unknown `coordination_uuid` / `session_uuid` | Resolver returns `null`; no exception surfaces to GraphQL client |
| invalid_data | Task with `subtask_queries` referencing non-existent agent UUID | Invalid entries filtered out by `insert_update_task` validation; valid entries persisted |
| api_failures | Repository `insert_update` raises mid-commit | Transaction rolls back; `session.rollback()` called; error re-raised with traceback logged |
| database_failures | PostgreSQL connection drop mid-query | `pool_pre_ping=True` detects; retry or graceful error; no silent corruption |
| authentication_failures | AWS credentials missing in DynamoDB mode | `Config.initialize` raises; engine fails fast |
| service_outages | DynamoDB table missing / PostgreSQL schema not provisioned | `initialize_tables` raises; tests skip with explicit reason |
| third_party_outages | `ai_agent_core_engine` loopback unreachable for `invoke_ask_model` | `askOperationHub` raises with error logged; no partial session state corruption |
| cache_failures | `HybridCacheEngine` miss/stale | SafeDataLoader falls back to fresh query; `normalize_model` normalizes cached shape |
| rls_bypass_attempt | Superuser session queries cross-tenant data | Superuser bypasses RLS by design; application must set `app.tenant_id` for non-superuser roles |
| predecessor_cycle | `agent_actions` predecessors form a cycle | `init_in_degree` produces incorrect in_degree values; `MAX_ITERATIONS` safety limit in `_handle_pending_agents` prevents infinite loop |
| max_iterations | Session stuck in pending state for >10 iterations | `_handle_pending_agents` detects `iteration_count >= MAX_ITERATIONS`; session marked `failed` with error log |

## 9. Data Reconciliation Checks

| Check | Rule | Tolerance |
|---|---|---|
| Referential integrity | No orphaned sessions (every `coordination_uuid` resolves to a coordination); no orphaned session_agents (every `session_uuid` resolves); no orphaned session_runs | 0 |
| Count consistency | Entities created == entities persisted (per type) | 0 |
| Backend parity | DynamoDB result == PostgreSQL result for the same scenario (field-by-field) | numeric: 0.01; otherwise exact |
| Cache freshness | Post-mutation query returns updated field values (no stale reads) | 0 mismatches |
| Agent validation | `task.subtask_queries` only contains `agent_uuid` values from coordination's `agents` list | 0 invalid |
| In-degree correctness | `session_agent.in_degree == count of predecessors in agent_action.predecessors` | 0 |
| Timestamp drift | `updated_at` advances on every successful mutation | 0 (must strictly increase) |
| Audit completeness | Every `insert_update` sets `updated_by` and `updated_at` | 0 missing |
| RLS enforcement | Cross-tenant `get()` returns `None` for non-superuser sessions | 0 cross-tenant reads |
| JSONB filter parity | Same filter produces same result count under DynamoDB and PostgreSQL | 0 diff |
| Agent_action structure | `agent_action` contains `primary_path`, `user_in_the_loop`, `predecessors`, `action_function` keys | 0 missing keys |

## 10. Entry and Exit Criteria

**Entry criteria (transaction testing may begin when):**

**Phase A — Asset Loading gate (all must pass before Phase B):**
- Environment validated: `Config.initialize` succeeds for the active backend; `initialize_tables` completes; `SELECT 1` (PostgreSQL) or `CoordinationModel.exists()` (DynamoDB) passes.
- All P1 dependencies operational: dispatch boundary, repository registry (both backends), `Config.DB_BACKEND` selectable.
- Schema provisioned: `alembic upgrade head` (PostgreSQL) or `initialize_tables` (DynamoDB) completes; all 6 entity tables exist.
- Seed scripts executed in dependency order (Section 5 seed-script sequence).
- Asset validation: row counts per table > 0 for all loaded entities; referential integrity clean; `agents` lists populated; `agent_actions` and `subtask_queries` populated; `agent_action` predecessor graph valid.
- `tests/test_dual_backend_guard.py` passes (INT-001, INT-002).

**Phase B — Transaction Testing (executes after Phase A gate passes):**
- All Phase A entry criteria met.
- Scenarios execute in the order defined by Section 6.3.
- A scenario may only run if its upstream dependencies have passed.

**Exit criteria (certification may be issued when):**
- All P1 scenarios pass (INT-001, INT-002, INT-003, INT-004, INT-006, INT-007, INT-008, INT-009, INT-010, INT-011, INT-013, INT-014, INT-015).
- Coverage ≥ 80% of scenarios in Section 7 executed (not skipped).
- No blocking defects open.
- Reconciliation checks (Section 9) all clean within tolerance.
- Backend parity (INT-013) shows zero field-level diffs between DynamoDB and PostgreSQL for the mirrored scenarios.

## 11. CI Trigger and Cadence

| Trigger | Scope run | Required to pass |
|---|---|---|
| On pull request | INT-001, INT-002, INT-003, INT-006 (smoke) | yes — blocks merge |
| Nightly | INT-001 through INT-012 + resilience (Section 8) | report only (non-blocking) |
| Pre-release | Full suite INT-001 through INT-015 + resilience (Section 8) + reconciliation (Section 9) | yes — blocks release |

> CI cadence targets are `<pending confirmation>` until the team confirms the
> PR-block vs nightly-report split.

## 12. Reporting and Certification Expectations

### 12.1 Report Format and Location

- **Report format:** `markdown`
- **Location:** written to the target project's `docs/` directory:
  - Stable: `docs/integration_certification_report.md` (latest certification)
  - Dated: `docs/live_integration_results_<YYYYMMDD>.md` (per-run archive)
- **Required certification decision:** one of `Integration Certified`, `Ready for UAT`, `Ready for Production`, `Ready with Conditions`, `Not Ready`
- **Distribution:** `bibow` (test owner + release manager)

### 12.2 Required Report Sections

1. **Header metadata** — generated-at, project, domain, environment, endpoint, partition, SOP reference, execution order, pass/fail/skipped/blocked counts, certification status.
2. **Executive Summary** — 3-6 sentences: what was certified, against which environment, headline result, blocking issues, certification decision.
3. **Scope** — in scope, out of scope, phases executed, phases skipped (with reason).
4. **Dependency Readiness** — table with Available / Configured / Initialized / Operational per dependency.
5. **Function Results** — one block per call (see Section 12.3 below).
6. **End-to-End Workflow Validation** — table: workflow, steps executed, validation points, result.
7. **Failure and Resilience Results** — table: scenario, injected fault, expected behavior, observed behavior, result.
8. **Data Reconciliation** — table: check, rule, tolerance, observed, result.
9. **Coverage Analysis** — table: area, covered, total, %, notes.
10. **Defect Analysis** — table: ID, severity, title, root cause, affected calls, recommendation.
11. **Open Risks and Mitigation Plan** — table: risk, likelihood, impact, mitigation, owner.
12. **Certification Decision** — status, rationale, conditions, evidence sources.
13. **Sign-off** — role, name, date, decision.

### 12.3 Function Results — Per-Call Recording Format

> Every GraphQL operation, CLI command, pytest invocation, SQL query, and
> function call executed during the certification run must be recorded as a
> separate block in the Function Results section, **in execution order**.

Each call block must contain:

| Field | Required | Description |
|---|---|---|
| **Number** | yes | Sequential call number (1, 2, 3, ...) |
| **Group** | yes | Logical group: `Environment`, `Schema`, `Dependency`, `Seed`, `Tests`, `Transaction`, `Resilience`, `Reconciliation` |
| **Method** | yes | The exact method/function/CLI invoked (e.g. `alembic upgrade head`, `pytest test_dual_backend_guard.py`, `AICoordinationEngine.ai_coordination_graphql`) |
| **Short description** | yes | One-line summary of what the call does |
| **Status** | yes | `pass`, `fail`, `error`, `skipped`, or `blocked` |
| **Elapsed** | yes | Duration in milliseconds or seconds |
| **Scenario ID** | yes | SOP scenario reference (e.g. `INT-001`, `INT-009`) |
| **Arguments** | yes | Exact input arguments as JSON (command args, env vars, GraphQL variables, function kwargs) |
| **Output** | yes | Returned output as JSON (test results, row counts, GraphQL response payload). Truncate oversized payloads with `... (truncated)` marker. |
| **Expected** | on failure only | Expected shape or value when status is `fail` or `error` |
| **Error/diff** | on failure only | Error message, status code, or expected-vs-actual diff |

#### GraphQL Call Recording (mandatory for all transaction and resilience scenarios)

Every call to `AICoordinationEngine.ai_coordination_graphql(query=..., variables=..., endpoint_id=..., part_id=...)` must be recorded with the **full GraphQL document** and the **full response payload**.

**Arguments block for a GraphQL call must include:**

```json
{
  "method": "AICoordinationEngine.ai_coordination_graphql",
  "engine_call": {
    "endpoint_id": "gpt",
    "part_id": "nestaging",
    "DB_BACKEND": "postgresql"
  },
  "graphql_document": "mutation InsertUpdateCoordination($name:String,$desc:String,$agents:[JSONCamelCase],$by:String!){insertUpdateCoordination(coordinationName:$name,coordinationDescription:$desc,agents:$agents,updatedBy:$by){coordination{coordinationUuid coordinationName agents{agentUuid agentName agentType}}}}",
  "graphql_operation": "mutation insertUpdateCoordination",
  "variables": {
    "name": "Test Coordination",
    "desc": "Test description",
    "agents": [{"agentUuid": "a1", "agentName": "Agent 1", "agentType": "task", "agentDescription": "Task agent"}],
    "by": "cert"
  }
}
```

**Output block for a GraphQL call must include the full response:**

```json
{
  "data": {
    "insertUpdateCoordination": {
      "coordination": {
        "coordinationUuid": "abc123...",
        "coordinationName": "Test Coordination",
        "agents": [{"agentUuid": "a1", "agentName": "Agent 1", "agentType": "task"}]
      }
    }
  },
  "errors": null
}
```

**Rules for GraphQL call recording:**

1. **Record the full `graphql_document`** — the complete GraphQL mutation or query string, including all field selections.
2. **Record the full `variables`** — the exact variables dict passed. Redact secrets but keep all business values.
3. **Record the full response `data`** — the complete `data` object from the GraphQL response. For list queries, truncate only if > 20 items.
4. **Record `errors`** — if present, include the full error array.
5. **Record `engine_call` context** — `endpoint_id`, `part_id`, and `DB_BACKEND` for backend auditability.
6. **One block per GraphQL operation** — if a scenario executes 5 mutations and 3 queries, there must be 8 separate blocks.
7. **Group by scenario** — tagged with Scenario ID, in execution order within the scenario.

### 12.4 Minimum Certification Output

The report must include these minimum sections whenever certifying readiness:

- Scope tested
- Dependencies validated, provisioned, configured, initialized, and blocked
- Execution order used
- Tests run with pass, fail, skipped, and blocked counts
- Per-call Function Results: input arguments and output for every call
- Workflow and data integrity findings
- Defects by severity and root cause
- Open risks and mitigation plan
- Final certification status

## 13. Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| Test owner | `<pending>` | `<pending>` | `<pending>` |
| Release manager | `<pending>` | `<pending>` | `<pending>` |
| DB owner (PostgreSQL) | `<pending>` | `<pending>` | `<pending>` |
| AWS account owner (DynamoDB) | `<pending>` | `<pending>` | `<pending>` |
| AACE team (loopback dependency) | `<pending>` | `<pending>` | `<pending>` |

---

## Pending Confirmation Items

Before any test execution begins, the following placeholders need
explicit decisions:

1. **Target environment** (Section 1): single environment for both backends, or separate `dev` (DynamoDB) + `qa` (PostgreSQL)?
2. **SOP owner / contact** (Section 1): who owns this document?
3. **Credential source confirmation** (Section 3): confirm `tests/.env` + `DATABASE_URL`/`PG_*` as the approved secret sources; confirm AWS credential scope.
4. **Dependency owners** (Section 4): who owns DynamoDB, PostgreSQL, and each library dependency for readiness sign-off?
5. **Provisioning policy** (Section 3): confirm auto-provisioning of the disposable PostgreSQL schema is allowed in the target environment.
6. **CI cadence** (Section 11): confirm the PR-block / nightly-report / pre-release-block split.
7. **Distribution list** (Section 12): who receives the certification report?
8. **Sign-off roles** (Section 13): names for test owner, release manager, DB owner, AWS account owner, AACE team.
9. **AACE loopback scope** (INT-009, INT-011): confirm whether live `ai_agent_core_engine` loopback calls are in scope or remain mocked; if live, identify the AACE team owner.
10. **Async Lambda dispatch scope** (INT-009, INT-011, INT-012): confirm whether async Lambda invocations are validated (requires Lambda function deployed) or only the handler logic is tested in-process.

Once these are confirmed, the SOP status moves from `draft` to `approved` and
the certification may proceed.