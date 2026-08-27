# -*- coding: utf-8 -*-
"""Alembic env.py — resolves DATABASE_URL > Config > alembic.ini fallback."""
from __future__ import print_function

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add the project root to sys.path so we can import ai_coordination_engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve the database URL: DATABASE_URL env var > Config > alembic.ini fallback
database_url = os.getenv("DATABASE_URL")

if not database_url:
    # Try to get from Config if it's been initialized
    try:
        from ai_coordination_engine.handlers.config import Config
        if getattr(Config, "DB_BACKEND", None) == "postgresql" and Config.db_session is not None:
            database_url = str(Config._db_engine.url)
    except Exception:
        pass

if not database_url:
    # Fall back to PG_* env vars
    pg_host = os.getenv("PG_HOST", "localhost")
    pg_port = os.getenv("PG_PORT", "5432")
    pg_user = os.getenv("PG_USER", "silvaengine")
    pg_password = os.getenv("PG_PASSWORD", "silvaengine")
    pg_db = os.getenv("PG_DB", "silvaengine")
    database_url = f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

config.set_main_option("sqlalchemy.url", database_url)

# Import the PG table prefix
pg_table_prefix = os.getenv("PG_TABLE_PREFIX", os.getenv("ACE_PG_TABLE_PREFIX", ""))

# Set up target metadata from PostgreSQL models
target_metadata = None
try:
    from ai_coordination_engine.models.postgresql.base import Base
    # Try to import all entity models so they register with Base.metadata
    import importlib
    for entity in ["coordination", "session", "session_agent", "session_run", "task", "task_schedule"]:
        try:
            importlib.import_module(f"ai_coordination_engine.models.postgresql.{entity}")
        except ImportError:
            pass
    target_metadata = Base.metadata
except Exception:
    pass


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        version_table="ace_alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            version_table="ace_alembic_version",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()