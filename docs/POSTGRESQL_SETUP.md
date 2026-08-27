# PostgreSQL Setup Guide

> Project: `ai_coordination_engine`
> Created: 2026-06-29

## Prerequisites

- PostgreSQL 14+ with the `uuid-ossp` extension
- Python 3.8+

## Installation

```bash
pip install ai-coordination-engine[postgresql]
```

This installs:
- `SQLAlchemy>=1.4` — ORM and database toolkit
- `psycopg2-binary>=2.9` — PostgreSQL adapter
- `alembic>=1.10` — Database migration tool

## Database Setup

### 1. Create Database and User

```sql
CREATE DATABASE silvaengine;
CREATE USER silvaengine WITH PASSWORD 'silvaengine';
GRANT ALL PRIVILEGES ON DATABASE silvaengine TO silvaengine;

-- Connect to the database and enable uuid-ossp
\c silvaengine
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 2. Configure the Engine

Set the following environment variables or pass them in the gateway setting:

```env
DB_BACKEND=postgresql
PG_HOST=localhost
PG_PORT=5432
PG_USER=silvaengine
PG_PASSWORD=silvaengine
PG_DB=silvaengine

# Or use a single DATABASE_URL (overrides PG_* keys)
# DATABASE_URL=postgresql+psycopg2://silvaengine:silvaengine@localhost:5432/silvaengine

# Per-module table prefix (forwarded by the gateway)
PG_TABLE_PREFIX=
ACE_PG_TABLE_PREFIX=
```

### 3. Run Migrations

```bash
# From the project root
export DATABASE_URL="postgresql+psycopg2://silvaengine:silvaengine@localhost:5432/silvaengine"
alembic -c migration/alembic.ini upgrade head
```

This creates all 6 entity tables with proper indexes and applies RLS policies (migration 0007):

| Migration | Table | Notes |
| --- | --- | --- |
| `0001` | `ace_coordinations` | Creates `uuid-ossp` extension |
| `0002` | `ace_sessions` | |
| `0003` | `ace_session_agents` | `partition_key` added in PG (not in DynamoDB) |
| `0004` | `ace_session_runs` | |
| `0005` | `ace_tasks` | |
| `0006` | `ace_task_schedules` | |
| `0007` | — (RLS) | Enables Row-Level Security on all 6 tables |

### 4. Verify Installation

```bash
psql -U silvaengine -d silvaengine -c "\dt"
```

You should see tables: `ace_coordinations`, `ace_sessions`, `ace_session_agents`,
`ace_session_runs`, `ace_tasks`, `ace_task_schedules`.

## RLS Setup

Row-Level Security is applied automatically via migration `0007`:

```sql
ALTER TABLE ace_coordinations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ace_coordinations
    USING (partition_key = current_setting('app.tenant_id', true));
```

This is applied to all 6 tables. RLS context is set per-request:

```python
Config._set_rls_context(partition_key)  # SET LOCAL app.tenant_id = :partition_key
# ... GraphQL execution ...
Config.db_session.remove()              # scoped_session cleanup
```

**SessionAgent** has `partition_key` added in PostgreSQL (not present in DynamoDB)
to enable uniform RLS. It is populated from the parent session's `partition_key` on insert.

## Connection Pooling

The SQLAlchemy engine is configured with:
- `pool_size=10` — 10 persistent connections
- `pool_recycle=7200` — recycle connections after 2 hours
- `pool_pre_ping=True` — health-check connections before use
- `echo=False` — set to True for SQL debugging

## Optional AWS Services

ACE uses AWS Lambda for async dispatch, S3 for module downloads, SES for email,
and DynamoDB for `FunctionModel` (shared platform table). These are initialized
even in PostgreSQL mode when credentials are present.

Without AWS credentials:
- Async task dispatch via Lambda will be unavailable
- S3-based module downloads will not work
- SES email notifications will not be available

With AWS credentials:
- All features work, but entity persistence uses PostgreSQL instead of DynamoDB

## Environment Variables

| Env Var | Setting Key | Description |
| --- | --- | --- |
| `DB_BACKEND` | `db_backend` | `dynamodb` (default) or `postgresql` |
| `DATABASE_URL` | `database_url` | Full connection URL (takes precedence over PG_*) |
| `PG_HOST` | `db_host` | PostgreSQL host (default: `localhost`) |
| `PG_PORT` | `db_port` | PostgreSQL port (default: `5432`) |
| `PG_USER` | `db_user` | PostgreSQL user (default: `silvaengine`) |
| `PG_PASSWORD` | `db_password` | PostgreSQL password |
| `PG_DB` | `db_schema` | PostgreSQL database name (default: `silvaengine`) |
| `PG_TABLE_PREFIX` | `pg_table_prefix` | Global table prefix (default: `""`) |
| `ACE_PG_TABLE_PREFIX` | `ace_pg_table_prefix` | Per-module prefix forwarded by gateway |

## Switching Back to DynamoDB

Set `DB_BACKEND=dynamodb` (or remove the `db_backend` key entirely — DynamoDB
is the default). No code changes needed — the repository dispatch boundary
handles the switch automatically.

## Troubleshooting

### "uuid_generate_v4() function does not exist"

Run: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
(Migration `0001` does this automatically.)

### "psycopg2 import error"

Ensure `psycopg2-binary` is installed: `pip install psycopg2-binary`

### "SQLAlchemy not found"

Install PostgreSQL extras: `pip install ai-coordination-engine[postgresql]`

### "could not connect to server"

Verify your `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DB` values
or `DATABASE_URL`. Ensure PostgreSQL is running and accepting connections
on the specified host/port.

### "No repository registered for entity '...' on backend 'postgresql'"

A PostgreSQL repository file failed to import. Check that all PG model
modules compile and that SQLAlchemy is installed.