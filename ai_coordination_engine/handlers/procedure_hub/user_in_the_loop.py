#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import ResolveInfo

from ...models.session_agent import insert_update_session_agent, resolve_session_agent
from .procedure_hub_listener import invoke_next_iteration
from .session_agent import handle_session_agent_completion


def execute_for_user_input(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    """
    Process user input for a session agent and handle its execution flow.
    Updates session agent state and triggers next iteration if needed.
    """
    try:
        # Retrieve the session agent
        session_agent = resolve_session_agent(
            info,
            **{
                "session_uuid": kwargs["session_uuid"],
                "session_agent_uuid": kwargs["session_agent_uuid"],
            },
        )

        # Validate session agent exists
        if session_agent is None:
            raise Exception("Session agent not found")

        # Determine state based on action function presence
        session_agent.state = (
            "pending"
            if session_agent.agent_action.get("action_function")
            else "completed"
        )

        # Update with user input
        session_agent.user_input = kwargs["user_input"]

    except Exception as e:
        # Handle errors and log them
        log = traceback.format_exc()
        info.context["logger"].error(log)
        if "Session agent not found" in str(e):
            raise
        session_agent.state = "failed"
        session_agent.notes = log

    # Persist session agent updates
    session_agent = insert_update_session_agent(
        info,
        **{
            "session_uuid": session_agent.session["session_uuid"],
            "session_agent_uuid": session_agent.session_agent_uuid,
            "user_input": session_agent.user_input,
            "state": session_agent.state,
            "notes": session_agent.notes if session_agent.state == "failed" else None,
            "updated_by": "procedure_hub",
        },
    )

    # Handle completion if needed
    if session_agent.state == "completed":
        handle_session_agent_completion(info, session_agent)

    # Log and trigger next iteration
    info.context["logger"].info(
        "🔄 Pending session_agent exist. Self-invoking for the next iteration."
    )
    invoke_next_iteration(
        info,
        session_agent.session["coordination"]["coordination_uuid"],
        session_agent.session["session_uuid"],
    )

    return True
