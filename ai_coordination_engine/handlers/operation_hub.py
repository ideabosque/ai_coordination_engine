#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import time
import traceback
from typing import Any, Dict, List, Optional

from graphene import ResolveInfo

from silvaengine_utility import Utility

from ..models.coordination import resolve_coordination
from ..models.session import insert_update_session
from ..models.session_run import insert_update_session_run
from ..types.operation_hub import AskOperationHubType
from .ai_coordination_utility import get_connection_by_email, invoke_ask_model
from .config import Config


def ask_operation_hub(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AskOperationHubType:
    """
    Orchestrates operation hub requests and agent coordination by managing sessions,
    processing queries, and handling asynchronous updates.

    The function performs the following key operations:
    1. Resolves coordination details and creates/updates sessions
    2. Selects appropriate agent (task or triage) based on request
    3. Processes and enhances user queries for triage scenarios
    4. Manages connection IDs and receiver email routing
    5. Invokes AI model and creates session runs
    6. Triggers asynchronous session updates via Lambda

    Args:
        info (ResolveInfo): GraphQL context and metadata
        **kwargs: Request parameters including:
            - coordination_uuid: Unique identifier for coordination
            - user_id: Optional user identifier
            - agent_uuid: Optional agent identifier
            - session_uuid: Optional session identifier
            - user_query: User's input query
            - receiver_email: Optional email for routing
            - thread_uuid: Optional thread ID for conversation continuity

    Returns:
        AskOperationHubType: Structured response with session details and run metadata
    """
    try:
        # Fetch coordination configuration and validate existence
        coordination = resolve_coordination(
            info,
            **{
                "endpoint_id": info.context.get("endpoint_id"),
                "coordination_uuid": kwargs["coordination_uuid"],
            },
        )

        # Initialize session parameters with core identifiers
        variables = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "user_id": kwargs.get("user_id"),
            "updated_by": "operation_hub",
        }

        # Determine session state based on request context
        if "agent_uuid" in kwargs:
            variables.update({"status": "active"})
        else:
            if "session_uuid" in kwargs:
                variables.update(
                    {"session_uuid": kwargs["session_uuid"], "status": "in_transit"}
                )

        # Persist session state
        session = insert_update_session(info, **variables)

        # Validate agent availability and select appropriate agent
        assert len(coordination.agents) > 0, "No agent found for the coordination."
        agent = next(
            (
                agent
                for agent in coordination.agents
                if agent["agent_uuid"] == kwargs.get("agent_uuid")
            ),
            next(
                (
                    agent
                    for agent in coordination.agents
                    if agent["agent_type"] == "triage"
                ),
                None,
            ),
        )

        # Process and enhance query based on agent type
        user_query = kwargs["user_query"]
        if agent["agent_type"] == "triage":
            # Extract relevant agent metadata for triage decision
            available_task_agents = [
                {
                    "agent_uuid": agent["agent_uuid"],
                    "agent_name": agent["agent_name"],
                    "agent_description": agent["agent_description"],
                }
                for agent in coordination.agents
                if agent["agent_type"] == "task"
            ]

            # Construct comprehensive triage prompt
            user_query = (
                f"Based on the following user query, please analyze and select the most appropriate agent:\n"
                f"User Query: {user_query}\n"
                f"Available Agents: {Utility.json_dumps(available_task_agents)}\n"
                f"Please assess the intent behind the query and align it with the agent's most appropriate capabilities, then export the results in JSON format."
            )
            info.context.get("logger").info(f"Enhanced triage request: {user_query}")

        # Resolve connection routing for non-triage scenarios
        connection_id = info.context.get("connectionId")
        if "receiver_email" in kwargs and agent["agent_type"] != "triage":
            receiver_connection = get_connection_by_email(
                info.context.get("logger"),
                info.context.get("endpoint_id"),
                email=kwargs["receiver_email"],
            )

            if receiver_connection:
                connection_id = receiver_connection.get("connection_id", connection_id)

        # Execute AI model interaction
        ask_model = invoke_ask_model(
            info.context.get("logger"),
            info.context.get("endpoint_id"),
            setting=info.context.get("setting"),
            connection_id=connection_id,
            **{
                "agentUuid": agent["agent_uuid"],
                "threadUuid": kwargs.get("thread_uuid"),
                "userQuery": user_query,
                "userId": kwargs.get("user_id"),
                "updatedBy": "operation_hub",
            },
        )

        # Record session run details
        session_run = insert_update_session_run(
            info,
            **{
                "session_uuid": session.session_uuid,
                "run_uuid": ask_model["current_run_uuid"],
                "thread_uuid": ask_model["thread_uuid"],
                "agent_uuid": agent["agent_uuid"],
                "coordination_uuid": session.coordination["coordination_uuid"],
                "async_task_uuid": ask_model["async_task_uuid"],
                "updated_by": "operation_hub",
            },
        )

        # Configure async update parameters
        params = {
            "coordination_uuid": session_run.session["coordination"][
                "coordination_uuid"
            ],
            "session_uuid": session_run.session["session_uuid"],
            "run_uuid": session_run.run_uuid,
        }
        if connection_id:
            params["connection_id"] = connection_id

        # Handle email routing for async updates
        if (
            connection_id is None
            and "receiver_email" in kwargs
            and agent["agent_type"] != "triage"
        ):
            params["receiver_email"] = kwargs["receiver_email"]

        # Initiate async session update
        Utility.invoke_funct_on_aws_lambda(
            info.context["logger"],
            info.context["endpoint_id"],
            "async_insert_update_session",
            params=params,
            setting=info.context["setting"],
            test_mode=info.context["setting"].get("test_mode"),
            aws_lambda=Config.aws_lambda,
            invocation_type="Event",
        )

        # Construct and return comprehensive response
        return AskOperationHubType(
            **{
                "session": {
                    "coordination_uuid": session.coordination["coordination_uuid"],
                    "session_uuid": session.session_uuid,
                    "user_id": session.user_id,
                    "endpoint_id": session.coordination["endpoint_id"],
                    "status": session.status,
                },
                "run_uuid": session_run.run_uuid,
                "thread_uuid": session_run.thread_uuid,
                "agent_uuid": session_run.agent_uuid,
                "async_task_uuid": session_run.async_task_uuid,
                "updated_at": session_run.updated_at,
            }
        )

    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e
