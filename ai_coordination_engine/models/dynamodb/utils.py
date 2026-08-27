# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict


def initialize_tables(logger: logging.Logger) -> None:
    """Initialize all DynamoDB tables for the AI Coordination Engine."""
    from typing import List

    from .coordination import CoordinationModel
    from .session import SessionModel
    from .session_agent import SessionAgentModel
    from .session_run import SessionRunModel
    from .task import TaskModel
    from .task_schedule import TaskScheduleModel

    models: List = [
        CoordinationModel,
        SessionModel,
        SessionAgentModel,
        SessionRunModel,
        TaskModel,
        TaskScheduleModel,
    ]

    for model in models:
        if model.exists():
            continue

        table_name = model.Meta.table_name
        # Create with on-demand billing (PAY_PER_REQUEST)
        model.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info(f"The {table_name} table has been created.")


def get_coordination(partition_key: str, coordination_uuid: str) -> Dict[str, Any]:
    """
    Get coordination as a dictionary for embedding purposes.

    This is used in validation contexts where we need coordination data
    but don't need the full GraphQL type with nested resolvers.
    Routes through the repository dispatch boundary for backend agnosticism.

    Args:
        partition_key: The partition key
        coordination_uuid: The coordination UUID

    Returns:
        Dict containing coordination data
    """
    from ..repositories import get_repo

    return get_repo("coordination").get(
        partition_key=partition_key,
        coordination_uuid=coordination_uuid,
    )
