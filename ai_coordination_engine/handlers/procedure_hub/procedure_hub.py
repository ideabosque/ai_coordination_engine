#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict, List

from graphene import ResolveInfo

from silvaengine_utility import Utility

from ...models.session import insert_update_session
from ...models.session_agent import insert_update_session_agent
from ...models.task import resolve_task
from ...types.procedure_hub import ProcedureTaskSessionType
from ...types.session import SessionType
from ...types.task import TaskType
from ..config import Config


def _init_session_agents(
    info: ResolveInfo,
    task: TaskType,
    session: SessionType,
) -> list:
    """Initializes session agents for each agent in the agent list
    Args:
        info (ResolveInfo): GraphQL resolve info containing context
        agent_list (Dict): Dictionary containing list of agents to initialize
        task (Dict): Dictionary containing task details
        coordination_session (Dict): Dictionary containing coordination session details
        task_session (Dict): Dictionary containing task session details
    Returns:
        list: List of dictionaries containing initialized session agent details including:
            - session_agent_uuid
            - agent_name
            - agent_action
            - in_degree
            - state
            - notes
    """
    session_agents = []
    for agent in task.coordination["agents"]:
        # Create or update session agent
        session_agent = insert_update_session_agent(
            info,
            **{
                "session_uuid": session.session_uuid,
                "coordination_uuid": task.coordination["coordination_uuid"],
                "agent_uuid": agent["agent_uuid"],
                "agent_action": task.agent_actions.get(agent["agent_uuid"], {}),
                "updated_by": "procedure_hub",
            },
        )

        # Add session agent details to list
        session_agents.append(
            {
                "session_uuid": session_agent.session["session_uuid"],
                "session_agent_uuid": session_agent.session_agent_uuid,
                "agent_uuid": session_agent.agent_uuid,
                "agent_action": session_agent.agent_action,
            }
        )
    return session_agents


def _init_in_degree(info: ResolveInfo, session_agents: List[Dict[str, Any]]) -> None:
    """
    Initializes the in-degree for each session_agent in a task session.
    The in-degree represents the number of dependencies each session_agent has.
    """
    try:

        # Step 2: Build dependency graph (successor -> predecessors mapping)
        dependency_graph = {}

        for session_agent in session_agents:
            # Multiple successors to one predecessor.
            predecessors = session_agent.get("agent_action", {}).get("predecessors", [])
            for predecessor in predecessors:
                dependency_graph.setdefault(predecessor, []).append(
                    session_agent["agent_uuid"]
                )

        # Step 3: Compute in-degree for each agent
        in_degree_map = {
            session_agent["agent_uuid"]: 0 for session_agent in session_agents
        }

        for predecessor, successors in dependency_graph.items():
            for successor in successors:
                if successor in in_degree_map:
                    in_degree_map[successor] += 1

        # Step 4: Batch update session agents with computed in-degree
        updated_agents = []
        for session_agent in session_agents:
            session_agent["in_degree"] = in_degree_map.get(
                session_agent["agent_uuid"], 0
            )
            updated_agents.append(
                {
                    "session_uuid": session_agent["session_uuid"],
                    "session_agent_uuid": session_agent["session_agent_uuid"],
                    "in_degree": session_agent["in_degree"],
                    "updated_by": "procedure_hub",
                }
            )

        # Batch update instead of multiple insert/update calls

        updated_session_agents = []
        for agent_update in updated_agents:
            updated_session_agent = insert_update_session_agent(info, **agent_update)

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


def execute_procedure_task_session(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> ProcedureTaskSessionType:
    """Creates a new procedure task session instance
    Args:
        info (ResolveInfo): GraphQL resolve info containing context
        **kwargs: Dictionary containing:
            - coordination_uuid (str): UUID of the coordination
            - task_uuid (str): UUID of the task
            - task_query (str, optional): Query for the task
    Returns:
        ProcedureTaskSessionType: Object containing:
            - task: Task details
            - session: Session details
            - task_query: Query for the task
            - status: Session status
            - notes: Session notes
            - session_agents: List of session agents
    """
    procedure_task_session = ProcedureTaskSessionType()

    # Fetch task details and extract relevant information
    task = resolve_task(
        info,
        **{
            "coordination_uuid": kwargs["coordination_uuid"],
            "task_uuid": kwargs["task_uuid"],
        },
    )

    # Initialize the session
    variables = {
        "coordination_uuid": kwargs["coordination_uuid"],
        "task_uuid": kwargs["task_uuid"],
        "task_query": kwargs.get("task_query", task.initial_task_query),
        "updated_by": "procedure_hub",
    }
    if kwargs.get("user_id"):
        variables["user_id"] = kwargs["user_id"]
    session = insert_update_session(
        info,
        **variables,
    )

    # * Process the task query and generate subtasks for each agent based on their capabilities and dependencies.
    # This involves:
    # 1. Analyzing and decomposing the task query into atomic subtasks
    # 2. Evaluating agent capabilities and matching them with appropriate subtasks
    # 3. Generating agent-specific task queries with necessary context and parameters
    # 4. Validating subtask dependencies align with agent_action predecessor relationships
    # 5. Optimizing subtask distribution for parallel execution where possible
    # 6. Storing subtask assignments and metadata in the session for tracking    # This involves:

    # Invoke async update function on AWS Lambda
    Utility.invoke_funct_on_aws_lambda(
        info.context["logger"],
        info.context["endpoint_id"],
        "async_decompose_task_query",
        params={
            "coordination_uuid": session.coordination["coordination_uuid"],
            "session_uuid": session.session_uuid,
        },
        setting=info.context["setting"],
        test_mode=info.context["setting"].get("test_mode"),
        aws_lambda=Config.aws_lambda,
    )

    procedure_task_session.session = {
        "coordination_uuid": session.coordination["coordination_uuid"],
        "session_uuid": session.session_uuid,
        "task_uuid": session.task["task_uuid"],
        "user_id": session.user_id,
        "task_query": session.task_query,
    }

    # Initialize session agents for all active agents
    session_agents = _init_session_agents(info, task, session)

    # Initialize in-degree values for session agents
    updated_session_agents = _init_in_degree(info, session_agents)

    procedure_task_session.session_agents = updated_session_agents

    #! Disable the section for testing.
    # Invoke async update function on AWS Lambda
    # Utility.invoke_funct_on_aws_lambda(
    #     info.context["logger"],
    #     info.context["endpoint_id"],
    #     "async_execute_procedure_task_session",
    #     params={
    #         "coordination_uuid": session.coordination["coordination_uuid"],
    #         "session_uuid": session.session_uuid,
    #     },
    #     setting=info.context["setting"],
    #     test_mode=info.context["setting"].get("test_mode"),
    #     aws_lambda=Config.aws_lambda,
    # )

    return procedure_task_session
