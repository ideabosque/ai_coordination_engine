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
    DeleteAgent,
    DeleteCoordination,
    DeleteSession,
    DeleteThread,
    InsertUpdateAgent,
    InsertUpdateCoordination,
    InsertUpdateSession,
    InsertUpdateThread,
)
from .queries import (
    resolve_agent,
    resolve_agent_list,
    resolve_coordination,
    resolve_coordination_list,
    resolve_session,
    resolve_session_list,
    resolve_thread,
    resolve_thread_list,
)
from .types import (
    AgentListType,
    AgentType,
    CoordinationListType,
    CoordinationType,
    SessionListType,
    SessionType,
    ThreadListType,
    ThreadType,
)


def type_class():
    return [
        AgentListType,
        AgentType,
        CoordinationListType,
        ThreadType,
        ThreadListType,
        SessionListType,
        SessionType,
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

    agent = Field(
        AgentType,
        coordination_uuid=String(required=True),
        agent_uuid=String(required=True),
    )

    agent_list = Field(
        AgentListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        coordination_uuid=String(required=False),
        agent_name=String(required=False),
        coordination_types=List(String, required=False),
        response_format=String(required=False),
        predecessor=String(required=False),
        successor=String(required=False),
    )

    session = Field(
        SessionType,
        coordination_uuid=String(required=True),
        session_uuid=String(required=True),
    )

    session_list = Field(
        SessionListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        coordination_uuid=String(required=False),
        coordination_types=List(String, required=False),
        statuses=List(String, required=False),
    )

    thread = Field(
        ThreadType,
        session_uuid=String(required=True),
        thread_id=String(required=True),
    )

    thread_list = Field(
        ThreadListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        session_uuid=String(required=False),
        coordination_uuid=String(required=False),
        agent_uuid=String(required=False),
    )

    def resolve_ping(self, info: ResolveInfo) -> str:
        return f"Hello at {time.strftime('%X')}!!"

    def resolve_coordination(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> CoordinationType:
        return resolve_coordination(info, **kwargs)

    def resolve_coordination_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> CoordinationListType:
        return resolve_coordination_list(info, **kwargs)

    def resolve_agent(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType:
        return resolve_agent(info, **kwargs)

    def resolve_agent_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> AgentListType:
        return resolve_agent_list(info, **kwargs)

    def resolve_session(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> SessionType:
        return resolve_session(info, **kwargs)

    def resolve_session_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> SessionListType:
        return resolve_session_list(info, **kwargs)

    def resolve_thread(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType:
        return resolve_thread(info, **kwargs)

    def resolve_thread_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadListType:
        return resolve_thread_list(info, **kwargs)


class Mutations(ObjectType):
    insert_update_coordination = InsertUpdateCoordination.Field()
    delete_coordination = DeleteCoordination.Field()
    insert_update_agent = InsertUpdateAgent.Field()
    delete_agent = DeleteAgent.Field()
    insert_update_session = InsertUpdateSession.Field()
    delete_session = DeleteSession.Field()
    insert_update_thread = InsertUpdateThread.Field()
    delete_thread = DeleteThread.Field()
