# -*- coding: utf-8 -*-
"""PostgreSQL model for Task — has partition_key attr, RLS-protected.

Hash key: coordination_uuid (non-partition-key)
Range key: task_uuid
Has partition_key column for RLS.
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import Column, Index, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class TaskModel(Base):
    __tablename__ = "ace_tasks"

    coordination_uuid = Column(String, primary_key=True)
    task_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    partition_key = Column(String(128), nullable=False)
    task_name = Column(String, nullable=False)
    task_description = Column(Text, nullable=True)
    initial_task_query = Column(Text, nullable=False)
    subtask_queries = Column(JSONB, default=list)
    agent_actions = Column(JSONB, default=dict)
    updated_by = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_ace_tasks_partition_updated", "partition_key", "updated_at"),
    )

    def __repr__(self):
        return f"<TaskModel(coordination_uuid={self.coordination_uuid}, task_uuid={self.task_uuid})>"