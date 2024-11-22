#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, DateTime, Field, Float, Int, List, Mutation, String
from silvaengine_utility import JSON

from .handlers import (
    delete_agent_handler,
    delete_coordination_handler,
    delete_session_handler,
    delete_thread_handler,
    insert_update_agent_handler,
    insert_update_coordination_handler,
    insert_update_session_handler,
    insert_update_thread_handler,
)
from .types import AgentType, CoordinationType, SessionType, ThreadType


class InsertUpdateCoordination(Mutation):
    coordination = Field(CoordinationType)

    class Arguments:
        coordination_type = String(required=True)
        coordination_uuid = String(required=False)
        coordination_name = String(required=False)
        coordination_description = String(required=False)
        assistant_id = String(required=False)
        assistant_type = String(required=False)
        additional_instructions = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateCoordination":
        try:
            coordination = insert_update_coordination_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateCoordination(coordination=coordination)


class DeleteCoordination(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_type = String(required=True)
        coordination_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteCoordination":
        try:
            ok = delete_coordination_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteCoordination(ok=ok)


class InsertUpdateAgent(Mutation):
    agent = Field(AgentType)

    class Arguments:
        coordination_uuid = String(required=True)
        agent_uuid = String(required=False)
        agent_name = String(required=False)
        agent_instructions = String(required=False)
        coordination_type = String(required=False)
        response_format = String(required=False)
        json_schema = JSON(required=False)
        tools = List(JSON, required=False)
        predecessor = String(required=False)
        successor = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateAgent":
        try:
            agent = insert_update_agent_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateAgent(agent=agent)


class DeleteAgent(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        agent_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteAgent":
        try:
            ok = delete_agent_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteAgent(ok=ok)


class InsertUpdateSession(Mutation):
    session = Field(SessionType)

    class Arguments:
        coordination_uuid = String(required=True)
        session_uuid = String(required=False)
        coordination_type = String(required=False)
        status = String(required=False)
        notes = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateSession":
        try:
            session = insert_update_session_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateSession(session=session)


class DeleteSession(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        session_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteSession":
        try:
            ok = delete_session_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteSession(ok=ok)


class InsertUpdateThread(Mutation):
    thread = Field(ThreadType)

    class Arguments:
        session_uuid = String(required=True)
        thread_id = String(required=True)
        coordination_uuid = String(required=True)
        agent_uuid = String(required=False)
        last_assistant_message = String(required=False)
        status = String(required=False)
        log = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateThread":
        try:
            thread = insert_update_thread_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateThread(thread=thread)


class DeleteThread(Mutation):
    ok = Boolean()

    class Arguments:
        session_uuid = String(required=True)
        message_id = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteThread":
        try:
            ok = delete_thread_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteThread(ok=ok)
