#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import time
import traceback
from typing import Any, Dict, List

from graphene import ResolveInfo

from silvaengine_utility import Utility

from ...handlers.config import Config
from ...models.session import insert_update_session, resolve_session
from ...models.session_agent import resolve_session_agent_list
from ...types.session import SessionType
from ...types.session_agent import SessionAgentListType, SessionAgentType
from ..ai_coordination_utility import create_listener_info
from .action_rules import execute_action_rules
from .session_agent import execute_session_agent, update_session_agent


def invoke_next_iteration(
    info: ResolveInfo,
    coordination_uuid: str,
    session_uuid: str,
    iteration_count: int = 0,
) -> None:
    """Invoke the next iteration
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        task_uuid (str): UUID of the task
        session_uuid (str): UUID of the session
        setting (Dict): Dictionary containing settings
    Returns:
        None
    """
    insert_update_session(
        info,
        **{
            "coordination_uuid": coordination_uuid,
            "session_uuid": session_uuid,
            "iteration_count": iteration_count,
            "updated_by": "procedure_hub",
        },
    )

    Utility.invoke_funct_on_aws_lambda(
        info.context["logger"],
        info.context["endpoint_id"],
        "async_execute_procedure_task_session",
        params={"coordination_uuid": coordination_uuid, "session_uuid": session_uuid},
        setting=info.context["setting"],
        test_mode=info.context["setting"].get("test_mode"),
        aws_lambda=Config.aws_lambda,
    )


def _check_session_status(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType:
    """Check and update task session status if needed
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        task_uuid (str): UUID of the task
        session_uuid (str): UUID of the session
        task_session (Dict): Dictionary containing task session details
        setting (Dict): Dictionary containing settings
    Returns:
        Dict: Updated task session details or None if completed/failed
    """
    session = resolve_session(
        info,
        **{
            "coordination_uuid": kwargs["coordination_uuid"],
            "session_uuid": kwargs["session_uuid"],
        },
    )

    if session.status in ["completed", "failed"]:
        return None
    elif session.status == "initial":
        return insert_update_session(
            info,
            **{
                "coordination_uuid": session.task["coordination_uuid"],
                "session_uuid": session.session_uuid,
                "status": "in_progress",
                "updated_by": "procedure_hub",
            },
        )
    return session


def _handle_no_ready_agents(
    info: ResolveInfo,
    session: SessionType,
    session_agent_list: SessionAgentListType,
) -> None:
    """Handle case when there are no ready agents
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        task_session (Dict): Dictionary containing task session details
        session_agents (list): List of all session agents
        setting (Dict): Dictionary containing settings
    Returns:
        None
    """

    if any(agent.state == "failed" for agent in session_agent_list.session_agent_list):
        insert_update_session(
            info,
            **{
                "coordination_uuid": session.task["coordination_uuid"],
                "session_uuid": session.session_uuid,
                "logs": [
                    {
                        "agent_uuid": agent.agent_uuid,
                        "log": agent.notes,
                    }
                    for agent in [
                        agent
                        for agent in session_agent_list.session_agent_list
                        if agent.state == "failed"
                    ]
                ],
                "status": "failed",
                "updated_by": "procedure_hub",
            },
        )
    if any(
        agent.state == "wait_for_user_input"
        for agent in session_agent_list.session_agent_list
    ):
        info.context["logger"].info(
            "🔄 Pending due to the status of wait_for_user_input. Self-invoking for the next iteration."
        )
        return

    if any(
        agent.state in ["initial", "pending", "executing"]
        for agent in session_agent_list.session_agent_list
    ):
        _handle_pending_agents(info, session)

    insert_update_session(
        info,
        **{
            "coordination_uuid": session.task["coordination_uuid"],
            "session_uuid": session.session_uuid,
            "status": "completed",
            "updated_by": "procedure_hub",
        },
    )
    return


def _handle_pending_agents(info: ResolveInfo, session: SessionType) -> None:
    """Handle pending agents and iteration logic
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        task_session (Dict): Dictionary containing task session details
        setting (Dict): Dictionary containing settings
    Returns:
        None
    """
    info.context["logger"].info(
        "🔄 Pending session_agent exist. Self-invoking for the next iteration."
    )

    session.iteration_count += 1
    MAX_ITERATIONS = 5

    if session.iteration_count >= MAX_ITERATIONS:
        info.context["logger"].error(
            f"Maximum iterations ({MAX_ITERATIONS}) reached - possible infinite loop detected"
        )
        insert_update_session(
            info,
            **{
                "coordination_uuid": session.task["coordination_uuid"],
                "session_uuid": session.session_uuid,
                "status": "failed",
                "logs": [
                    {
                        "error": f"Maximum iterations ({MAX_ITERATIONS}) reached - possible infinite loop"
                    }
                ],
                "updated_by": "procedure_hub",
            },
        )
        return

    insert_update_session(
        info,
        **{
            "coordination_uuid": session.task["coordination_uuid"],
            "session_uuid": session.session_uuid,
            "iteration_count": session.iteration_count,
            "updated_by": "procedure_hub",
        },
    )

    time.sleep(10)
    invoke_next_iteration(
        info,
        session.task["coordination_uuid"],
        session.session_uuid,
        iteration_count=session.iteration_count,
    )
    return


def _execute_ready_agents(
    info: ResolveInfo, ready_session_agents: List[SessionAgentType]
) -> None:
    """Execute all ready session agents
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        ready_session_agents (list): List of agents ready for execution
        setting (Dict): Dictionary containing settings
    Returns:
        None
    """
    for session_agent in ready_session_agents:
        if session_agent.state == "pending":
            # TODO: Implement logic to handle pending state
            execute_action_rules(info, session_agent)
        else:
            # TODO: Execute execute_session_agent
            info.context["logger"].info(
                f"\n🚀 Executing session_agent: {session_agent.agent_uuid}"
            )
            execute_session_agent(info, session_agent)


def async_execute_procedure_task_session(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    """Execute a procedure task session
    Args:
        logger (logging.Logger): Logger instance
        **kwargs: Dictionary containing:
            - endpoint_id (str): ID of the endpoint
            - setting (Dict): Dictionary containing settings
            - task_uuid (str): UUID of the task
            - session_uuid (str): UUID of the session
    Returns:
        None
    """
    try:
        # Create listener info with session details
        info = create_listener_info(
            logger, "async_execute_procedure_task_session", setting, **kwargs
        )

        session = _check_session_status(info, **kwargs)
        if session is None:
            return

        session_agent_list = resolve_session_agent_list(
            info,
            **{
                "session_uuid": session.session_uuid,
            },
        )

        ready_session_agents = [
            agent
            for agent in session_agent_list.session_agent_list
            if agent.in_degree == 0 and agent.state in ["initial", "pending"]
        ]

        if not ready_session_agents:
            _handle_no_ready_agents(info, session, session_agent_list)
            return

        _execute_ready_agents(info, ready_session_agents)

        logger.info(
            "🔄 Pending session_agent exist. Self-invoking for the next iteration."
        )
        invoke_next_iteration(
            info,
            session.task["coordination_uuid"],
            session.session_uuid,
            iteration_count=session.iteration_count,
        )

    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e


def async_update_session_agent(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    try:
        # Create listener info with session details
        info = create_listener_info(
            logger, "async_update_session_agent", setting, **kwargs
        )
        update_session_agent(info, **kwargs)
    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e
