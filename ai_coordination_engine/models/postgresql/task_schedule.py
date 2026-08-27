# -*- coding: utf-8 -*-
"""PostgreSQL model for TaskSchedule — has partition_key attr, RLS-protected.

Hash key: task_uuid (non-partition-key)
Range key: schedule_uuid
Has partition_key column for RLS.
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import Column, Index, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class TaskScheduleModel(Base):
    __tablename__ = "ace_task_schedules"

    task_uuid = Column(UUID(as_uuid=True), primary_key=True)
    schedule_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    coordination_uuid = Column(String, nullable=False)
    partition_key = Column(String(128), nullable=False)
    schedule = Column(String, nullable=False)
    status = Column(String, default="initial")
    updated_by = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_ace_task_schedules_partition_updated", "partition_key", "updated_at"),
        Index("ix_ace_task_schedules_coord", "coordination_uuid"),
    )

    def __repr__(self):
        return f"<TaskScheduleModel(task_uuid={self.task_uuid}, schedule_uuid={self.schedule_uuid})>"