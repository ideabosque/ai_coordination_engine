#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import time
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, ObjectType, ResolveInfo, String

from .mutations.agent import DeleteAgent, InsertUpdateAgent
from .mutations.coordination import DeleteCoordination, InsertUpdateCoordination
from .mutations.session import DeleteSession, InsertUpdateSession
from .mutations.session_agent import DeleteSessionAgent, InsertUpdateSessionAgent
from .mutations.task import DeleteTask, InsertUpdateTask
from .mutations.task_schedule import DeleteTaskSchedule, InsertUpdateTaskSchedule
from .mutations.task_session import DeleteTaskSession, InsertUpdateTaskSession
from .mutations.thread import DeleteThread, InsertUpdateThread
from .queries.agent import resolve_agent, resolve_agent_list
from .queries.coordination import resolve_coordination, resolve_coordination_list
from .queries.session import resolve_session, resolve_session_list
from .queries.session_agent import resolve_session_agent, resolve_session_agent_list
from .queries.task import resolve_task, resolve_task_list
from .queries.task_schedule import resolve_task_schedule, resolve_task_schedule_list
from .queries.task_session import resolve_task_session, resolve_task_session_list
from .queries.thread import resolve_thread, resolve_thread_list
from .types.agent import AgentListType, AgentType
from .types.coordination import CoordinationListType, CoordinationType
from .types.session import SessionListType, SessionType
from .types.session_agent import SessionAgentListType, SessionAgentType
from .types.task import TaskListType, TaskType
from .types.task_schedule import TaskScheduleListType, TaskScheduleType
from .types.task_session import TaskSessionListType, TaskSessionType
from .types.thread import ThreadListType, ThreadType


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
        TaskType,
        TaskListType,
        TaskSessionType,
        TaskSessionListType,
        TaskScheduleType,
        TaskScheduleListType,
        SessionAgentType,
        SessionAgentListType,
    ]


class Query(ObjectType):
    ping = String()

    coordination = Field(
        CoordinationType,
        coordination_uuid=String(required=True),
    )

    coordination_list = Field(
        CoordinationListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        coordination_name=String(required=False),
        coordination_description=String(required=False),
        assistant_id=String(required=False),
    )

    agent = Field(
        AgentType,
        coordination_uuid=String(required=True),
        agent_name=String(required=False),
        agent_version_uuid=String(required=False),
    )

    agent_list = Field(
        AgentListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        coordination_uuid=String(required=False),
        agent_name=String(required=False),
        response_format=String(required=False),
        status=String(required=False),
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
        agent_name=String(required=False),
    )

    task = Field(
        TaskType,
        coordination_uuid=String(required=True),
        task_uuid=String(required=True),
    )

    task_list = Field(
        TaskListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        coordination_uuid=String(required=False),
        task_name=String(required=False),
        task_description=String(required=False),
        initial_task_query=String(required=False),
    )

    task_session = Field(
        TaskSessionType,
        task_uuid=String(required=True),
        session_uuid=String(required=True),
    )

    task_session_list = Field(
        TaskSessionListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        task_uuid=String(required=False),
        coordination_uuid=String(required=False),
        task_query=String(required=False),
        statuses=List(String, required=False),
    )

    session_agent = Field(
        SessionAgentType,
        session_uuid=String(required=True),
        session_agent_uuid=String(required=True),
    )

    session_agent_list = Field(
        SessionAgentListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        session_uuid=String(required=False),
        thread_id=String(required=False),
        task_uuid=String(required=False),
        agent_name=String(required=False),
        primary_path=Boolean(required=False),
        user_in_the_loop=String(required=False),
        predecessor=String(required=False),
        predecessors=List(String, required=False),
        in_degree=Int(required=False),
        states=List(String, required=False),
    )

    task_schedule = Field(
        TaskScheduleType,
        task_uuid=String(required=True),
        schedule_uuid=String(required=True),
    )

    task_schedule_list = Field(
        TaskScheduleListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        task_uuid=String(required=False),
        coordination_uuid=String(required=False),
        statuses=List(String, required=False),
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

    def resolve_task(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType:
        return resolve_task(info, **kwargs)

    def resolve_task_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadListType:
        return resolve_task_list(info, **kwargs)

    def resolve_task_session(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadType:
        return resolve_task_session(info, **kwargs)

    def resolve_task_session_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadListType:
        return resolve_task_session_list(info, **kwargs)

    def resolve_session_agent(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadType:
        return resolve_session_agent(info, **kwargs)

    def resolve_session_agent_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadListType:
        return resolve_session_agent_list(info, **kwargs)

    def resolve_task_schedule(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadType:
        return resolve_task_schedule(info, **kwargs)

    def resolve_task_schedule_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadListType:
        return resolve_task_schedule_list(info, **kwargs)


class Mutations(ObjectType):
    insert_update_coordination = InsertUpdateCoordination.Field()
    delete_coordination = DeleteCoordination.Field()
    insert_update_agent = InsertUpdateAgent.Field()
    delete_agent = DeleteAgent.Field()
    insert_update_session = InsertUpdateSession.Field()
    delete_session = DeleteSession.Field()
    insert_update_thread = InsertUpdateThread.Field()
    delete_thread = DeleteThread.Field()
    insert_update_task = InsertUpdateTask.Field()
    delete_task = DeleteTask.Field()
    insert_update_task_session = InsertUpdateTaskSession.Field()
    delete_task_session = DeleteTaskSession.Field()
    insert_update_session_agent = InsertUpdateSessionAgent.Field()
    delete_session_agent = DeleteSessionAgent.Field()
    insert_update_task_schedule = InsertUpdateTaskSchedule.Field()
    delete_task_schedule = DeleteTaskSchedule.Field()
