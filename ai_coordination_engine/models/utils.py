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


def _get_coordination(partition_key: str, coordination_uuid: str) -> Dict[str, Any]:
    """
    Get coordination as a dictionary for embedding purposes.

    This is used in validation contexts where we need coordination data
    but don't need the full GraphQL type with nested resolvers.

    Args:
        partition_key: The partition key
        coordination_uuid: The coordination UUID

    Returns:
        Dict containing coordination data
    """
    from .coordination import get_coordination

    coordination = get_coordination(partition_key, coordination_uuid)
    return {
        "partition_key": coordination.partition_key,
        "endpoint_id": coordination.endpoint_id,
        "coordination_uuid": coordination.coordination_uuid,
        "coordination_name": coordination.coordination_name,
        "coordination_description": coordination.coordination_description,
        "agents": coordination.agents,
    }
