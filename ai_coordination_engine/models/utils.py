# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict


def _initialize_tables(logger: logging.Logger) -> None:
    """Initialize all DynamoDB tables for the AI Coordination Engine."""
    from .coordination import create_coordination_table
    from .session import create_session_table
    from .session_agent import create_session_agent_table
    from .session_run import create_session_run_table
    from .task import create_task_table
    from .task_schedule import create_task_schedule_table

    create_coordination_table(logger)
    create_session_table(logger)
    create_session_agent_table(logger)
    create_session_run_table(logger)
    create_task_table(logger)
    create_task_schedule_table(logger)


def _get_coordination(endpoint_id: str, coordination_uuid: str) -> Dict[str, Any]:
    """
    Get coordination as a dictionary for embedding purposes.

    This is used in validation contexts where we need coordination data
    but don't need the full GraphQL type with nested resolvers.

    Args:
        endpoint_id: The endpoint identifier
        coordination_uuid: The coordination UUID

    Returns:
        Dict containing coordination data
    """
    from .coordination import get_coordination

    coordination = get_coordination(endpoint_id, coordination_uuid)
    return {
        "endpoint_id": coordination.endpoint_id,
        "coordination_uuid": coordination.coordination_uuid,
        "coordination_name": coordination.coordination_name,
        "coordination_description": coordination.coordination_description,
        "agents": coordination.agents,
    }


def _get_task(coordination_uuid: str, task_uuid: str) -> Dict[str, Any]:
    """
    Get task as a dictionary for embedding purposes.

    This is used in contexts where we need task data embedded as a dict
    (e.g., task schedules) rather than using GraphQL nested resolvers.

    Args:
        coordination_uuid: The coordination UUID
        task_uuid: The task UUID

    Returns:
        Dict containing task data with embedded coordination
    """
    from .task import get_task

    task = get_task(coordination_uuid, task_uuid)
    return {
        "coordination": _get_coordination(
            task.endpoint_id,
            task.coordination_uuid,
        ),
        "task_uuid": task.task_uuid,
        "task_name": task.task_name,
        "task_description": task.task_description,
        "initial_task_query": task.initial_task_query,
        "subtask_queries": task.subtask_queries,
        "agent_actions": task.agent_actions,
    }
