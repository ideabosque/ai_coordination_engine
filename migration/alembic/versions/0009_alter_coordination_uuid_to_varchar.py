# -*- coding: utf-8 -*-
"""Alter coordination_uuid columns from UUID to VARCHAR on all 6 ACE tables.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-07

DynamoDB stores coordination_uuid as a UnicodeAttribute (string), and some
values are not valid UUIDs (e.g. numeric strings like "09047568911300349976").
The PG columns were originally UUID type, which rejects non-UUID strings.
This migration converts all coordination_uuid columns to VARCHAR, preserving
existing UUID data by casting it to its text representation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table_name, is_primary_key)
_COORDINATION_UUID_COLUMNS = [
    ("ace_coordinations", True),
    ("ace_sessions", True),
    ("ace_session_agents", False),
    ("ace_session_runs", False),
    ("ace_tasks", True),
    ("ace_task_schedules", False),
]


def upgrade() -> None:
    for table_name, is_pk in _COORDINATION_UUID_COLUMNS:
        # Drop indexes that include coordination_uuid before altering
        if table_name == "ace_sessions":
            op.drop_index("ix_ace_sessions_coord_user", table_name=table_name)
            op.drop_index("ix_ace_sessions_coord_task", table_name=table_name)
        elif table_name == "ace_session_agents":
            op.drop_index("ix_ace_session_agents_coord", table_name=table_name)
        elif table_name == "ace_session_runs":
            op.drop_index("ix_ace_session_runs_coord", table_name=table_name)
        elif table_name == "ace_task_schedules":
            op.drop_index("ix_ace_task_schedules_coord", table_name=table_name)

        # Alter column type from UUID to VARCHAR, casting existing data to text
        op.alter_column(
            table_name,
            "coordination_uuid",
            type_=sa.String(),
            postgresql_using="coordination_uuid::text",
            existing_type=UUID(as_uuid=True),
        )

    # Recreate indexes
    op.create_index("ix_ace_sessions_coord_user", "ace_sessions", ["coordination_uuid", "user_id"])
    op.create_index("ix_ace_sessions_coord_task", "ace_sessions", ["coordination_uuid", "task_uuid"])
    op.create_index("ix_ace_session_agents_coord", "ace_session_agents", ["coordination_uuid"])
    op.create_index("ix_ace_session_runs_coord", "ace_session_runs", ["coordination_uuid"])
    op.create_index("ix_ace_task_schedules_coord", "ace_task_schedules", ["coordination_uuid"])


def downgrade() -> None:
    # Drop recreated indexes
    op.drop_index("ix_ace_task_schedules_coord", table_name="ace_task_schedules")
    op.drop_index("ix_ace_session_runs_coord", table_name="ace_session_runs")
    op.drop_index("ix_ace_session_agents_coord", table_name="ace_session_agents")
    op.drop_index("ix_ace_sessions_coord_task", table_name="ace_sessions")
    op.drop_index("ix_ace_sessions_coord_user", table_name="ace_sessions")

    for table_name, is_pk in _COORDINATION_UUID_COLUMNS:
        op.alter_column(
            table_name,
            "coordination_uuid",
            type_=UUID(as_uuid=True),
            postgresql_using="coordination_uuid::uuid",
            existing_type=sa.String(),
        )

    # Recreate original indexes
    op.create_index("ix_ace_sessions_coord_user", "ace_sessions", ["coordination_uuid", "user_id"])
    op.create_index("ix_ace_sessions_coord_task", "ace_sessions", ["coordination_uuid", "task_uuid"])
    op.create_index("ix_ace_session_agents_coord", "ace_session_agents", ["coordination_uuid"])
    op.create_index("ix_ace_session_runs_coord", "ace_session_runs", ["coordination_uuid"])
    op.create_index("ix_ace_task_schedules_coord", "ace_task_schedules", ["coordination_uuid"])