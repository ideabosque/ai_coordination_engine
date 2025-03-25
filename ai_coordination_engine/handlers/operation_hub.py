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


def ask_operation_hub(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AskOperationHubType:
    try:
        info.context.get("logger")
        info.context.get("endpoint_id")
        setting = info.context.get("setting")

        # Get coordination.
        coordination = resolve_coordination(
            info,
            **{
                "endpoint_id": info.context.get("endpoint_id"),
                "coordination_uuid": kwargs["coordination_uuid"],
            },
        )

        variables = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "user_id": kwargs.get("user_id"),
            "updated_by": "operation_hub",
        }

        # Check the session.
        if "agent_uuid" in kwargs:
            variables.update({"status": "active"})
        else:
            if "session_uuid" in kwargs:
                variables.update(
                    {"session_uuid": kwargs["session_uuid"], "status": "in_transit"}
                )

        # Insert update session.
        session = insert_update_session(info, **variables)

        # Get the agent.
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

        # New logic to handle receiver_email
        connection_id = info.context.get("connectionId")
        if "receiver_email" in kwargs:
            # Attempt to find connection_id for the receiver's email
            receiver_connection = get_connection_by_email(
                info.context.get("logger"),
                info.context.get("endpoint_id"),
                email=kwargs["receiver_email"],
            )

            if receiver_connection:
                connection_id = receiver_connection.get("connection_id", connection_id)

        # Call ask model.
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
                "userQuery": kwargs.get("user_query"),
                "userId": kwargs.get("user_id"),
                "updatedBy": "operation_hub",
            },
        )

        # Insert update session thread.
        session_run = insert_update_session_run(
            info,
            **{
                "session_uuid": session.session_uuid,
                "run_uuid": ask_model["current_run_uuid"],
                "thread_uuid": ask_model["thread_uuid"],
                "agent_uuid": agent["agent_uuid"],
                "coordination_uuid": session.coordination_uuid,
                "async_task_uuid": ask_model["async_task_uuid"],
                "updated_by": "operation_hub",
            },
        )

        # Invoke async call to update session.
        # Add receiver_email to the variables.
        # Add this section

    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e
