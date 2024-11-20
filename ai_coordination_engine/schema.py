#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import time
from typing import Any, Dict

from graphene import (
    Boolean,
    DateTime,
    Field,
    Int,
    List,
    ObjectType,
    ResolveInfo,
    String,
)

from .mutations import (
    DeleteCoordination,
    DeleteCoordinationAgent,
    DeleteCoordinationMessage,
    DeleteCoordinationSession,
    InsertUpdateCoordination,
    InsertUpdateCoordinationAgent,
    InsertUpdateCoordinationMessage,
    InsertUpdateCoordinationSession,
)
from .queries import (
    resolve_coordination,
    resolve_coordination_agent,
    resolve_coordination_agent_list,
    resolve_coordination_list,
    resolve_coordination_message,
    resolve_coordination_message_list,
    resolve_coordination_session,
    resolve_coordination_session_list,
)
from .types import (
    CoordinationAgentListType,
    CoordinationAgentType,
    CoordinationListType,
    CoordinationMessageListType,
    CoordinationMessageType,
    CoordinationSessionListType,
    CoordinationSessionType,
    CoordinationType,
)


def type_class():
    return [
        CoordinationAgentListType,
        CoordinationAgentType,
        CoordinationListType,
        CoordinationMessageType,
        CoordinationMessageListType,
        CoordinationSessionListType,
        CoordinationSessionType,
        CoordinationType,
    ]


class Query(ObjectType):
    ping = String()

    coordination = Field(
        CoordinationType,
        coordination_type=String(required=True),
        coordination_uuid=String(required=True),
    )

    coordination_list = Field(
        CoordinationListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        coordination_type=String(required=False),
        coordination_name=String(required=False),
        coordination_description=String(required=False),
        assistant_id=String(required=False),
        assistant_types=List(String, required=False),
    )

    coordination_agent = Field(
        CoordinationAgentType,
        coordination_uuid=String(required=True),
        agent_uuid=String(required=True),
    )

    coordination_agent_list = Field(
        CoordinationAgentListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        coordination_uuid=String(required=False),
        agent_name=String(required=False),
        agent_description=String(required=False),
        coordination_types=List(String, required=False),
        response_format=String(required=False),
        predecessor=String(required=False),
        successor=String(required=False),
    )

    coordination_session = Field(
        CoordinationSessionType,
        coordination_uuid=String(required=True),
        session_uuid=String(required=True),
    )

    coordination_session_list = Field(
        CoordinationSessionListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        coordination_uuid=String(required=False),
        coordination_types=List(String, required=False),
        thread_id=String(required=False),
        current_agent_uuid=String(required=False),
        statuses=List(String, required=False),
    )

    coordination_message = Field(
        CoordinationMessageType,
        session_uuid=String(required=True),
        message_id=String(required=True),
    )

    coordination_message_list = Field(
        CoordinationMessageListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        session_uuid=String(required=False),
        coordination_uuid=String(required=False),
        thread_id=String(required=False),
        agent_uuid=String(required=False),
    )

    def resolve_ping(self, info: ResolveInfo) -> str:
        return f"Hello at {time.strftime('%X')}!!"

    def resolve_coordination(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
        return resolve_coordination(info, **kwargs)

    def resolve_coordination_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> Any:
        return resolve_coordination_list(info, **kwargs)

    def resolve_coordination_agent(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> Any:
        return resolve_coordination_agent(info, **kwargs)

    def resolve_coordination_agent_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> Any:
        return resolve_coordination_agent_list(info, **kwargs)

    def resolve_coordination_session(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> Any:
        return resolve_coordination_session(info, **kwargs)

    def resolve_coordination_session_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> Any:
        return resolve_coordination_session_list(info, **kwargs)

    def resolve_coordination_message(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> Any:
        return resolve_coordination_message(info, **kwargs)

    def resolve_coordination_message_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> Any:
        return resolve_coordination_message_list(info, **kwargs)


class Mutations(ObjectType):
    insert_update_coordination = InsertUpdateCoordination.Field()
    delete_coordination = DeleteCoordination.Field()
    insert_update_coordination_agent = InsertUpdateCoordinationAgent.Field()
    delete_coordination_agent = DeleteCoordinationAgent.Field()
    insert_update_coordination_session = InsertUpdateCoordinationSession.Field()
    delete_coordination_session = DeleteCoordinationSession.Field()
    insert_update_coordination_message = InsertUpdateCoordinationMessage.Field()
    delete_coordination_message = DeleteCoordinationMessage.Field()
