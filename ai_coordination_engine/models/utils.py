# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List


def _initialize_tables(logger: logging.Logger) -> None:
    from .coordination import create_coordination_table
    from .session import create_session_table
    from .session_agent import create_session_agent_table
    from .session_thread import create_session_thread_table
    from .task import create_task_table
    from .task_schedule import create_task_schedule_table

    create_coordination_table(logger)
    create_session_table(logger)
    create_session_agent_table(logger)
    create_session_thread_table(logger)
    create_task_table(logger)
    create_task_schedule_table(logger)


def _get_coordination(endpoint_id: str, coordination_uuid: str) -> Dict[str, Any]:
    from .coordination import get_coordination

    coordination = get_coordination(endpoint_id, coordination_uuid)
    return {
        "endpoint_id": coordination.endpoint_id,
        "coordination_uuid": coordination.coordination_uuid,
        "coordination_name": coordination.coordination_name,
        "coordination_description": coordination.coordination_description,
    }


def _get_session(coordination_uuid: str, session_uuid: str) -> Dict[str, Any]:
    from .session import get_session

    session = get_session(coordination_uuid, session_uuid)
    return {
        "coordination": _get_coordination(
            session.endpoint_id,
            session.coordination_uuid,
        ),
        "session_uuid": session.session_uuid,
        "task": (
            {}
            if session.task_uuid is None
            else _get_task(
                session.coordination_uuid,
                session.task_uuid,
            )
        ),
        "user_id": session.user_id,
        "endpoint_id": session.endpoint_id,
        "task_query": session.task_query,
        "iteration_count": session.iteration_count,
        "status": session.status,
        "notes": session.notes,
    }


def _get_task(coordination_uuid: str, task_uuid: str) -> Dict[str, Any]:
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
        "agent_actions": task.agent_actions,
    }
