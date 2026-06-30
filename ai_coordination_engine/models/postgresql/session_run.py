# -*- coding: utf-8 -*-
"""PostgreSQL model for SessionRun — has partition_key (nullable in DDB), RLS-protected.

Hash key: session_uuid (non-partition-key)
Range key: run_uuid
partition_key is nullable in DynamoDB — populate from parent session in PG.
LSIs: thread_uuid-index, agent_uuid-index
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import Column, Index, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class SessionRunModel(Base):
    __tablename__ = "ace_session_runs"

    session_uuid = Column(UUID(as_uuid=True), primary_key=True)
    run_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    partition_key = Column(String(128), nullable=True)
    thread_uuid = Column(UUID(as_uuid=True), nullable=False)
    agent_uuid = Column(String, nullable=False)
    coordination_uuid = Column(UUID(as_uuid=True), nullable=False)
    async_task_uuid = Column(String, nullable=False)
    session_agent_uuid = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_ace_session_runs_session_thread", "session_uuid", "thread_uuid"),
        Index("ix_ace_session_runs_session_agent", "session_uuid", "agent_uuid"),
        Index("ix_ace_session_runs_partition_updated", "partition_key", "updated_at"),
        Index("ix_ace_session_runs_coord", "coordination_uuid"),
    )

    def __repr__(self):
        return f"<SessionRunModel(session_uuid={self.session_uuid}, run_uuid={self.run_uuid})>"