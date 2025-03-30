#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import time
import traceback
from typing import Any, Dict, List

from graphene import ResolveInfo

from silvaengine_utility import Utility

from ...models.session import insert_update_session
from ...models.session_agent import (
    insert_update_session_agent,
    resolve_session_agent,
    resolve_session_agent_list,
)
from ...models.session_run import insert_update_session_run, resolve_session_run_list
from ...types.session_agent import SessionAgentType
from ..ai_coordination_utility import get_async_task, invoke_ask_model
from ..config import Config


def decrement_in_degree(info: ResolveInfo, session_agent: SessionAgentType) -> None:
    try:
        if session_agent.in_degree > 0:
            session_agent.in_degree -= 1
            insert_update_session_agent(
                info,
                **{
                    "session_uuid": session_agent.session["session_uuid"],
                    "session_agent_uuid": session_agent.session_agent_uuid,
                    "in_degree": int(session_agent.in_degree),
                    "updated_by": "procedure_hub",
                },
            )
    except Exception as e:
        log = traceback.format_exc()
        info.context["logger"].error(log)
        raise e


def get_successors(
    info: ResolveInfo, session_agent: SessionAgentType
) -> List[SessionAgentType]:
    session_agent_list = resolve_session_agent_list(
        info,
        **{
            "session_uuid": session_agent.session["session_uuid"],
            "predecessor": session_agent.agent_uuid,
        },
    )
    if session_agent_list.total == 0:
        return []
    return session_agent_list.session_agent_list


def get_predecessors(
    info: ResolveInfo, session_agent: SessionAgentType
) -> List[SessionAgentType]:
    predecessors = session_agent.agent_action.get("predecessors", [])
    if len(predecessors) == 0:
        return predecessors
    session_agent_list = resolve_session_agent_list(
        info,
        **{
            "session_uuid": session_agent.session["session_uuid"],
            "predecessors": predecessors,
        },
    )
    if session_agent_list.total == 0:
        return []
    return session_agent_list.session_agent_list


def handle_session_agent_completion(
    info: ResolveInfo,
    session_agent: SessionAgentType,
) -> None:
    try:
        successors = get_successors(info, session_agent)
        if session_agent.state == "completed":
            for successor in successors:
                decrement_in_degree(info, successor)
        return
    except Exception as e:
        log = traceback.format_exc()
        info.context["logger"].error(log)
        insert_update_session(
            info,
            **{
                "coordination_uuid": session_agent.session["coordination"][
                    "coordination_uuid"
                ],
                "session_uuid": session_agent.session["session_uuid"],
                "status": "failed",
                "logs": Utility.json_dumps([{"error": log}]),
                "updated_by": "procedure_hub",
            },
        )
        raise e


def update_session_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    try:
        session_agent = resolve_session_agent(
            info,
            **{
                "session_uuid": kwargs["session_uuid"],
                "session_agent_uuid": kwargs["session_agent_uuid"],
            },
        )
        session_agent.state = "completed"
        if session_agent.agent_action.get("action_rules"):
            session_agent.state = "pending"

        if session_agent.agent_action.get("user_in_the_loop"):
            info.context["logger"].info("🚀 Executing user_in_the_loop session_agent.")
            session_agent.state = "wait_for_user_input"

        start_time = time.time()
        while True:
            async_task = get_async_task(
                info.context.get("logger"),
                info.context.get("endpoint_id"),
                info.context.get("setting"),
                **{
                    "functionName": "async_execute_ask_model",
                    "asyncTaskUuid": kwargs["async_task_uuid"],
                },
            )
            if async_task["status"] == "completed":
                session_agent.agent_output = async_task["result"]
                break
            if async_task["status"] == "failed":
                session_agent.state = async_task["status"]
                session_agent.notes = async_task["notes"]
                break
            if time.time() - start_time > 60:
                session_agent.state = "failed"
                session_agent.notes = "Task timed out after 60 seconds"
                break

    except Exception as e:
        log = traceback.format_exc()
        info.context["logger"].error(log)
        session_agent.state = "failed"
        session_agent.notes = log

    session_agent = insert_update_session_agent(
        info,
        **{
            "session_uuid": session_agent.session["session_uuid"],
            "session_agent_uuid": session_agent.session_agent_uuid,
            "agent_output": session_agent.agent_output,
            "state": session_agent.state,
            "notes": session_agent.notes if session_agent.state == "failed" else None,
            "updated_by": "procedure_hub",
        },
    )

    handle_session_agent_completion(info, session_agent)

    return


def get_agent_input(user_input: str, predecessors: List[SessionAgentType]) -> str:
    """Get agent input from either agent input or task session."""
    if len(predecessors) == 0:
        return None

    agents = predecessors[0].session["coordination"]["agents"]
    agent_inputs = []
    if user_input and user_input != "":
        agent_inputs.append(f"user_input: {user_input}")
    for predecessor in predecessors:
        agent = next(
            (
                agent
                for agent in agents
                if agent["agent_uuid"] == predecessor.agent_uuid
            ),
            None,
        )
        if not agent:
            continue

        if predecessor.agent_output and predecessor.agent_output != "":
            agent_inputs.append(
                f"agent_output({agent["agent_name"]}): {predecessor.agent_output}"
            )

    agent_input = "\n".join(agent_inputs)
    return agent_input


def get_thread_uuid(
    info: ResolveInfo,
    session_agent: SessionAgentType,
    predecessors: List[SessionAgentType],
) -> str:
    """Get thread UUID from predecessor agents."""
    if len(predecessors) == 0:
        return None
    if not session_agent.agent_action.get("primary_path"):
        return None

    session_run_list = resolve_session_run_list(
        info,
        **{
            "session_uuid": session_agent.session["session_uuid"],
            "session_agent_uuid": predecessors[0].session_agent_uuid,
        },
    )
    if session_run_list.total == 0:
        return None
    return session_run_list.session_run_list[0].thread_uuid


def execute_session_agent(info: ResolveInfo, session_agent: SessionAgentType) -> None:
    """Main function to execute the session agent workflow.

    This function orchestrates the entire session agent execution process.
    It handles initialization, coordination, thread management, and OpenAI API interaction.
    """
    try:
        # Initialize the session agent state to "executing"
        predecessors = get_predecessors(info, session_agent)
        agent_input = get_agent_input(session_agent.user_input, predecessors)

        agent_input = agent_input or session_agent.session["task_query"]
        info.context["logger"].info(f"User query: {agent_input}")

        session_agent = insert_update_session_agent(
            info,
            **{
                "session_uuid": session_agent.session["session_uuid"],
                "session_agent_uuid": session_agent.session_agent_uuid,
                "agent_input": agent_input,
                "state": "executing",
                "updated_by": "procedure_hub",
            },
        )
        thread_uuid = get_thread_uuid(info, session_agent, predecessors)
        if thread_uuid:
            info.context["logger"].info(
                f"Found thread_uuid: {thread_uuid}"
            )  # Get user query from either agent input or task session

        ask_model = invoke_ask_model(
            info.context.get("logger"),
            info.context.get("endpoint_id"),
            setting=info.context.get("setting"),
            connection_id=info.context.get("connectionId"),
            **{
                "agentUuid": session_agent.agent_uuid,
                "threadUuid": thread_uuid,
                "userQuery": agent_input,
                "userId": session_agent.session.get("user_id"),
                "updatedBy": "operation_hub",
            },
        )

        insert_update_session_run(
            info,
            **{
                "session_uuid": session_agent.session["session_uuid"],
                "run_uuid": ask_model["current_run_uuid"],
                "thread_uuid": ask_model["thread_uuid"],
                "agent_uuid": session_agent.agent_uuid,
                "coordination_uuid": session_agent.session["coordination"][
                    "coordination_uuid"
                ],
                "async_task_uuid": ask_model["async_task_uuid"],
                "session_agent_uuid": session_agent.session_agent_uuid,
                "updated_by": "operation_hub",
            },
        )

        # Prepare parameters for async session agent update
        params = {
            "session_uuid": session_agent.session["session_uuid"],
            "session_agent_uuid": session_agent.session_agent_uuid,
            "async_task_uuid": ask_model["async_task_uuid"],
        }

        # Invoke async update function on AWS Lambda
        Utility.invoke_funct_on_aws_lambda(
            info.context["logger"],
            info.context["endpoint_id"],
            "async_update_session_agent",
            params=params,
            setting=info.context["setting"],
            test_mode=info.context["setting"].get("test_mode"),
            aws_lambda=Config.aws_lambda,
        )
        return

    except Exception as e:
        # Handle any exceptions by logging error and updating task session status
        log = traceback.format_exc()
        info.context["logger"].error(log)
        insert_update_session(
            info,
            **{
                "coordination_uuid": session_agent.session["coordination"][
                    "coordination_uuid"
                ],
                "session_uuid": session_agent.session["session_uuid"],
                "status": "failed",
                "logs": Utility.json_dumps([{"error": log}]),
                "updated_by": "procedure_hub",
            },
        )
        raise e
