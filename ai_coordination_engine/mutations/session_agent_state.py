#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.session_agent_state import (
    delete_session_agent_state,
    insert_update_session_agent_state,
)
from ..types.session_agent_state import SessionAgentStateType


class InsertUpdateSessionAgentState(Mutation):
    session_agent_state = Field(SessionAgentStateType)

    class Arguments:
        session_uuid = String(required=True)
        session_agent_state_uuid = String(required=False)
        thread_id = String(required=False)
        task_uuid = String(required=False)
        agent_name = String(required=False)
        user_in_the_loop = String(required=False)
        user_action = String(required=False)
        agent_input = String(required=False)
        agent_output = String(required=False)
        predecessors = String(required=False)
        in_degree = Int(required=True)
        state = String(required=False)
        notes = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateSessionAgentState":
        try:
            session_agent_state = insert_update_session_agent_state(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateSessionAgentState(session_agent_state=session_agent_state)


class DeleteSessionAgentState(Mutation):
    ok = Boolean()

    class Arguments:
        session_uuid = String(required=True)
        session_agent_state_uuid = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "DeleteSessionAgentState":
        try:
            ok = delete_session_agent_state(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteSessionAgentState(ok=ok)
