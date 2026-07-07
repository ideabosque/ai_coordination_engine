# -*- coding: utf-8 -*-
"""PostgreSQL model for Coordination — partition-keyed, RLS-protected."""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import Column, Index, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import deferred

from .base import Base, prefixed_table


class CoordinationModel(Base):
    __tablename__ = "ace_coordinations"

    partition_key = Column(String(128), primary_key=True)
    coordination_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    endpoint_id = Column(String, nullable=False)
    part_id = Column(String, nullable=False)
    coordination_name = Column(String, nullable=False)
    coordination_description = Column(Text)
    agents = Column(JSONB, default=list)
    theme_uuid = Column(String, nullable=True)
    updated_by = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_ace_coordinations_partition_updated", "partition_key", "updated_at"),
    )

    def __repr__(self):
        return f"<CoordinationModel(partition_key={self.partition_key}, coordination_uuid={self.coordination_uuid})>"