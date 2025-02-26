# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List


def _get_coordination(endpoint_id: str, coordination_uuid: str) -> Dict[str, Any]:
    from .coordination import get_coordination

    coordination = get_coordination(endpoint_id, coordination_uuid)
    return {
        "endpoint_id": coordination.endpoint_id,
        "coordination_uuid": coordination.coordination_uuid,
        "coordination_name": coordination.coordination_name,
        "coordination_description": coordination.coordination_description,
        "assistant_id": coordination.assistant_id,
        "additional_instructions": coordination.additional_instructions,
    }


def _get_agent(coordination_uuid: str, agent_name: str) -> Dict[str, Any]:
    from .agent import _get_active_agent

    agent = _get_active_agent(coordination_uuid, agent_name)
    return {
        "coordination_uuid": agent.coordination_uuid,
        "agent_name": agent.agent_name,
        "agent_instructions": agent.agent_instructions,
        "response_format": agent.response_format,
        "json_schema": agent.json_schema,
        "tools": agent.tools,
        "predecessor": agent.predecessor,
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
        "status": session.status,
        "notes": session.notes,
    }


def _get_thread_ids(session_uuid: str) -> List[str]:
    from .thread import ThreadModel

    results = ThreadModel.query(session_uuid, None)
    thread_ids = [result.thread_id for result in results]

    return thread_ids


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


def _get_task_session(task_uuid: str, session_uuid: str) -> Dict[str, Any]:
    from .task_session import get_task_session

    task_session = get_task_session(task_uuid, session_uuid)
    return {
        "task": _get_task(
            task_session.coordination_uuid,
            task_session.task_uuid,
        ),
        "session_uuid": task_session.session_uuid,
        "task_query": task_session.task_query,
        "status": task_session.status,
        "notes": task_session.notes,
    }
