# -*- coding: utf-8 -*-
"""Create ace_sessions table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ace_sessions",
        sa.Column("coordination_uuid", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_uuid", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("partition_key", sa.String(128), nullable=False),
        sa.Column("task_uuid", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.String, nullable=True),
        sa.Column("task_query", sa.Text, nullable=True),
        sa.Column("input_files", JSONB, default=list),
        sa.Column("iteration_count", sa.Integer, default=0),
        sa.Column("subtask_queries", JSONB, default=list),
        sa.Column("status", sa.String, default="initial"),
        sa.Column("logs", sa.Text, nullable=True),
        sa.Column("updated_by", sa.String, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ace_sessions_coord_user", "ace_sessions", ["coordination_uuid", "user_id"])
    op.create_index("ix_ace_sessions_coord_task", "ace_sessions", ["coordination_uuid", "task_uuid"])
    op.create_index("ix_ace_sessions_partition_updated", "ace_sessions", ["partition_key", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_ace_sessions_partition_updated", table_name="ace_sessions")
    op.drop_index("ix_ace_sessions_coord_task", table_name="ace_sessions")
    op.drop_index("ix_ace_sessions_coord_user", table_name="ace_sessions")
    op.drop_table("ace_sessions")