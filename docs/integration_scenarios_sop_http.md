# Continuous Integration Scenarios SOP — AI Coordination Engine (HTTP Gateway Transport)

## 1. Document Control

| Field | Value |
|---|---|
| SOP title | AI Coordination Engine Live Integration SOP — HTTP Gateway Transport (GraphQL over REST) |
| Version | 0.1.0 |
| Owner / contact | `bibow` |
| Last updated | 2026-06-30 |
| Business domain | `ai_coordination` (multi-agent orchestration / session coordination) |
| Target environment | local dev gateway instance using `ai_coordination_engine/tests/.env` |
| Approval status | `<pending confirmation>` |
| Companion SOP | `INTEGRATION_SCENARIOS_SOP.md` (direct in-process GraphQL engine invocation) |
| Test script | `ai_coordination_engine/tests/run_http_integration.py` `<pending creation>` |

## 2. Purpose and Scope

This SOP defines the ordered live integration scenarios used to validate
`ai_coordination_engine` through the **HTTP gateway transport layer** — the
same GraphQL-over-REST path (`POST /{endpoint_id}/ai_coordination_graphql`)
that a real client (AI agent, frontend, or external service) uses to invoke
queries and mutations via the `silvaengine_gateway`. Unlike the companion SOP
(which calls `AICoordinationEngine.ai_coordination_graphql()` directly
in-process with `DB_BACKEND` set per invocation), this SOP exercises only the
`HTTP client → gateway /ai_coordination_graphql → dispatch_graphql →
AICoordinationEngine.ai_coordination_graphql` path. The gateway handles Config
initialization, JWT Bearer auth, tenant routing via `Part-Id` header, and
request/response serialization internally.

- **In scope:**
  - All 6 persisted entities (coordination, task, task_schedule, session,
    session_agent, session_run) through the gateway GraphQL endpoint.
  - All GraphQL queries and mutations exposed by the `ai_coordination_engine`
    schema (Section 7).
  - Gateway JWT Bearer auth flow (`POST /auth/token` → JWT → `Authorization`
    header on all GraphQL requests).
  - Tenant routing via `Part-Id` request header (gateway builds
    `partition_key = {endpoint_id}#{part_id}`).
  - `DB_BACKEND` configured at gateway startup via `Config.initialize`; both
    `dynamodb` and `postgresql` backends exercisable by restarting the gateway
    with different `.env` settings.
  - RLS (Row-Level Security) enforcement on PostgreSQL backend (gateway sets
    `app.tenant_id` from `partition_key` context).
  - Operation Hub workflow: `askOperationHub` query via HTTP.
  - Procedure Hub workflow: `executeProcedureTaskSession` mutation via HTTP.
  - User-in-the-loop workflow: `executeForUserInput` mutation via HTTP.
  - JSONB `agent_action` filtering on `sessionAgentList` via HTTP.
  - Gateway error handling: HTTP status codes, GraphQL error envelopes,
    connection failures, auth failures.
- **Out of scope:**
  - Direct in-process method calls on `AICoordinationEngine` (covered by
    companion SOP `INTEGRATION_SCENARIOS_SOP.md`).
  - AWS Lambda async dispatch mechanism (`async_insert_update_session`,
    `async_execute_procedure_task_session`, `async_update_session_agent`,
    `async_orchestrate_task_query`) — handler logic is in scope via the
    synchronous GraphQL operations that trigger them; the Lambda invocation
    mechanism is not.
  - Live external LLM calls (AI *decision-making* is not; prompt *storage* and
    *retrieval* via coordination `agents` list is in scope).
  - The `ai_agent_core_engine` companion service (separate engine; ACE invokes
    it via GraphQL loopback for `ask_model` / `get_async_task` — mocked for
    this SOP).
  - Production testing, destructive cleanup of generated live test records,
    cloud provisioning, third-party production side effects, UI testing, load
    testing.
  - DynamoDB-to-PostgreSQL data migration (no production data exists; both
    backends start empty).
  - Performance benchmarking beyond smoke-level timing.
- **System(s) under test:** `silvaengine_gateway` REST GraphQL route
  (`/{endpoint_id}/ai_coordination_graphql` with `Part-Id` request header),
  `ai_coordination_engine.main:dispatch_graphql`, `AICoordinationEngine`
  GraphQL engine and its persistence layer (`models/dynamodb`,
  `models/postgresql`, `models/repositories`).
- **Transport validation:** this SOP validates that the gateway correctly
  dispatches GraphQL POST requests to `dispatch_graphql`, which instantiates
  `AICoordinationEngine`, executes the GraphQL schema, and returns the
  response as HTTP JSON `{data, errors}`. The test script never accesses the
  engine or database directly.

## 2.1 Controlling End-to-End Testing Procedure

The following procedure is authoritative for this HTTP gateway transport SOP:

1. Execute the end-to-end live integration testing with the script
   `ai_coordination_engine/tests/run_http_integration.py`, which uses an async
   HTTP client to drive all GraphQL queries and mutations through the gateway
   REST endpoint `POST /{endpoint_id}/ai_coordination_graphql`.
2. Use variables from `ai_coordination_engine/tests/.env` to target the local
   gateway instance. Do not hard-code credentials, endpoint IDs, partition
   IDs, or gateway URLs in generated reports.
3. Read and use the prepared test data as the reference dataset and dependency
   source for function inputs, expected relationships, and scenario
   ordering.
4. Before any scenario group is executed, verify that the HTTP client can
   successfully complete the gateway auth flow (`POST /auth/token` → JWT) and
   that a `ping` query returns a valid response. This confirms the transport
   layer is operational.
5. Optionally run with `--list-operations` to verify that the GraphQL schema
   introspection returns the expected queries and mutations before proceeding
   to scenario execution.
6. Build the entity dependency map before execution, then derive the test
   sequence priority from that dependency map rather than file-discovery
   order.
7. Perform end-to-end live integration testing in dependency order via async
   GraphQL POST invocations.
8. Address any implementation, runner, data-contract, HTTP transport, or
   scenario-ordering issues found during live execution.
9. Retest affected scenarios, then rerun the full dependency-ordered suite
   until all required calls pass with zero unexpected error responses.
10. Export the final per-function arguments and outputs into the project
    `docs/` directory.

## 3. Environment and Access

> **Env var split.** There are two distinct `.env` scopes: **test-script env
> vars** (read by `run_http_integration.py` for HTTP connection) and
> **gateway-startup env vars** (read by the gateway process at boot for backend
> configuration). The test script does NOT read or set `DB_BACKEND`,
> `DATABASE_URL`, `PG_*`, `functs_on_local`, or backend credentials — those
> are gateway-startup settings. To switch backends, restart the gateway with
> different startup env vars.

### 3.1 Test-Script Env Vars (read by `run_http_integration.py`)

| Item | Value / source |
|---|---|
| Environment target | local dev gateway instance |
| GraphQL REST endpoint | `GRAPHQL_URL` from `.env`, default `{GATEWAY_BASE_URL}/{endpoint_id}/ai_coordination_graphql` |
| Credential source | `.env` variable names only; do not write secret values into reports |
| Auth flow | HTTP client obtains JWT Bearer token from `{GATEWAY_BASE_URL}/auth/token` using `TOKEN_USERNAME` / `TOKEN_PASSWORD` (or uses `GATEWAY_TOKEN` if set); token is sent as `Authorization: Bearer ***` header on all GraphQL POST requests |
| Required env vars | `base_dir`, `GATEWAY_BASE_URL`, `TOKEN_USERNAME`, `TOKEN_PASSWORD`, `GATEWAY_TOKEN` (optional), `endpoint_id`, `part_id`, `GRAPHQL_URL` (optional, derived by default) |
| HTTP client config | `base_url` = `GATEWAY_BASE_URL`, `graphql_endpoint` = `{base_url}/{endpoint_id}/ai_coordination_graphql`, `bearer_token` = gateway JWT, `headers` = `{"Part-Id": PART_ID}` |

### 3.2 Gateway-Startup Env Vars (read by the gateway process at boot)

| Item | Value / source |
|---|---|
| Data stores | DynamoDB (`ace-*` tables, 6 tables); PostgreSQL (6 tables, SQLAlchemy + Alembic) — configured at gateway startup, not per-request |
| Backend selection | `DB_BACKEND=dynamodb` (default) or `DB_BACKEND=postgresql`; set at gateway startup; restart gateway to switch |
| DynamoDB credentials | `region_name`, `aws_access_key_id`, `aws_secret_access_key` (DynamoDB mode) |
| PostgreSQL credentials | `DATABASE_URL` or `PG_HOST` / `PG_PORT` / `PG_USER` / `PG_PASSWORD` / `PG_DB` (PostgreSQL mode) |
| Execute mode | `execute_mode=local_for_all` + `functs_on_local` mapping (for in-process async dispatch without Lambda) |
| Messaging / events | AWS Lambda async dispatch (out of scope); AWS SES email (out of scope); WebSocket connections (out of scope) |
| Access constraints | local process access to gateway; `ai_coordination_engine` module must be loaded into gateway via `routes.yaml` |
| Provisioning policy | auto-provision PG schema (`alembic upgrade head` or `Base.metadata.create_all`) at gateway startup; manual approval required for any cloud credential scope change or production access |

### 3.3 Gateway Route Configuration

| Item | Value |
|---|---|
| Route path | `/{endpoint_id}/ai_coordination_graphql` |
| Handler type | `graphql` |
| Dispatch function | `ai_coordination_engine.main:dispatch_graphql` |
| Auth | `true` (JWT Bearer required) |
| Config class | `ai_coordination_engine.handlers.config:Config` |
| Config init style | `kwargs` — gateway calls `Config.initialize(logger, **setting)` (NOT `dict` style like `rfq_engine`); mismatch causes gateway startup failure |
| `Part-Id` header | not part of the URL; sent in `Part-Id` request header; gateway builds `partition_key = {endpoint_id}#{Part-Id}` |
| Session lifecycle | `dispatch_graphql` wraps each request with `try/except: db_session.rollback()` + `finally: db_session.remove()` — automatic scoped-session cleanup on PostgreSQL; no stale session state across HTTP requests |

> **Names and sources only — never paste secrets, tokens, or connection strings.**

## 4. Dependency Readiness Requirements

| Dependency | Type | Health check | Required readiness | Owner |
|---|---|---|---|---|
| Python environment | infrastructure | import HTTP client and `run_http_integration` module | operational | `bibow` |
| `aiohttp` / `httpx` | library | importable (required for async HTTP) | installed | `bibow` |
| `silvaengine_gateway` local instance | internal | `POST /auth/token` returns JWT; `POST /{endpoint_id}/ai_coordination_graphql` with `ping` query returns `"Hello at ..."` | operational | `bibow` |
| `ai_coordination_engine` module loaded | internal | GraphQL `ping` query returns valid response via gateway | loaded and operational | `bibow` |
| DynamoDB (`ace-*` tables) | infrastructure | `initialize_tables(logger)` succeeds at gateway startup; `CoordinationModel.exists()` | operational (if `DB_BACKEND=dynamodb`) | `bibow` |
| PostgreSQL (disposable schema) | infrastructure | `DATABASE_URL` reachable; `SELECT 1`; `alembic upgrade head` or `Base.metadata.create_all` at gateway startup | initialized (if `DB_BACKEND=postgresql`) | `bibow` |
| Repository dispatch boundary | internal (module) | `get_repo("coordination")` resolves under active backend; `get_loaders({})` returns correct loader type | operational | ACE team |
| Alembic migration set `0001`-`0007` | internal (module) | `alembic upgrade head` applies cleanly to empty schema (PostgreSQL only) | initialized | ACE team |
| `ai_agent_core_engine` (loopback) | external (service) | GraphQL loopback for `invoke_ask_model` / `get_async_task` reachable or mocked | configured | AACE team |
| AWS credentials (Lambda, S3, SES) | infrastructure | `boto3.client("lambda").list_functions()` (or scoped equivalent) | configured | `bibow` |
| `silvaengine_dynamodb_base` | internal (library) | import + `BaseModel` meta initialized | operational | SilvaEngine team |
| `silvaengine_utility` | internal (library) | import + `HybridCacheEngine` instantiable | operational | SilvaEngine team |
| `silvaengine_constants` | internal (library) | import + `InvocationType` accessible | operational | SilvaEngine team |
| `graphene` / `promise` | internal (library) | import + schema builds | operational | open-source |
| `tenacity` | internal (library) | import + retry decorator works | operational | open-source |
| `SQLAlchemy>=1.4` / `psycopg2-binary` / `alembic` | internal (library, PG-only) | import; installed via `ai-coordination-engine[postgresql]` extras | configured | open-source |

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
- **Data source:** generated by the test script driving data through the gateway GraphQL endpoint via HTTP POST — the same mutations production traffic uses. Scripts are backend-agnostic: the active backend is determined by gateway startup `DB_BACKEND` config.

### Seed Script Execution Sequence

| Step | Script | Reads | Writes | Entities created |
|---|---|---|---|---|
| 1 | `prepare_coordinations.py` | — | `coordinations.json` | Coordination (3, with agents lists) |
| 2 | `prepare_tasks.py` | `coordinations.json` | `tasks.json` | Task (3, with subtask_queries + agent_actions) |
| 3 | `prepare_task_schedules.py` | `tasks.json` | `task_schedules.json` | TaskSchedule (2) |
| 4 | `prepare_sessions.py` | `coordinations.json` + `tasks.json` | `sessions.json` | Session (5) |
| 5 | `prepare_session_agents.py` | `sessions.json` + `tasks.json` | `session_agents.json` | SessionAgent (6+, with agent_action predecessor graph) |
| 6 | `prepare_session_runs.py` | `sessions.json` + `session_agents.json` | `session_runs.json` | SessionRun (4+, with thread_uuid + async_task_uuid) |

**Backend selection** (env vars at gateway startup):
- `DB_BACKEND=dynamodb` (default) — uses `region_name` / `aws_access_key_id` / `aws_secret_access_key`
- `DB_BACKEND=postgresql` — uses `DATABASE_URL` or `PG_HOST` / `PG_PORT` / `PG_USER` / `PG_PASSWORD` / `PG_DB`

**Prerequisites:**
- Gateway `.env` configured with `endpoint_id`, `part_id`, `execute_mode=local_for_all`, and backend-specific credentials
- For PostgreSQL: `alembic -c migration/alembic.ini upgrade head` applied before gateway startup (schema must exist before data loading)
- Gateway running and reachable at `GATEWAY_BASE_URL`
- `ai_coordination_engine` loaded into gateway via `routes.yaml`

## 6. Execution Order

```text
[auth handshake + ping (INT-HTTP-000)] → [auth failure (INT-HTTP-001)] → [tenant isolation (INT-HTTP-002)] → coordinations → tasks → task_schedules → sessions → session_agents → session_runs → operation_hub → JSONB filter → procedure_hub → user_in_the_loop → backend parity → alembic → RLS
```

**Reason for ordering:** this engine manages multi-agent coordination with a strict parent → child entity hierarchy. Coordination (root) must exist before task/session; task must exist before task_schedule; session must exist before session_agent/session_run; session_agent must exist before user-in-the-loop workflow. The gateway auth handshake and `ping` query are implicit first steps — the HTTP client obtains a JWT and verifies connectivity before any scenario executes.

**Sequence construction rule:** the execution order must be rebuilt or revalidated before each certification run from the actual entity dependencies in the schema and codebase. Static file order is not sufficient.

### 6.1 Model Dependency Matrix

| # | Child entity | Parent entity | FK field on child | Notes |
|---|---|---|---|---|
| 1 | Coordination | — (root) | — | Tenant-partitioned (hash=partition_key); contains `agents` list |
| 2 | Task | Coordination | `coordination_uuid` | Hash=coordination_uuid; validates `subtask_queries` + `agent_actions` against coordination's `agents` |
| 3 | TaskSchedule | Task | `task_uuid` | Hash=task_uuid; has `partition_key` + `coordination_uuid` |
| 4 | Session | Coordination | `coordination_uuid` | Hash=coordination_uuid; optional `task_uuid` |
| 5 | SessionAgent | Session | `session_uuid` | `agent_action` JSONB with predecessor graph |
| 6 | SessionRun | Session | `session_uuid` | `thread_uuid` + `agent_uuid` + `async_task_uuid`; optional `session_agent_uuid` |

### 6.2 Execution Sequence

The certification run proceeds in two phases: **asset loading** and
**transaction testing**. All test assets must be loaded and validated before
any transaction scenario executes.

#### Phase A: Asset Loading (must complete before Phase B)

```text
1. Schema provisioning
   -> alembic upgrade head (PostgreSQL) or initialize_tables (DynamoDB)
   -> gateway started with correct DB_BACKEND

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
4. Transport smoke (INT-HTTP-000)
   -> auth handshake, ping query, schema introspection

5. Entity CRUD scenarios (INT-HTTP-003 through INT-HTTP-008)
   -> coordination, task, task_schedule, session, session_agent, session_run

6. Workflow scenarios (INT-HTTP-009 through INT-HTTP-012)
   -> operation hub, JSONB filter, procedure hub, user-in-the-loop

7. Backend parity (INT-HTTP-013)
   -> same GraphQL workflow under PostgreSQL (restart gateway with DB_BACKEND=postgresql)

8. Infrastructure scenarios (INT-HTTP-014, INT-HTTP-015)
   -> Alembic migrations, RLS enforcement

9. Resilience scenarios (Section 8)
   -> missing data, invalid data, auth failures, gateway failures, cache failures

10. Reconciliation (Section 9)
    -> referential integrity, count consistency, backend parity
```

### 6.3 Transaction Scenario Dependency Graph

```text
INT-HTTP-000 (transport smoke) --> all scenarios
INT-HTTP-001 (auth failure) -----> INT-HTTP-003+ (requires valid auth first)
INT-HTTP-002 (tenant isolation) --> INT-HTTP-015 (RLS enforcement)
     |
     v
INT-HTTP-003 (coordination CRUD) ---> INT-HTTP-009 (operation hub)
     |                            ---> INT-HTTP-011 (procedure hub)
     v
INT-HTTP-004 (task CRUD) -----------> INT-HTTP-011 (procedure hub)
     |
     v
INT-HTTP-005 (task_schedule CRUD)
     |
INT-HTTP-006 (session CRUD) --------> INT-HTTP-009 (operation hub)
     |                             ---> INT-HTTP-011 (procedure hub)
     v
INT-HTTP-007 (session_agent CRUD) --> INT-HTTP-011 (procedure hub)
     |                              ---> INT-HTTP-012 (user-in-the-loop)
     v
INT-HTTP-008 (session_run CRUD) ---> INT-HTTP-009 (operation hub)
     |
INT-HTTP-009 (operation hub) -----> INT-HTTP-013 (backend parity)
INT-HTTP-010 (JSONB filter)
INT-HTTP-011 (procedure hub) -----> INT-HTTP-013 (backend parity)
INT-HTTP-012 (user-in_the_loop) --> INT-HTTP-013 (backend parity)
INT-HTTP-014 (alembic migrations)
INT-HTTP-015 (RLS enforcement)
```

## 7. Integration Scenarios

### INT-HTTP-000 — Gateway transport initialization and smoke test

| Field | Value |
|---|---|
| **ID** | INT-HTTP-000 |
| **Name** | Gateway auth handshake, ping query, and schema introspection |
| **Priority** | P0 |
| **Type** | transport / smoke |
| **CI trigger** | manual / pre-release |
| **Preconditions** | Gateway is running; `ai_coordination_engine` is loaded via `routes.yaml` |
| **Dependencies** | gateway, `dispatch_graphql`, `Config.initialize` |
| **Test data** | none (transport handshake only) |
| **Steps** | 1. `POST /auth/token` with `TOKEN_USERNAME` / `TOKEN_PASSWORD` → verify JWT returned. 2. `POST /{endpoint_id}/ai_coordination_graphql` with `Authorization: Bearer ***`, `Part-Id: ***`, body `{"query": "{ ping }"}` → verify response `{"data": {"ping": "Hello at ..."}}`. 3. Optionally introspect schema: `{"query": "{ __schema { queryType { fields { name } } mutationType { fields { name } } } }"}` → verify expected query/mutation names. |
| **Expected behavior** | JWT obtained; `ping` returns greeting string; schema introspection returns all expected queries (coordination, coordinationList, session, sessionList, task, taskList, sessionAgent, sessionAgentList, sessionRun, sessionRunList, taskSchedule, taskScheduleList, askOperationHub) and mutations (insertUpdateCoordination, deleteCoordination, insertUpdateSession, deleteSession, insertUpdateSessionRun, deleteSessionRun, insertUpdateTask, deleteTask, insertUpdateSessionAgent, deleteSessionAgent, insertUpdateTaskSchedule, deleteTaskSchedule, executeProcedureTaskSession, executeForUserInput) |
| **Validation points** | jwt_obtained, ping_returns_greeting, schema_introspection_complete |
| **Cross-system checks** | gateway correctly resolves `ai_coordination_engine.main:dispatch_graphql` and `Config.initialize` succeeds with `config_init_style: kwargs` |

### INT-HTTP-001 — Auth failure (missing/invalid Bearer token)

| Field | Value |
|---|---|
| **ID** | INT-HTTP-001 |
| **Name** | Missing or invalid JWT Bearer token returns 401 |
| **Priority** | P0 |
| **Type** | transport / security |
| **CI trigger** | manual / pre-release |
| **Preconditions** | Gateway is running; `ai_coordination_engine` is loaded |
| **Dependencies** | gateway auth middleware |
| **Test data** | none |
| **Steps** | 1. `POST /{endpoint_id}/ai_coordination_graphql` with no `Authorization` header → verify HTTP 401. 2. `POST /{endpoint_id}/ai_coordination_graphql` with `Authorization: Bearer invalid-token` → verify HTTP 401. 3. `POST /{endpoint_id}/ai_coordination_graphql` with valid JWT but no `Part-Id` header → verify gateway returns error (missing partition context) or HTTP 400/500. |
| **Expected behavior** | Gateway rejects unauthenticated requests with 401; invalid tokens rejected; missing `Part-Id` header causes explicit error (gateway cannot build `partition_key`) |
| **Validation points** | missing_token_rejected, invalid_token_rejected, missing_part_id_error |
| **Cross-system checks** | Gateway auth middleware active on `ai_coordination_graphql` route; no GraphQL execution occurs without valid auth |

### INT-HTTP-002 — Tenant isolation via Part-Id header

| Field | Value |
|---|---|
| **ID** | INT-HTTP-002 |
| **Name** | Same query with different `Part-Id` headers returns different tenant's data |
| **Priority** | P1 |
| **Type** | transport / tenant isolation |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-000 passed; data exists in at least 2 tenants |
| **Dependencies** | gateway `Part-Id` header routing; `partition_key` context |
| **Test data** | 1 coordination created under tenant A (`Part-Id: part_a`); 1 coordination under tenant B (`Part-Id: part_b`) |
| **Steps** | 1. `POST` mutation `insertUpdateCoordination` with `Part-Id: part_a` → create coordination A. 2. `POST` mutation `insertUpdateCoordination` with `Part-Id: part_b` → create coordination B. 3. `POST` query `coordinationList` with `Part-Id: part_a` → verify only coordination A is returned. 4. `POST` query `coordinationList` with `Part-Id: part_b` → verify only coordination B is returned. 5. `POST` query `coordination(coordinationUuid: <A>)` with `Part-Id: part_b` → verify returns `null` (wrong tenant). |
| **Expected behavior** | Gateway builds `partition_key` from `Part-Id` header; each tenant sees only its own data; cross-tenant queries return `null` or empty lists |
| **Validation points** | tenant_a_isolated, tenant_b_isolated, cross_tenant_query_null |
| **Cross-system checks** | `partition_key` in response context matches `{endpoint_id}#{Part-Id}`; no tenant data leakage |

### INT-HTTP-003 — Coordination CRUD via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-003 |
| **Name** | Create, read, update, delete a coordination through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (HTTP) |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-HTTP-000 passed; gateway running with active backend |
| **Dependencies** | `coordination` repository; gateway GraphQL dispatch |
| **Test data** | 1 coordination with 3 agents |
| **Steps** | 1. `POST /{endpoint_id}/ai_coordination_graphql` mutation `insertUpdateCoordination` with `coordinationUuid`, `coordinationName`, `coordinationDescription`, `agents` (list of 3 agent maps with `agentUuid`, `agentName`, `agentType`, `agentDescription`), `updatedBy`. 2. `POST` query `coordination(coordinationUuid: ...)` verify all fields. 3. `POST` mutation `insertUpdateCoordination` update `coordinationName`. 4. `POST` query `coordination` verify updated name. 5. `POST` query `coordinationList(coordinationName: ...)` verify `total >= 1`. 6. `POST` mutation `deleteCoordination` verify `ok == true`. 7. `POST` query `coordination` verify `null`. |
| **Expected behavior** | Insert returns coordination type; get returns all fields; update changes name; list returns correct total; delete returns true; post-delete get returns null |
| **Validation points** | insert_returns_type, get_returns_fields, update_changes_name, list_returns_total, delete_returns_true, post_delete_null |
| **Cross-system checks** | `agents` list length == 3; `updated_at` advances on update; HTTP response is valid JSON `{data, errors}` with `errors: null` |

### INT-HTTP-004 — Task CRUD with agent validation via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-004 |
| **Name** | Create, read, update, delete a task with agent UUID validation through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (HTTP) |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-003 coordination exists |
| **Dependencies** | `task` repository, `coordination` repository (for validation); gateway GraphQL dispatch |
| **Test data** | 1 task with subtask_queries and agent_actions |
| **Steps** | 1. `POST` mutation `insertUpdateTask` with `coordinationUuid`, `taskUuid`, `taskName`, `taskDescription`, `initialTaskQuery`, `subtaskQueries` (list of maps with `agent_uuid` + `subtask_query`), `agentActions` (map of agent_uuid → action with predecessors), `updatedBy`. 2. `POST` query `task(coordinationUuid: ..., taskUuid: ...)` verify all fields. 3. `POST` mutation `insertUpdateTask` with invalid `agent_uuid` in `subtaskQueries` → verify filtered out. 4. `POST` query `taskList(coordinationUuid: ...)` verify `total >= 1`. 5. `POST` mutation `deleteTask` verify `ok == true`. |
| **Expected behavior** | Insert returns task type; agent UUIDs validated against coordination's agents; invalid UUIDs filtered from subtask_queries and agent_actions; list returns correct total |
| **Validation points** | insert_returns_type, agent_validation_filters, list_returns_total, delete_returns_true |
| **Cross-system checks** | `subtask_queries` only contains agent_uuids from coordination's agents list |

### INT-HTTP-005 — TaskSchedule CRUD via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-005 |
| **Name** | Create, read, update, delete a task schedule through gateway GraphQL |
| **Priority** | P2 |
| **Type** | end-to-end (HTTP) |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-004 task exists |
| **Dependencies** | `task_schedule` repository; gateway GraphQL dispatch |
| **Test data** | 2 schedules (active + initial) |
| **Steps** | 1. `POST` mutation `insertUpdateTaskSchedule` with `taskUuid`, `coordinationUuid`, `schedule` (cron expression), `status="initial"`, `updatedBy`. 2. `POST` query `taskSchedule(taskUuid: ..., scheduleUuid: ...)` verify fields. 3. `POST` mutation `insertUpdateTaskSchedule` update `status="active"`. 4. `POST` query `taskScheduleList(taskUuid: ...)` verify `total >= 1`. 5. `POST` mutation `deleteTaskSchedule` verify `ok == true`. |
| **Expected behavior** | Insert returns schedule type; status update works; list filters by task_uuid; delete returns true |
| **Validation points** | insert_returns_type, status_update, list_filters, delete_returns_true |
| **Cross-system checks** | `schedule_uuid` present; `status` transitions initial → active |

### INT-HTTP-006 — Session CRUD via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-006 |
| **Name** | Create, read, update, delete a session through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (HTTP) |
| **CI trigger** | manual / pre-release |
| **Preconditions** | INT-HTTP-003 coordination exists |
| **Dependencies** | `session` repository; gateway GraphQL dispatch |
| **Test data** | 1 session with status, task_query, user_id |
| **Steps** | 1. `POST` mutation `insertUpdateSession` with `coordinationUuid`, `sessionUuid`, `userId`, `taskQuery`, `status="initial"`, `updatedBy`. 2. `POST` query `session(coordinationUuid: ..., sessionUuid: ...)` verify all fields including `partitionKey`. 3. `POST` mutation `insertUpdateSession` update `status="active"`, `iterationCount=1`. 4. `POST` query `sessionList(coordinationUuid: ...)` verify `total >= 1`. 5. `POST` mutation `insertUpdateSession` update `logs` (JSON string). 6. `POST` mutation `deleteSession` verify `ok == true`. |
| **Expected behavior** | Insert returns session type; `partition_key` populated from gateway context; status update works; list filters by coordination_uuid; logs update works; delete returns true |
| **Validation points** | insert_returns_type, partition_key_populated, status_update, list_filters, logs_update, delete_returns_true |
| **Cross-system checks** | `partition_key == endpoint_id#part_id` from gateway `Part-Id` header context |

### INT-HTTP-007 — SessionAgent CRUD with JSONB agent_action via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-007 |
| **Name** | Create, read, update, delete a session agent with agent_action JSONB through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (HTTP) |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-006 session exists |
| **Dependencies** | `session_agent` repository; gateway GraphQL dispatch |
| **Test data** | 2 session agents with agent_action (primary_path, predecessors, user_in_the_loop) |
| **Steps** | 1. `POST` mutation `insertUpdateSessionAgent` with `sessionUuid`, `sessionAgentUuid`, `coordinationUuid`, `agentUuid`, `agentAction` (map: `primary_path=true`, `user_in_the_loop=null`, `predecessors=[]`, `action_function={}`), `updatedBy`. 2. `POST` query `sessionAgent(sessionUuid: ..., sessionAgentUuid: ...)` verify `agentAction` map. 3. `POST` mutation `insertUpdateSessionAgent` update `state="executing"`, `inDegree=1`. 4. `POST` query `sessionAgentList(sessionUuid: ...)` verify `total >= 1`. 5. `POST` mutation `deleteSessionAgent` verify `ok == true`. |
| **Expected behavior** | Insert returns session agent type; `agent_action` JSONB populated with default merge; state/in_degree update works; list filters by session_uuid; delete returns true |
| **Validation points** | insert_returns_type, agent_action_populated, state_update, in_degree_update, list_filters, delete_returns_true |
| **Cross-system checks** | `agent_action.primary_path == true`; `partition_key` populated in PG (not in GraphQL type) |

### INT-HTTP-008 — SessionRun CRUD via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-008 |
| **Name** | Create, read, update, delete a session run through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (HTTP) |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-006 session exists |
| **Dependencies** | `session_run` repository; gateway GraphQL dispatch |
| **Test data** | 1 session run with thread_uuid, agent_uuid, async_task_uuid |
| **Steps** | 1. `POST` mutation `insertUpdateSessionRun` with `sessionUuid`, `runUuid`, `threadUuid`, `agentUuid`, `coordinationUuid`, `asyncTaskUuid`, `updatedBy`. 2. `POST` query `sessionRun(sessionUuid: ..., runUuid: ...)` verify all fields. 3. `POST` query `sessionRunList(sessionUuid: ...)` verify `total >= 1`. 4. `POST` mutation `deleteSessionRun` verify `ok == true`. |
| **Expected behavior** | Insert returns session run type; all FK fields populated; list filters by session_uuid; delete returns true |
| **Validation points** | insert_returns_type, fk_fields_populated, list_filters, delete_returns_true |
| **Cross-system checks** | `thread_uuid` and `async_task_uuid` present; `partition_key` populated from gateway context |

### INT-HTTP-009 — Operation Hub workflow (askOperationHub) via HTTP

> **Mock limitation under HTTP transport.** Unlike the companion in-process
> SOP, which uses `unittest.mock.patch` to mock AACE loopback
> (`invoke_ask_model`) in-process, the HTTP test script **cannot patch
> gateway-internal code** — the gateway runs as a separate process. Options:
> - **Option A (preferred):** Configure AACE loopback at the gateway level via
>   `functs_on_local` in the gateway startup `.env`, making real loopback calls
>   to `ai_agent_core_engine`. This requires AACE to be running and reachable.
> - **Option B:** Skip workflow scenarios (INT-HTTP-009, INT-HTTP-011,
>   INT-HTTP-012) in the HTTP SOP and reference the companion in-process SOP for
>   those. Document the skip in the certification report with reason
>   `"AACE loopback mock not possible under HTTP transport"`.
> - **Option C:** Mock at gateway startup via a test configuration that patches
>   AACE before the gateway starts — fragile and not recommended.
>
> This SOP assumes **Option A** (real AACE loopback via `functs_on_local`).
> If AACE is not available, scenarios INT-HTTP-009/011/012 are marked as
> `skipped` with the reason documented.

| Field | Value |
|---|---|
| **ID** | INT-HTTP-009 |
| **Name** | `askOperationHub` creates session, invokes AI model, records session run through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (workflow / HTTP) |
| **CI trigger** | pre-release |
| **Preconditions** | INT-HTTP-003 coordination exists with agents; `ai_agent_core_engine` loopback reachable (or mocked) |
| **Dependencies** | `coordination`, `session`, `session_run` repositories; `handlers.operation_hub`; `ai_coordination_utility.invoke_ask_model`; gateway GraphQL dispatch |
| **Test data** | 1 coordination with triage + task agents |
| **Steps** | 1. `POST` query `askOperationHub(coordinationUuid: ..., userId: ..., userQuery: "test query", stream: false)`. 2. Verify response contains `sessionUuid`, `runUuid`, `threadUuid`, `agentUuid`, `asyncTaskUuid`. 3. `POST` query `session(coordinationUuid: ..., sessionUuid: ...)` verify `status` advanced from `initial`. 4. `POST` query `sessionRun(sessionUuid: ..., runUuid: ...)` verify `threadUuid` and `agentUuid` match response. |
| **Expected behavior** | Coordination resolved; session created/updated; triage or specified agent selected; AI model invoked via loopback; session_run recorded; async update dispatched |
| **Validation points** | coordination_resolved, session_created, agent_selected, ask_model_invoked, session_run_recorded, async_dispatched |
| **Cross-system checks** | `session_run.agent_uuid` matches selected agent from coordination's agents list |

### INT-HTTP-010 — SessionAgent JSONB filter via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-010 |
| **Name** | `sessionAgentList` JSONB filtering (primary_path, user_in_the_loop, predecessors, states) through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (filter parity / HTTP) |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-007 session agents exist with varied `agent_action` |
| **Dependencies** | `session_agent` repository; gateway GraphQL dispatch |
| **Test data** | 3+ session agents with different `primary_path`, `predecessors`, `state` |
| **Steps** | 1. `POST` query `sessionAgentList(sessionUuid: ..., primaryPath: true)` → verify only agents with `agent_action.primary_path == true` returned. 2. `POST` query `sessionAgentList(sessionUuid: ..., states: ["initial", "pending"])` → verify only agents in those states. 3. `POST` query `sessionAgentList(sessionUuid: ..., predecessor: "agent-uuid-1")` → verify only agents whose `agent_action.predecessors` contains that UUID. 4. `POST` query `sessionAgentList(sessionUuid: ..., predecessors: ["uuid-1", "uuid-2"])` → verify only agents whose `agent_uuid` is in the list. 5. `POST` query `sessionAgentList(sessionUuid: ..., inDegree: 0)` → verify only root agents. |
| **Expected behavior** | JSONB filters return correct subsets; combination of filters narrows correctly; results match between DynamoDB and PostgreSQL |
| **Validation points** | primary_path_filter, states_filter, predecessor_filter, predecessors_filter, in_degree_filter |
| **Cross-system checks** | Filter result counts identical between DynamoDB and PostgreSQL for the same data |

### INT-HTTP-011 — Procedure Hub workflow (executeProcedureTaskSession) via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-011 |
| **Name** | `executeProcedureTaskSession` creates session, initializes session agents, dispatches orchestration through gateway GraphQL |
| **Priority** | P1 |
| **Type** | end-to-end (workflow / HTTP) |
| **CI trigger** | pre-release |
| **Preconditions** | INT-HTTP-004 task exists with subtask_queries and agent_actions; `ai_agent_core_engine` loopback reachable (or mocked) |
| **Dependencies** | `task`, `session`, `session_agent` repositories; `handlers.procedure_hub`; `session_agent.init_session_agents`, `init_in_degree`; gateway GraphQL dispatch |
| **Test data** | 1 task with 2 task agents and predecessor graph |
| **Steps** | 1. `POST` mutation `executeProcedureTaskSession(coordinationUuid: ..., taskUuid: ..., taskQuery: "test")`. 2. Verify response contains `sessionUuid`, `taskUuid`, `taskQuery`. 3. `POST` query `session(coordinationUuid: ..., sessionUuid: ...)` verify `status` is `dispatched` or `in_transit`. 4. `POST` query `sessionAgentList(sessionUuid: ...)` verify session agents initialized for each task agent. 5. Verify each session agent has `in_degree` set (0 for root, >0 for dependent). |
| **Expected behavior** | Task resolved; session created; session agents initialized for each task agent in the coordination; in_degree computed from predecessor graph; async orchestration dispatched |
| **Validation points** | task_resolved, session_created, agents_initialized, in_degree_computed, async_dispatched |
| **Cross-system checks** | `session_agent.in_degree` matches predecessor graph: root agents have 0, dependent agents have count of predecessors |

### INT-HTTP-012 — User-in-the-loop workflow (executeForUserInput) via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-012 |
| **Name** | `executeForUserInput` updates session agent with user input and triggers next iteration through gateway GraphQL |
| **Priority** | P2 |
| **Type** | end-to-end (workflow / HTTP) |
| **CI trigger** | nightly |
| **Preconditions** | INT-HTTP-011 procedure session exists with a session agent in `wait_for_user_input` state |
| **Dependencies** | `session_agent` repository; `handlers.procedure_hub.user_in_the_loop`; gateway GraphQL dispatch |
| **Test data** | 1 session agent in `wait_for_user_input` state |
| **Steps** | 1. `POST` mutation `executeForUserInput(sessionUuid: ..., sessionAgentUuid: ..., userInput: "user response")`. 2. Verify `ok == true`. 3. `POST` query `sessionAgent(sessionUuid: ..., sessionAgentUuid: ...)` verify `userInput` updated. 4. Verify `state` transitioned to `pending` (if action_function) or `completed` (if no action_function). 5. Verify `handle_session_agent_completion` decrements successor in_degree if completed. |
| **Expected behavior** | User input recorded; state transitions based on action_function presence; completion cascades to successors; next iteration invoked |
| **Validation points** | user_input_recorded, state_transitioned, completion_cascaded, next_iteration_invoked |
| **Cross-system checks** | If state == `completed`, successor agents' `in_degree` decremented |

### INT-HTTP-013 — Backend parity: same GraphQL workflow under PostgreSQL via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-013 |
| **Name** | INT-HTTP-003 through INT-HTTP-012 pass identically under `DB_BACKEND=postgresql` via gateway |
| **Priority** | P1 |
| **Type** | end-to-end (backend parity / HTTP) |
| **CI trigger** | pre-release |
| **Preconditions** | PostgreSQL disposable schema provisioned; `alembic upgrade head` applied; gateway restarted with `DB_BACKEND=postgresql` |
| **Dependencies** | All entity repositories (PG), `PGRequestLoaders`; gateway GraphQL dispatch |
| **Test data** | Same fixtures as DynamoDB scenarios |
| **Steps** | 1. Restart gateway with `DB_BACKEND=postgresql` and `DATABASE_URL` / `PG_*` env vars. 2. Run INT-HTTP-003 through INT-HTTP-012 via gateway GraphQL POST against PostgreSQL. 3. Compare GraphQL HTTP responses field-by-field with the DynamoDB run. |
| **Expected behavior** | Identical GraphQL HTTP responses (within numeric tolerance); same status transitions; same JSONB filter results; same HTTP status codes |
| **Validation points** | pg_crud_matches, pg_workflow_matches, pg_jsonb_filter_matches |
| **Cross-system checks** | Per-field diff between DynamoDB and PostgreSQL outputs == 0 (numeric tolerance 0.01) |

### INT-HTTP-014 — Alembic migrations apply to empty PostgreSQL

| Field | Value |
|---|---|
| **ID** | INT-HTTP-014 |
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

### INT-HTTP-015 — RLS tenant isolation enforcement via HTTP

| Field | Value |
|---|---|
| **ID** | INT-HTTP-015 |
| **Name** | Non-superuser session with tenant A's `Part-Id` cannot read tenant B's rows via gateway |
| **Priority** | P1 |
| **Type** | security |
| **CI trigger** | pre-release |
| **Preconditions** | PostgreSQL with RLS enabled; non-superuser role `aace_app` created and granted table access; gateway running with `DB_BACKEND=postgresql` |
| **Dependencies** | RLS policies (migration `0007`); `Config._set_rls_context`; gateway `Part-Id` header routing |
| **Test data** | 2 coordinations in different tenants |
| **Steps** | 1. `POST` mutation `insertUpdateCoordination` with `Part-Id: endpoint_a#part_a` → create coordination for tenant A. 2. `POST` mutation `insertUpdateCoordination` with `Part-Id: endpoint_b#part_b` → create coordination for tenant B. 3. `POST` query `coordination(coordinationUuid: ...)` with `Part-Id: endpoint_a#part_a` → verify returns data. 4. `POST` query `coordination(coordinationUuid: ...)` with `Part-Id: endpoint_a#part_a` for tenant B's coordination → verify returns `null` (RLS blocks). 5. Repeat for all 6 entity tables (create cross-tenant records, verify RLS blocks cross-tenant reads via different `Part-Id` headers). |
| **Expected behavior** | Gateway sets `app.tenant_id` from `Part-Id` header; non-superuser can read own tenant's data; cannot read other tenant's data; superuser bypasses RLS |
| **Validation points** | own_tenant_readable, cross_tenant_blocked, rls_enforced_on_all_tables |
| **Cross-system checks** | Cross-tenant `coordination` query returns `null` for all 6 entity types via gateway HTTP |

## 8. Failure and Resilience Scenarios

| Scenario | Injected fault | Expected behavior |
|---|---|---|
| missing gateway | stop gateway before live execution | HTTP client connection fails; script exits with FATAL connection error message |
| invalid credentials | bad `TOKEN_USERNAME` / `TOKEN_PASSWORD` | `/auth/token` returns 401; token request fails; no tests execute |
| expired JWT | use expired token | Gateway returns 401 on GraphQL POST; client detects and re-authenticates (or exits with auth error) |
| missing_data | `POST` query unknown `coordination_uuid` / `session_uuid` | Resolver returns `null`; HTTP 200 with `{"data": {...: null}}`; no exception surfaces to HTTP client |
| invalid_data | `POST` mutation `insertUpdateTask` with `subtask_queries` referencing non-existent agent UUID | Invalid entries filtered out by validation; valid entries persisted; HTTP 200 with filtered result |
| api_failures | Repository `insert_update` raises mid-commit | Transaction rolls back; `session.rollback()` called by `dispatch_graphql` error handler; HTTP 500 or GraphQL error envelope returned |
| database_failures | PostgreSQL connection drop mid-query | `pool_pre_ping=True` detects; retry or graceful error; no silent corruption; HTTP 500 with error message |
| authentication_failures | AWS credentials missing in DynamoDB mode | `Config.initialize` raises at gateway startup; gateway fails to start with explicit error |
| service_outages | DynamoDB table missing / PostgreSQL schema not provisioned | `initialize_tables` raises at gateway startup; gateway fails to start |
| third_party_outages | `ai_agent_core_engine` loopback unreachable for `invoke_ask_model` | `askOperationHub` raises with error logged; HTTP 200 with GraphQL `errors` array; no partial session state corruption |
| cache_failures | `HybridCacheEngine` miss/stale | SafeDataLoader falls back to fresh query; `normalize_model` normalizes cached shape; no HTTP-level error |
| rls_bypass_attempt | Superuser session queries cross-tenant data with wrong `Part-Id` | Superuser bypasses RLS by design; application must set `app.tenant_id` for non-superuser roles |
| predecessor_cycle | `agent_actions` predecessors form a cycle | `init_in_degree` produces incorrect in_degree values; `MAX_ITERATIONS` safety limit in `_handle_pending_agents` prevents infinite loop |
| max_iterations | Session stuck in pending state for >10 iterations | `_handle_pending_agents` detects `iteration_count >= MAX_ITERATIONS`; session marked `failed` with error log |
| gateway_graphql_error | GraphQL query syntax error | Gateway returns HTTP 200 with `{"errors": [...]}` array; no HTTP 500 |
| wrong_part_id | `Part-Id` header missing or malformed | Gateway raises `ValueError` for missing `endpoint_id` or `part_id`; HTTP 500 or 400 with error message |

## 9. Data Reconciliation Checks

| Check | Rule | Tolerance |
|---|---|---|
| Referential integrity | No orphaned sessions (every `coordination_uuid` resolves to a coordination); no orphaned session_agents (every `session_uuid` resolves); no orphaned session_runs | 0 |
| Count consistency | Entities created == entities persisted (per type) | 0 |
| Backend parity | DynamoDB HTTP response == PostgreSQL HTTP response for the same scenario (field-by-field) | numeric: 0.01; otherwise exact |
| Cache freshness | Post-mutation query returns updated field values (no stale reads) | 0 mismatches |
| Agent validation | `task.subtask_queries` only contains `agent_uuid` values from coordination's `agents` list | 0 invalid |
| In-degree correctness | `session_agent.in_degree == count of predecessors in agent_action.predecessors` | 0 |
| Timestamp drift | `updated_at` advances on every successful mutation | 0 (must strictly increase) |
| Audit completeness | Every `insert_update` sets `updated_by` and `updated_at` | 0 missing |
| RLS enforcement | Cross-tenant query returns `null` for non-superuser sessions via gateway HTTP | 0 cross-tenant reads |
| JSONB filter parity | Same filter produces same result count under DynamoDB and PostgreSQL via gateway HTTP | 0 diff |
| Agent_action structure | `agent_action` contains `primary_path`, `user_in_the_loop`, `predecessors`, `action_function` keys | 0 missing keys |
| HTTP response structure | Every gateway GraphQL response has valid JSON `{data, errors}` envelope | 0 malformed |
| Auth token validity | All GraphQL POST requests carry valid `Authorization: Bearer` header | 0 missing |

## 10. Entry and Exit Criteria

**Entry criteria (testing may begin when):**

- SOP is approved.
- Local gateway is running and reachable.
- `ai_coordination_engine` is loaded into gateway (verified via `ping` query).
- `.env` names are configured (`GATEWAY_BASE_URL`, `TOKEN_USERNAME`, `TOKEN_PASSWORD`, `endpoint_id`, `part_id`).
- Backend schema provisioned: `alembic upgrade head` (PostgreSQL) or `initialize_tables` (DynamoDB) at gateway startup.
- Authentication succeeds (`/auth/token` returns JWT).
- `ping` query returns valid greeting via gateway HTTP.
- No destructive cleanup is required.

**Exit criteria (certification may be issued when):**
- All P0 and P1 scenarios pass (INT-HTTP-000, INT-HTTP-001, INT-HTTP-003, INT-HTTP-004, INT-HTTP-006, INT-HTTP-007, INT-HTTP-008, INT-HTTP-009, INT-HTTP-010, INT-HTTP-011, INT-HTTP-013, INT-HTTP-014, INT-HTTP-015).
- Coverage ≥ 80% of scenarios in Section 7 executed (not skipped).
- No unexpected error responses remain (HTTP 4xx/5xx or GraphQL `errors` arrays).
- Any defects or data-contract issues found during execution have been fixed and retested.
- The final full dependency-ordered live suite has passed after the last fix.
- Per-call function results are exported to `docs/`.
- Any expected live no-op behavior is explicitly documented.
- Open environment warnings are listed as non-blocking or resolved.
- Backend parity (INT-HTTP-013) shows zero field-level diffs between DynamoDB and PostgreSQL for the mirrored scenarios.

## 11. CI Trigger and Cadence

| Trigger | Scope run | Required to pass |
|---|---|---|
| Manual local validation | full live suite via `run_http_integration.py` | yes for certification |
| Pre-release | full live suite plus report export (`--export`) | yes |
| Pull request | INT-HTTP-000, INT-HTTP-001, INT-HTTP-003, INT-HTTP-006 (smoke subset) | yes — blocks merge |
| Nightly | full suite against isolated test tenant | report only (non-blocking) |
| Gateway transport change | full live suite plus `--list-operations` verification | yes |
| Backend switch | full live suite under both `DB_BACKEND` values (restart gateway between runs) | yes |

## 12. Reporting and Certification Expectations

### 12.1 Report Format and Location

- **Report format:** Markdown.
- **Report artifact:** `docs/test_results/http_integration_results.md` (default export path from `run_http_integration.py --export`).
- **Required certification decision:** `Integration Certified`, `Ready for UAT`, `Ready for Production`, `Ready with Conditions`, or `Not Ready`.
- **Distribution:** `bibow` (test owner + release manager).

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

> Every GraphQL HTTP POST, auth call, CLI command, pytest invocation, SQL
> query, and function call executed during the certification run must be
> recorded as a separate block in the Function Results section, **in execution
> order**.

Each call block must contain:

| Field | Required | Description |
|---|---|---|
| **Number** | yes | Sequential call number (1, 2, 3, ...) |
| **Group** | yes | Logical group: `Environment`, `Schema`, `Dependency`, `Seed`, `Tests`, `Transaction`, `Resilience`, `Reconciliation` |
| **Method** | yes | The exact method/function/CLI invoked (e.g. `POST /auth/token`, `POST /{endpoint_id}/ai_coordination_graphql`, `alembic upgrade head`) |
| **Short description** | yes | One-line summary of what the call does |
| **Status** | yes | `pass`, `fail`, `error`, `skipped`, or `blocked` |
| **Elapsed** | yes | Duration in milliseconds or seconds |
| **Scenario ID** | yes | SOP scenario reference (e.g. `INT-HTTP-001`, `INT-HTTP-009`) |
| **Arguments** | yes | Exact input arguments as JSON (HTTP headers, GraphQL query document, variables, function kwargs) |
| **Output** | yes | Returned output as JSON (HTTP status, GraphQL response payload, row counts). Truncate oversized payloads with `... (truncated)` marker. |
| **Expected** | on failure only | Expected shape or value when status is `fail` or `error` |
| **Error/diff** | on failure only | Error message, status code, or expected-vs-actual diff |

#### GraphQL HTTP Call Recording (mandatory for all transaction and resilience scenarios)

Every `POST /{endpoint_id}/ai_coordination_graphql` call must be recorded with
the **full GraphQL document** and the **full response payload**.

**Arguments block for a GraphQL HTTP call must include:**

```json
{
  "method": "POST /{endpoint_id}/ai_coordination_graphql",
  "http_request": {
    "url": "http://localhost:8765/gpt/ai_coordination_graphql",
    "headers": {
      "Authorization": "Bearer ***",
      "Part-Id": "neprodai",
      "Content-Type": "application/json"
    },
    "DB_BACKEND": "postgresql"
  },
  "graphql_document": "mutation InsertUpdateCoordination($cu:String!,$name:String!,$agents:[JSONCamelCase],$by:String!){insertUpdateCoordination(coordinationUuid:$cu,coordinationName:$name,agents:$agents,updatedBy:$by){coordination{coordinationUuid coordinationName agents{agentUuid agentName agentType}}}}",
  "graphql_operation": "mutation insertUpdateCoordination",
  "variables": {
    "cu": "abc-123",
    "name": "Test Coordination",
    "agents": [{"agentUuid": "a1", "agentName": "Agent 1", "agentType": "task", "agentDescription": "Task agent"}],
    "by": "cert"
  }
}
```

**Output block for a GraphQL HTTP call must include the full response:**

```json
{
  "http_status": 200,
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

**Rules for GraphQL HTTP call recording:**

1. **Record the full `graphql_document`** — the complete GraphQL mutation or query string, including all field selections.
2. **Record the full `variables`** — the exact variables dict passed. Redact secrets but keep all business values.
3. **Record the full HTTP response** — HTTP status code, `data` object, and `errors` array. For list queries, truncate only if > 20 items.
4. **Record `errors`** — if present, include the full error array.
5. **Record `http_request` context** — URL, headers (redacted `Authorization`), `Part-Id`, and `DB_BACKEND` for backend auditability.
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

## 13. Comparison with Companion SOP (Direct In-Process Transport)

| Aspect | Companion SOP (`INTEGRATION_SCENARIOS_SOP.md`) | This SOP (`integration_scenarios_sop_http.md`) |
|---|---|---|
| Test script | `test_integration_scenarios.py` (pytest) | `run_http_integration.py` (async HTTP) |
| Transport | direct in-process `AICoordinationEngine.ai_coordination_graphql()` | HTTP POST to gateway `/{endpoint_id}/ai_coordination_graphql` |
| Gateway involved | no | yes (`silvaengine_gateway` dispatch) |
| Auth | none (in-process) | JWT Bearer token from `POST /auth/token` |
| Tenant routing | `partition_key` in params context | `Part-Id` request header → gateway builds `partition_key` |
| Backend selection | `DB_BACKEND` per `Config.initialize` call | `DB_BACKEND` at gateway startup; restart to switch |
| Execution model | synchronous (pytest) | asynchronous (`asyncio` + `aiohttp`/`httpx`) |
| Report artifact | `docs/live_integration_results_<YYYYMMDD>.md` | `docs/test_results/http_integration_results.md` |
| Additional validation | repository dispatch, adoption guard | HTTP transport layer, gateway dispatch, JWT auth, `Part-Id` routing, HTTP status codes |
| AACE loopback | mocked in-process via `unittest.mock.patch` | cannot mock (gateway is separate process); use `functs_on_local` for real loopback or skip |
| RLS enforcement | `Config._set_rls_context` called directly | `Config._set_rls_context` called by `dispatch_graphql` from `Part-Id` context |
| Session lifecycle | test handles `db_session.remove()` cleanup | `dispatch_graphql` handles `rollback()` + `remove()` automatically per request |

## 14. Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| Test owner | `bibow` | `<pending>` | `<pending>` |
| Release manager | `<pending>` | `<pending>` | `<pending>` |
| DB owner (PostgreSQL) | `<pending>` | `<pending>` | `<pending>` |
| AWS account owner (DynamoDB) | `<pending>` | `<pending>` | `<pending>` |
| AACE team (loopback dependency) | `<pending>` | `<pending>` | `<pending>` |

---

## Pending Confirmation Items

Before any test execution begins, the following placeholders need
explicit decisions:

1. **Test script creation** — `run_http_integration.py` does not yet exist; confirm it should be created following the pattern from `mcp_hospirfq_processor/tests/run_http_integration.py`.
2. **Target environment** (Section 1): single environment for both backends (restart gateway to switch), or separate `dev` (DynamoDB) + `qa` (PostgreSQL)?
3. **SOP owner / contact** (Section 1): confirm `bibow` as owner.
4. **Credential source confirmation** (Section 3): confirm `.env` + `GATEWAY_BASE_URL` / `TOKEN_*` as the approved secret sources.
5. **Dependency owners** (Section 4): who owns DynamoDB, PostgreSQL, and each library dependency for readiness sign-off?
6. **Provisioning policy** (Section 3): confirm auto-provisioning of the disposable PostgreSQL schema is allowed in the target environment.
7. **CI cadence** (Section 11): confirm the PR-block / nightly-report / pre-release-block split.
8. **Distribution list** (Section 12): who receives the certification report?
9. **Sign-off roles** (Section 14): names for test owner, release manager, DB owner, AWS account owner, AACE team.
10. **AACE loopback scope** (INT-HTTP-009, INT-HTTP-011): confirm whether live `ai_agent_core_engine` loopback calls are in scope or remain mocked; if live, identify the AACE team owner.
11. **Async Lambda dispatch scope** (INT-HTTP-009, INT-HTTP-011, INT-HTTP-012): confirm whether async Lambda invocations are validated (requires Lambda function deployed) or only the handler logic is tested in-process via `execute_mode=local_for_all`.

Once these are confirmed, the SOP status moves from `draft` to `approved` and
test execution may proceed.