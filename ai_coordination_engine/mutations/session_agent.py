#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, Mutation, String
from silvaengine_utility import JSONCamelCase

from ..models.session_agent import delete_session_agent, insert_update_session_agent
from ..types.session_agent import SessionAgentType


class InsertUpdateSessionAgent(Mutation):
    session_agent = Field(SessionAgentType)

    class Arguments:
        session_uuid = String(required=True)
        session_agent_uuid = String(required=False)
        coordination_uuid = String(required=False)
        agent_uuid = String(required=False)
        agent_action = JSONCamelCase(required=False)
        user_input = String(required=False)
        agent_input = String(required=False)
        agent_output = String(required=False)
        in_degree = Int(required=False)
        state = String(required=False)
        notes = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateSessionAgent":
        try:
            session_agent = insert_update_session_agent(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateSessionAgent(session_agent=session_agent)


class DeleteSessionAgent(Mutation):
    ok = Boolean()

    class Arguments:
        session_uuid = String(required=True)
        session_agent_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteSessionAgent":
        try:
            ok = delete_session_agent(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteSessionAgent(ok=ok)
