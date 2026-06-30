# -*- coding: utf-8 -*-
"""DynamoDB repository wrappers — thin adapters over PynamoDB model modules.

Each wrapper delegates to the existing model-module functions and normalizes
results via ``_normalize()`` so that PynamoDB model instances never leak above
the repository boundary.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Dict

from ..base import EntityRepository
from .coordination_repo import CoordinationDynamoDBRepository
from .session_repo import SessionDynamoDBRepository
from .session_agent_repo import SessionAgentDynamoDBRepository
from .session_run_repo import SessionRunDynamoDBRepository
from .task_repo import TaskDynamoDBRepository
from .task_schedule_repo import TaskScheduleDynamoDBRepository

__all__ = [
    "EntityRepository",
    "CoordinationDynamoDBRepository",
    "SessionDynamoDBRepository",
    "SessionAgentDynamoDBRepository",
    "SessionRunDynamoDBRepository",
    "TaskDynamoDBRepository",
    "TaskScheduleDynamoDBRepository",
    "register_all",
]


def register_all(registry: Dict[str, EntityRepository]) -> None:
    """Register all DynamoDB repository instances into *registry*."""
    registry["coordination"] = CoordinationDynamoDBRepository()
    registry["session"] = SessionDynamoDBRepository()
    registry["session_agent"] = SessionAgentDynamoDBRepository()
    registry["session_run"] = SessionRunDynamoDBRepository()
    registry["task"] = TaskDynamoDBRepository()
    registry["task_schedule"] = TaskScheduleDynamoDBRepository()