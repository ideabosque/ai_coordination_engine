# -*- coding: utf-8 -*-
"""Enable RLS policies on all 6 ACE tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-29

Applies Row-Level Security policies to all ACE tables for multi-tenant isolation.
Each table gets: ENABLE ROW LEVEL SECURITY + CREATE POLICY tenant_isolation
USING (partition_key = current_setting('app.tenant_id', true))
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RLS_TABLES = [
    "ace_coordinations",
    "ace_sessions",
    "ace_session_agents",
    "ace_session_runs",
    "ace_tasks",
    "ace_task_schedules",
]


def upgrade() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table_name} "
            f"USING (partition_key = current_setting('app.tenant_id', true))"
        )


def downgrade() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")