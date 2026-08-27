# AI Coordination Engine — Dual-Backend Configuration

> Project: `ai_coordination_engine`
> Last reviewed: 2026-06-29

## Backend Selection

ACE supports two persistence backends, selectable at deployment time:

| Setting | Default | Values |
| --- | --- | --- |
| `db_backend` | `dynamodb` | `dynamodb`, `postgresql` |

Set via environment variable (`db_backend=postgresql`) or the gateway setting dict.

## DynamoDB Mode (default)

- PynamoDB models under `ai_coordination_engine.models.dynamodb`
- DynamoDB DataLoaders (`RequestLoaders` with 8 loader properties)
- `@method_cache` on model getters and query list resolvers
- DynamoDB table initialization via `models.dynamodb.utils.initialize_tables`
- Tables: `ace-coordinations`, `ace-sessions`, `ace-session_agents`, `ace-session_runs`, `ace-tasks`, `ace-task_schedules`

## PostgreSQL Mode

- SQLAlchemy models under `ai_coordination_engine.models.postgresql`
- 7 Alembic migrations (`0001`–`0007`) under `migration/alembic/versions/`
- 6 PostgreSQL repository classes under `models.repositories.postgresql`
- PG DataLoaders (`PGRequestLoaders` with 8 loader properties)
- **RLS (Row-Level Security)** on all 6 tables for multi-tenant isolation
- Cache config is empty (PG repos don't use `@method_cache`)

### Connection Settings

| Env Var | Setting Key | Description |
| --- | --- | --- |
| `DATABASE_URL` | `database_url` | Full connection URL (takes precedence over PG_*) |
| `PG_HOST` | `db_host` | PostgreSQL host |
| `PG_PORT` | `db_port` | PostgreSQL port (default 5432) |
| `PG_USER` | `db_user` | PostgreSQL user |
| `PG_PASSWORD` | `db_password` | PostgreSQL password |
| `PG_DB` | `db_schema` | PostgreSQL database name |
| `PG_TABLE_PREFIX` | `pg_table_prefix` | Global table prefix (default: "") |
| `ACE_PG_TABLE_PREFIX` | `ace_pg_table_prefix` | Per-module prefix forwarded by gateway |

## RLS (Row-Level Security)

All 6 ACE tables have RLS policies applied (migration `0007`):

```sql
ALTER TABLE ace_coordinations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ace_coordinations
    USING (partition_key = current_setting('app.tenant_id', true));
```

RLS context is set per-request in `AICoordinationEngine.ai_coordination_graphql`:
```python
Config._set_rls_context(partition_key)  # SET LOCAL app.tenant_id = :partition_key
# ... GraphQL execution ...
Config.db_session.remove()  # scoped_session cleanup
```

**SessionAgent** has `partition_key` added in PostgreSQL (not present in DynamoDB) to enable uniform RLS. It is populated from the parent session's `partition_key` on insert.

## Cache Configuration

| Config | DynamoDB | PostgreSQL |
| --- | --- | --- |
| `CACHE_ENTITY_CONFIG` | 6 entities with module paths | Empty `{}` |
| `CACHE_RELATIONSHIPS` | 4 relationship edges | Empty `{}` |

The PG repositories still call `purge_entity_cascading_cache` after writes (a no-op under PG since cache config is empty), preserving parity for future opt-in.

## Gateway Integration

ACE is registered in `silvaengine_gateway/routes.yaml`:

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

**Important**: `config_init_style: kwargs` — ACE uses `Config.initialize(logger, **setting)`, not dict style.

The gateway reads `ace_pg_table_prefix` in `build_setting_from_env()` and forwards it to ACE's `Config.initialize()` via `config_overrides`.