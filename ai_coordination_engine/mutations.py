#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, DateTime, Field, Float, Int, List, Mutation, String

from silvaengine_utility import JSON

from .handlers import (
    delete_coordination_agent_handler,
    delete_coordination_handler,
    delete_coordination_message_handler,
    delete_coordination_session_handler,
    insert_update_coordination_agent_handler,
    insert_update_coordination_handler,
    insert_update_coordination_message_handler,
    insert_update_coordination_session_handler,
)
from .types import (
    CoordinationAgentType,
    CoordinationMessageType,
    CoordinationSessionType,
    CoordinationType,
)


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


class InsertUpdateCoordinationAgent(Mutation):
    coordination_agent = Field(CoordinationAgentType)

    class Arguments:
        coordination_uuid = String(required=True)
        agent_uuid = String(required=False)
        agent_name = String(required=False)
        agent_description = String(required=False)
        agent_instructions = String(required=False)
        coordination_type = String(required=False)
        response_format = String(required=False)
        predecessor = String(required=False)
        successor = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateCoordinationAgent":
        try:
            coordination_agent = insert_update_coordination_agent_handler(
                info, **kwargs
            )
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateCoordinationAgent(coordination_agent=coordination_agent)


class DeleteCoordinationAgent(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        agent_uuid = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "DeleteCoordinationAgent":
        try:
            ok = delete_coordination_agent_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteCoordinationAgent(ok=ok)


class InsertUpdateCoordinationSession(Mutation):
    coordination_session = Field(CoordinationSessionType)

    class Arguments:
        coordination_uuid = String(required=True)
        session_uuid = String(required=False)
        coordination_type = String(required=False)
        thread_id = String(required=False)
        current_agent_uuid = String(required=False)
        last_assistant_message = String(required=False)
        status = String(required=False)
        log = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateCoordinationSession":
        try:
            coordination_session = insert_update_coordination_session_handler(
                info, **kwargs
            )
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateCoordinationSession(
            coordination_session=coordination_session
        )


class DeleteCoordinationSession(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        session_uuid = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "DeleteCoordinationSession":
        try:
            ok = delete_coordination_session_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteCoordinationSession(ok=ok)


class InsertUpdateCoordinationMessage(Mutation):
    coordination_message = Field(CoordinationMessageType)

    class Arguments:
        session_uuid = String(required=True)
        message_id = String(required=True)
        coordination_uuid = String(required=True)
        thread_id = String(required=True)
        agent_uuid = String(required=False)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateCoordinationMessage":
        try:
            coordination_message = insert_update_coordination_message_handler(
                info, **kwargs
            )
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateCoordinationMessage(
            coordination_message=coordination_message
        )


class DeleteCoordinationMessage(Mutation):
    ok = Boolean()

    class Arguments:
        session_uuid = String(required=True)
        message_id = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "DeleteCoordinationMessage":
        try:
            ok = delete_coordination_message_handler(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteCoordinationMessage(ok=ok)
