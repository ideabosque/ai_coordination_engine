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
from ..config import Config
from .session_agent import init_in_degree, init_session_agents


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
    if task.subtask_queries:
        variables["subtask_queries"] = task.subtask_queries
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
    if not session.subtask_queries:
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
    else:
        # Initialize session agents for all active agents
        session_agents = init_session_agents(info, session)

        # Initialize in-degree values for session agents
        updated_session_agents = init_in_degree(info, session_agents)
        info.context["logger"].info(
            f"Updated session agents: {Utility.json_dumps(updated_session_agents)}"
        )

    # Invoke async update function on AWS Lambda
    Utility.invoke_funct_on_aws_lambda(
        info.context["logger"],
        info.context["endpoint_id"],
        "async_execute_procedure_task_session",
        params={
            "coordination_uuid": session.coordination["coordination_uuid"],
            "session_uuid": session.session_uuid,
        },
        setting=info.context["setting"],
        test_mode=info.context["setting"].get("test_mode"),
        aws_lambda=Config.aws_lambda,
    )

    return ProcedureTaskSessionType(
        **{
            "coordination_uuid": session.coordination["coordination_uuid"],
            "session_uuid": session.session_uuid,
            "task_uuid": session.task["task_uuid"],
            "user_id": session.user_id,
            "task_query": session.task_query,
        }
    )
