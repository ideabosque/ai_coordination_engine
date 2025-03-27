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
    Main function to handle operation hub requests and coordinate with agents.

    Args:
        info (ResolveInfo): GraphQL resolve info containing context
        **kwargs: Variable keyword arguments including:
            - coordination_uuid: UUID of the coordination
            - user_id: ID of the user (optional)
            - agent_uuid: UUID of the agent (optional)
            - session_uuid: UUID of the session (optional)
            - user_query: Query from the user
            - receiver_email: Email of receiver (optional)
            - thread_uuid: UUID of conversation thread (optional)

    Returns:
        AskOperationHubType: Response containing session and run details
    """
    try:
        # Get coordination details for the given coordination UUID
        coordination = resolve_coordination(
            info,
            **{
                "endpoint_id": info.context.get("endpoint_id"),
                "coordination_uuid": kwargs["coordination_uuid"],
            },
        )

        # Prepare variables for session creation/update
        variables = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "user_id": kwargs.get("user_id"),
            "updated_by": "operation_hub",
        }

        # Set session status based on presence of agent_uuid or session_uuid
        if "agent_uuid" in kwargs:
            variables.update({"status": "active"})
        else:
            if "session_uuid" in kwargs:
                variables.update(
                    {"session_uuid": kwargs["session_uuid"], "status": "in_transit"}
                )

        # Create or update session with the prepared variables
        session = insert_update_session(info, **variables)

        # Validate and get appropriate agent - either specified agent or triage agent
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

        # Process user query - enhance it for triage agents
        user_query = kwargs["user_query"]
        if agent["agent_type"] == "triage":
            # Extract task agents with relevant properties for triage
            available_task_agents = [
                {
                    "agent_uuid": agent["agent_uuid"],
                    "agent_name": agent["agent_name"],
                    "agent_description": agent["agent_description"],
                }
                for agent in coordination.agents
                if agent["agent_type"] == "task"
            ]

            # Construct enhanced triage request with available agents
            user_query = (
                f"Based on the following user query, please analyze and select the most appropriate agent:\n"
                f"User Query: {user_query}\n"
                f"Available Agents: {Utility.json_dumps(available_task_agents)}\n"
                f"Please assess the intent behind the query and align it with the agent's most appropriate capabilities, then export the results in JSON format."
            )
            info.context.get("logger").info(f"Enhanced triage request: {user_query}")

        # Handle receiver email and connection ID logic
        connection_id = info.context.get("connectionId")
        if "receiver_email" in kwargs and agent["agent_type"] != "triage":
            # Look up connection_id for receiver's email
            receiver_connection = get_connection_by_email(
                info.context.get("logger"),
                info.context.get("endpoint_id"),
                email=kwargs["receiver_email"],
            )

            if receiver_connection:
                connection_id = receiver_connection.get("connection_id", connection_id)

        # Invoke AI model with prepared parameters
        ask_model = invoke_ask_model(
            info.context.get("logger"),
            info.context.get("endpoint_id"),
            setting=info.context.get("setting"),
            connection_id=connection_id,
            **{
                "agentUuid": agent["agent_uuid"],
                "threadUuid": kwargs.get(
                    "thread_uuid"
                ),  # Optional, it can be passed for the continue conversation.
                "userQuery": user_query,
                "userId": kwargs.get("user_id"),
                "updatedBy": "operation_hub",
            },
        )

        # Create or update session run with model response
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

        # Prepare parameters for asynchronous session update
        params = {
            "coordination_uuid": session_run.session["coordination"][
                "coordination_uuid"
            ],
            "session_uuid": session_run.session["session_uuid"],
            "run_uuid": session_run.run_uuid,
        }
        if connection_id:
            params["connection_id"] = connection_id

        # Add receiver email if needed
        if (
            connection_id is None
            and "receiver_email" in kwargs
            and agent["agent_type"] != "triage"
        ):
            params["receiver_email"] = kwargs["receiver_email"]

        # Trigger asynchronous session update via Lambda
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

        # Return response with session and run details
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
