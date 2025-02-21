#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.agent import delete_agent, insert_update_agent
from ..types.agent import AgentType


class InsertUpdateAgent(Mutation):
    agent = Field(AgentType)

    class Arguments:
        coordination_uuid = String(required=True)
        agent_version_uuid = String(required=False)
        agent_name = String(required=True)
        agent_instructions = String(required=False)
        response_format = String(required=False)
        json_schema = JSON(required=False)
        tools = List(JSON, required=False)
        predecessor = String(required=False)
        status = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateAgent":
        try:
            agent = insert_update_agent(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateAgent(agent=agent)


class DeleteAgent(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        agent_version_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteAgent":
        try:
            ok = delete_agent(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteAgent(ok=ok)
