# -*- coding: utf-8 -*-
"""Create ace_task_schedules table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ace_task_schedules",
        sa.Column("task_uuid", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("schedule_uuid", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("coordination_uuid", UUID(as_uuid=True), nullable=False),
        sa.Column("partition_key", sa.String(128), nullable=False),
        sa.Column("schedule", sa.String, nullable=False),
        sa.Column("status", sa.String, default="initial"),
        sa.Column("updated_by", sa.String, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ace_task_schedules_partition_updated", "ace_task_schedules", ["partition_key", "updated_at"])
    op.create_index("ix_ace_task_schedules_coord", "ace_task_schedules", ["coordination_uuid"])


def downgrade() -> None:
    op.drop_index("ix_ace_task_schedules_coord", table_name="ace_task_schedules")
    op.drop_index("ix_ace_task_schedules_partition_updated", table_name="ace_task_schedules")
    op.drop_table("ace_task_schedules")