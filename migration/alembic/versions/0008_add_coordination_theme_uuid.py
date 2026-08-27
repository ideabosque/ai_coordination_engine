# -*- coding: utf-8 -*-
"""Add theme_uuid to ace_coordinations.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ace_coordinations",
        sa.Column("theme_uuid", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ace_coordinations", "theme_uuid")
