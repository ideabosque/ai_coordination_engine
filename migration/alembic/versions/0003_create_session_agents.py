# -*- coding: utf-8 -*-
"""Create ace_session_agents table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-29

Note: partition_key column is ADDED in PostgreSQL (not present in DynamoDB)
to enable RLS. Populated from the parent session's partition_key on insert.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ace_session_agents",
        sa.Column("session_uuid", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_agent_uuid", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("partition_key", sa.String(128), nullable=False),
        sa.Column("coordination_uuid", UUID(as_uuid=True), nullable=False),
        sa.Column("agent_uuid", sa.String, nullable=False),
        sa.Column("agent_action", JSONB, nullable=True),
        sa.Column("user_input", sa.Text, nullable=True),
        sa.Column("agent_input", sa.Text, nullable=True),
        sa.Column("agent_output", sa.Text, nullable=True),
        sa.Column("in_degree", sa.Integer, default=0),
        sa.Column("state", sa.String, default="initial"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("updated_by", sa.String, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ace_session_agents_session_updated", "ace_session_agents", ["session_uuid", "updated_at"])
    op.create_index("ix_ace_session_agents_partition_updated", "ace_session_agents", ["partition_key", "updated_at"])
    op.create_index("ix_ace_session_agents_coord", "ace_session_agents", ["coordination_uuid"])
    op.create_index("ix_ace_session_agents_agent", "ace_session_agents", ["agent_uuid"])
    op.create_index("ix_ace_session_agents_action_gin", "ace_session_agents", ["agent_action"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_ace_session_agents_action_gin", table_name="ace_session_agents")
    op.drop_index("ix_ace_session_agents_agent", table_name="ace_session_agents")
    op.drop_index("ix_ace_session_agents_coord", table_name="ace_session_agents")
    op.drop_index("ix_ace_session_agents_partition_updated", table_name="ace_session_agents")
    op.drop_index("ix_ace_session_agents_session_updated", table_name="ace_session_agents")
    op.drop_table("ace_session_agents")