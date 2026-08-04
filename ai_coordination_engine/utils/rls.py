# -*- coding: utf-8 -*-
"""RLS (Row-Level Security) helpers for PostgreSQL multi-tenant isolation.

Provides:
- set_rls_context(session, partition_key): sets SET LOCAL app.tenant_id
- create_rls_policies(engine): applies RLS policies to all partition-keyed tables
"""

from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)

# All tables that should have RLS policies (all 6 ACE tables)
_RLS_TABLES = [
    "coordinations",
    "sessions",
    "session_agents",
    "session_runs",
    "tasks",
    "task_schedules",
]


def set_rls_context(session: Any, partition_key: str) -> None:
    """Set the RLS tenant context for the current database session.

    Must be called before any query that touches RLS-protected tables.
    """
    session.execute(
        text("SET LOCAL app.tenant_id = :tenant"),
        {"tenant": partition_key},
    )


def create_rls_policies(engine: Any) -> None:
    """Apply RLS policies to all ACE tables.

    For each table:
    1. ENABLE ROW LEVEL SECURITY
    2. CREATE POLICY tenant_isolation USING (partition_key = current_setting('app.tenant_id', true))

    This enforces tenant isolation at the database level — a session with
    tenant A's partition_key cannot read tenant B's rows.
    """
    from ..models.postgresql.base import prefixed_table

    with engine.connect() as conn:
        for table_name in _RLS_TABLES:
            actual_name = prefixed_table(table_name)
            try:
                conn.execute(
                    text(f"ALTER TABLE {actual_name} ENABLE ROW LEVEL SECURITY")
                )
                # Drop existing policy if any (idempotent)
                conn.execute(
                    text(f"DROP POLICY IF EXISTS tenant_isolation ON {actual_name}")
                )
                # Create the tenant isolation policy
                conn.execute(
                    text(
                        f"CREATE POLICY tenant_isolation ON {actual_name} "
                        f"USING (partition_key = current_setting('app.tenant_id', true))"
                    )
                )
                logger.debug(f"RLS policy applied to {actual_name}")
            except Exception as exc:
                logger.warning(f"Failed to apply RLS to {actual_name}: {exc}")
        conn.commit()
