# -*- coding: utf-8 -*-
"""Create uuid-ossp extension and ace_coordinations table.

Revision ID: 0001
Revises:
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "ace_coordinations",
        sa.Column("partition_key", sa.String(128), primary_key=True, nullable=False),
        sa.Column("coordination_uuid", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("endpoint_id", sa.String, nullable=False),
        sa.Column("part_id", sa.String, nullable=False),
        sa.Column("coordination_name", sa.String, nullable=False),
        sa.Column("coordination_description", sa.Text),
        sa.Column("agents", JSONB, default=list),
        sa.Column("updated_by", sa.String, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ace_coordinations_partition_updated", "ace_coordinations", ["partition_key", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_ace_coordinations_partition_updated", table_name="ace_coordinations")
    op.drop_table("ace_coordinations")