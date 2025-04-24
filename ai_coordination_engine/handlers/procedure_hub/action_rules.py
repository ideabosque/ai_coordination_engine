#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import ResolveInfo

from ...models.session_agent import insert_update_session_agent, resolve_session_agent
from ..ai_coordination_utility import get_action_rules_function
from .session_agent import get_successors, handle_session_agent_completion


def execute_action_rules(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    try:
        session_agent = resolve_session_agent(
            info,
            **{
                "session_uuid": kwargs["session_uuid"],
                "session_agent_uuid": kwargs["session_agent_uuid"],
            },
        )
        session_agent.state = "completed"

        # TODO: Process action_rules.
        action_rules_function = get_action_rules_function(
            info,
            session_agent.agent_action["action_rules"]["module_name"],
            session_agent.agent_action["action_rules"]["function_name"],
        )
        session_agent, successors = action_rules_function(
            info, session_agent, get_successors(info, session_agent)
        )

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

    if session_agent.state == "completed":
        handle_session_agent_completion(info, session_agent)

    return
