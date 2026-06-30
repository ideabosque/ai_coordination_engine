# -*- coding: utf-8 -*-
"""PostgreSQL model for SessionAgent — partition_key added in PG (not in DynamoDB), RLS-protected.

Hash key: session_uuid (non-partition-key)
Range key: session_agent_uuid
partition_key column ADDED in PG for RLS (populated from parent session).
agent_action is JSONB for nested map filtering (primary_path, user_in_the_loop, predecessors).
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import Column, Index, Integer, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class SessionAgentModel(Base):
    __tablename__ = "ace_session_agents"

    session_uuid = Column(UUID(as_uuid=True), primary_key=True)
    session_agent_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    # partition_key is NOT in the DynamoDB model — added in PG for RLS.
    # Populated from the parent session's partition_key on insert.
    partition_key = Column(String(128), nullable=False)
    coordination_uuid = Column(UUID(as_uuid=True), nullable=False)
    agent_uuid = Column(String, nullable=False)
    agent_action = Column(JSONB, nullable=True)
    user_input = Column(Text, nullable=True)
    agent_input = Column(Text, nullable=True)
    agent_output = Column(Text, nullable=True)
    in_degree = Column(Integer, default=0)
    state = Column(String, default="initial")
    notes = Column(Text, nullable=True)
    updated_by = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_ace_session_agents_session_updated", "session_uuid", "updated_at"),
        Index("ix_ace_session_agents_partition_updated", "partition_key", "updated_at"),
        Index("ix_ace_session_agents_coord", "coordination_uuid"),
        Index("ix_ace_session_agents_agent", "agent_uuid"),
        # GIN index for JSONB agent_action filtering (primary_path, user_in_the_loop, predecessors)
        Index("ix_ace_session_agents_action_gin", "agent_action", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<SessionAgentModel(session_uuid={self.session_uuid}, session_agent_uuid={self.session_agent_uuid})>"