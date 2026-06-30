# -*- coding: utf-8 -*-
"""Create ace_tasks table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ace_tasks",
        sa.Column("coordination_uuid", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("task_uuid", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("partition_key", sa.String(128), nullable=False),
        sa.Column("task_name", sa.String, nullable=False),
        sa.Column("task_description", sa.Text, nullable=True),
        sa.Column("initial_task_query", sa.Text, nullable=False),
        sa.Column("subtask_queries", JSONB, default=list),
        sa.Column("agent_actions", JSONB, default=dict),
        sa.Column("updated_by", sa.String, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ace_tasks_partition_updated", "ace_tasks", ["partition_key", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_ace_tasks_partition_updated", table_name="ace_tasks")
    op.drop_table("ace_tasks")