#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import time
import traceback
from typing import Any, Dict, List, Tuple

from graphene import ResolveInfo
from silvaengine_utility.invoker import Invoker
from silvaengine_utility.serializer import Serializer

from ...models.session import insert_update_session
from ...models.session_agent import (
    insert_update_session_agent,
    resolve_session_agent,
    resolve_session_agent_list,
)
from ...models.session_run import insert_update_session_run, resolve_session_run_list
from ...types.session import SessionType
from ...types.session_agent import SessionAgentType
from ..ai_coordination_utility import (
    ensure_coordination_data,
    ensure_task_data,
    get_async_task,
    invoke_ask_model,
)
from ..config import Config


def init_session_agents(
    info: ResolveInfo, session: SessionType
) -> List[SessionAgentType]:
    """Initializes session agents for each agent in the agent list
    Args:
        info (ResolveInfo): GraphQL resolve info containing context
        session (SessionType): Session object containing task and coordination details
    Returns:
        list: List of dictionaries containing initialized session agent details including:
            - session_uuid
            - session_agent_uuid
            - agent_uuid
            - agent_action
    """
    session_agents = []
    subtask_queries = []

    # Get task data with nested coordination info
    task_data = ensure_task_data(session, info)

    # Ensure coordination exists in task_data
    if "coordination" not in task_data or not isinstance(
        task_data["coordination"], dict
    ):
        raise ValueError(
            f"Task data missing coordination info. Task UUID: {task_data.get('task_uuid')}. "
            f"Available keys: {list(task_data.keys())}"
        )

    for agent in task_data["coordination"]["agents"]:
        if agent["agent_type"] != "task":
            continue

        # Create or update session agent
        for subtask_query in list(
            filter(
                lambda x: x["agent_uuid"] == agent["agent_uuid"],
                session.subtask_queries,
            )
        ):
            session_agent = insert_update_session_agent(
                info,
                **{
                    "session_uuid": session.session_uuid,
                    "coordination_uuid": session.coordination_uuid,
                    "agent_uuid": agent["agent_uuid"],
                    "agent_action": task_data["agent_actions"].get(
                        agent["agent_uuid"], {}
                    ),
                    "updated_by": "procedure_hub",
                },
            )

            try:
                # Check if task_query is valid JSON and can be parsed
                variables = {
                    k: ",".join(v) if isinstance(v, list) else v
                    for k, v in Serializer.json_loads(session.task_query).items()
                }
                subtask_query.update(
                    {
                        "session_agent_uuid": session_agent.session_agent_uuid,
                        "subtask_query": subtask_query["subtask_query"].format(
                            **variables
                        ),
                    }
                )
            except:
                # If task_query is not valid JSON, just update session_agent_uuid
                subtask_query.update(
                    {
                        "session_agent_uuid": session_agent.session_agent_uuid,
                    }
                )

            subtask_queries.append(subtask_query)

            # Add session agent details to list
            session_agents.append(session_agent)

    session = insert_update_session(
        info,
        **{
            "coordination_uuid": session.coordination_uuid,
            "session_uuid": session.session_uuid,
            "subtask_queries": subtask_queries,
            "updated_by": "procedure_hub",
        },
    )

    return session_agents


def init_in_degree(
    info: ResolveInfo, session_agents: List[SessionAgentType]
) -> None | List[SessionAgentType]:
    """
    Initializes the in-degree for each session_agent in a task session.
    The in-degree represents the number of dependencies each session_agent has.
    """
    try:

        # Step 2: Build dependency graph (successor -> predecessors mapping)
        dependency_graph = {}

        for session_agent in session_agents:
            # Multiple successors to one predecessor.
            for predecessor in get_predecessors(info, session_agent):
                dependency_graph.setdefault(predecessor.agent_uuid, []).append(
                    session_agent.agent_uuid
                )

        # Step 3: Compute in-degree for each agent
        in_degree_map = {
            session_agent.agent_uuid: 0 for session_agent in session_agents
        }

        for predecessor, successors in dependency_graph.items():
            for successor in successors:
                if successor in in_degree_map:
                    in_degree_map[successor] += 1

        # Step 4: Batch update session agents with computed in-degree
        updated_agents = []
        for session_agent in session_agents:
            session_agent.in_degree = in_degree_map.get(session_agent.agent_uuid, 0)
            updated_agents.append(
                {
                    "session_uuid": session_agent.session_uuid,
                    "session_agent_uuid": session_agent.session_agent_uuid,
                    "in_degree": session_agent.in_degree,
                    "updated_by": "procedure_hub",
                }
            )

        # Batch update instead of multiple insert/update calls

        updated_session_agents = []
        for agent_update in updated_agents:
            updated_session_agent: SessionAgentType = insert_update_session_agent(
                info, **agent_update
            )

            # Add session agent details to list
            updated_session_agents.append(
                {
                    "session_agent_uuid": updated_session_agent.session_agent_uuid,
                    "agent_uuid": updated_session_agent.agent_uuid,
                    "agent_action": updated_session_agent.agent_action,
                    "in_degree": updated_session_agent.in_degree,
                }
            )

        info.context["logger"].info(
            f"In-degree initialized for {len(session_agents)} session agents."
        )

        return updated_session_agents

    except Exception as e:
        info.context["logger"].error(
            f"Error initializing in-degree: {traceback.format_exc()}"
        )
        raise e


def decrement_in_degree(info: ResolveInfo, session_agent: SessionAgentType) -> None:
    try:
        if session_agent.in_degree > 0:
            session_agent.in_degree -= 1
            insert_update_session_agent(
                info,
                **{
                    "session_uuid": session_agent.session_uuid,
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
            "session_uuid": session_agent.session_uuid,
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
            "session_uuid": session_agent.session_uuid,
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
                "coordination_uuid": session_agent.coordination_uuid,
                "session_uuid": session_agent.session_uuid,
                "status": "failed",
                "logs": Serializer.json_dumps([{"error": log}]),
                "updated_by": "procedure_hub",
            },
        )
        raise e


def update_session_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    """
    Updates the state and output of a session agent based on async task results.

    Args:
        info: GraphQL resolve info containing context
        kwargs: Must contain session_uuid, session_agent_uuid and async_task_uuid
    """
    try:
        # Retrieve the session agent
        session_agent = resolve_session_agent(
            info,
            session_uuid=kwargs["session_uuid"],
            session_agent_uuid=kwargs["session_agent_uuid"],
        )

        # Set initial state based on agent action rules
        session_agent.state = (
            "wait_for_user_input"
            if session_agent.agent_action.get("user_in_the_loop")
            else (
                "pending"
                if session_agent.agent_action.get("action_function")
                else "completed"
            )
        )

        if session_agent.agent_action.get("user_in_the_loop"):
            info.context["logger"].info("🚀 Executing user_in_the_loop session_agent.")

        # Poll async task with configurable timeout
        start_time = time.time()
        TIMEOUT = 60  # seconds
        POLL_INTERVAL = 1  # seconds

        while time.time() - start_time < TIMEOUT:
            async_task = get_async_task(
                info.context,
                **{
                    "functionName": "async_execute_ask_model",
                    "asyncTaskUuid": kwargs["async_task_uuid"],
                },
            )

            status = async_task["status"]
            if status == "completed":
                session_agent.agent_output = async_task["result"]
                break
            elif status == "failed":
                session_agent.state = "failed"
                session_agent.notes = async_task["notes"]
                break

            time.sleep(POLL_INTERVAL)  # Avoid tight polling loop
        else:
            # Handle timeout
            session_agent.state = "failed"
            session_agent.notes = f"Task timed out after {TIMEOUT} seconds"
    except Exception as e:
        # Handle exceptions by logging and marking agent as failed
        log = traceback.format_exc()
        info.context["logger"].error(log)
        session_agent.state = "failed"
        session_agent.notes = log

    # Update session agent in database
    session_agent = insert_update_session_agent(
        info,
        **{
            "session_uuid": session_agent.session_uuid,
            "session_agent_uuid": session_agent.session_agent_uuid,
            "agent_output": session_agent.agent_output,
            "state": session_agent.state,
            "notes": session_agent.notes if session_agent.state == "failed" else None,
            "updated_by": "procedure_hub",
        },
    )

    # Handle completion state and update successors
    handle_session_agent_completion(info, session_agent)


def prepare_task_query(
    info: ResolveInfo,
    session_agent: SessionAgentType,
    session: SessionType,
    predecessors: List[SessionAgentType],
) -> Tuple[str, List]:
    """Get agent input from either agent input or task session."""
    subtask_queries = getattr(session, "subtask_queries", [])
    subtask_query = next(
        (
            subtask_query["subtask_query"]
            for subtask_query in subtask_queries
            if subtask_query["session_agent_uuid"] == session_agent.session_agent_uuid
        ),
        "",
    )

    predecessors_outputs = []
    coordination_data = ensure_coordination_data(session, info)
    agents = coordination_data.get("agents") or []
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
            predecessors_outputs.append(
                f"agent_output({agent['agent_name']}): {predecessor.agent_output}"
            )
        if predecessor.user_input and predecessor.user_input != "":
            predecessors_outputs.append(f"user_input: {predecessor.user_input}")

    return subtask_query, predecessors_outputs


def get_thread_uuid(
    info: ResolveInfo,
    session_agent: SessionAgentType,
    predecessors: List[SessionAgentType],
) -> str | None:
    """Get thread UUID from predecessor agents."""
    if len(predecessors) == 0:
        return None
    if not session_agent.agent_action.get("primary_path"):
        return None

    session_run_list = resolve_session_run_list(
        info,
        **{
            "session_uuid": session_agent.session_uuid,
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
        # Resolve the session first to access its properties
        from ...models.session import resolve_session

        session = resolve_session(
            info,
            coordination_uuid=session_agent.coordination_uuid,
            session_uuid=session_agent.session_uuid,
        )

        # Initialize the session agent state to "executing"
        predecessors = get_predecessors(info, session_agent)
        subtask_query, predecessors_outputs = prepare_task_query(
            info, session_agent, session, predecessors
        )

        session_agent = insert_update_session_agent(
            info,
            **{
                "session_uuid": session_agent.session_uuid,
                "session_agent_uuid": session_agent.session_agent_uuid,
                "agent_input": subtask_query,
                "state": "executing",
                "updated_by": "procedure_hub",
            },
        )
        thread_uuid = get_thread_uuid(info, session_agent, predecessors)
        if thread_uuid:
            info.context["logger"].info(
                f"Found thread_uuid: {thread_uuid}"
            )  # Get user query from either agent input or task session

        successors = get_successors(info, session_agent)
        connection_id = (
            info.context.get("connectionId")
            if len(successors) == 0
            or session_agent.agent_action.get("user_in_the_loop")
            else None
        )
        variables = {
            "agentUuid": session_agent.agent_uuid,
            "threadUuid": thread_uuid,
            "userQuery": subtask_query + "\n\n" + "\n\n".join(predecessors_outputs),
            "userId": session.user_id
            or "system",  # Default to "system" if user_id is None
            "updatedBy": "operation_hub",
        }

        # Check if session has input files and add them to variables if present
        input_files = getattr(session, "input_files", None)
        if input_files is not None and len(input_files) > 0:
            variables.update({"input_files": input_files})

        ask_model = invoke_ask_model(
            info.context,
            **variables,
        )

        insert_update_session_run(
            info,
            **{
                "session_uuid": session_agent.session_uuid,
                "run_uuid": ask_model["current_run_uuid"],
                "thread_uuid": ask_model["thread_uuid"],
                "agent_uuid": session_agent.agent_uuid,
                "coordination_uuid": session_agent.coordination_uuid,
                "async_task_uuid": ask_model["async_task_uuid"],
                "session_agent_uuid": session_agent.session_agent_uuid,
                "updated_by": "operation_hub",
            },
        )

        # Prepare parameters for async session agent update
        params = {
            "session_uuid": session_agent.session_uuid,
            "session_agent_uuid": session_agent.session_agent_uuid,
            "async_task_uuid": ask_model["async_task_uuid"],
        }
        if "connectionId" in info.context:
            params.update({"connection_id": info.context["connectionId"]})

        # Invoke async update function on AWS Lambda
        Invoker.invoke_funct_on_aws_lambda(
            info.context,
            "async_update_session_agent",
            params=params,
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
                "coordination_uuid": session_agent.coordination_uuid,
                "session_uuid": session_agent.session_uuid,
                "status": "failed",
                "logs": Serializer.json_dumps([{"error": log}]),
                "updated_by": "procedure_hub",
            },
        )
        raise e
