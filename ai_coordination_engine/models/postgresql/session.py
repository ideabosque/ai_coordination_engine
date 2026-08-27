# -*- coding: utf-8 -*-
"""PostgreSQL model for Session — has partition_key attr, RLS-protected.

Hash key: coordination_uuid (non-partition-key)
Range key: session_uuid
Has partition_key column for RLS.
LSIs: user_id-index, task_uuid-index
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import Column, Index, Integer, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class SessionModel(Base):
    __tablename__ = "ace_sessions"

    coordination_uuid = Column(String, primary_key=True)
    session_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    partition_key = Column(String(128), nullable=False)
    task_uuid = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(String, nullable=True)
    task_query = Column(Text, nullable=True)
    input_files = Column(JSONB, default=list)
    iteration_count = Column(Integer, default=0)
    subtask_queries = Column(JSONB, default=list)
    status = Column(String, default="initial")
    logs = Column(Text, nullable=True)
    updated_by = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_ace_sessions_coord_user", "coordination_uuid", "user_id"),
        Index("ix_ace_sessions_coord_task", "coordination_uuid", "task_uuid"),
        Index("ix_ace_sessions_partition_updated", "partition_key", "updated_at"),
    )

    def __repr__(self):
        return f"<SessionModel(coordination_uuid={self.coordination_uuid}, session_uuid={self.session_uuid})>"