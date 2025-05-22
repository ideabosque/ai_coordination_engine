#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import time
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, ObjectType, ResolveInfo, String

from .mutations.coordination import DeleteCoordination, InsertUpdateCoordination
from .mutations.procedure_hub import ExecuteForUserInput, ExecuteProcedureTaskSession
from .mutations.session import DeleteSession, InsertUpdateSession
from .mutations.session_agent import DeleteSessionAgent, InsertUpdateSessionAgent
from .mutations.session_run import DeleteSessionRun, InsertUpdateSessionRun
from .mutations.task import DeleteTask, InsertUpdateTask
from .mutations.task_schedule import DeleteTaskSchedule, InsertUpdateTaskSchedule
from .queries.coordination import resolve_coordination, resolve_coordination_list
from .queries.operation_hub import resolve_ask_operation_hub
from .queries.session import resolve_session, resolve_session_list
from .queries.session_agent import resolve_session_agent, resolve_session_agent_list
from .queries.session_run import resolve_session_run, resolve_session_run_list
from .queries.task import resolve_task, resolve_task_list
from .queries.task_schedule import resolve_task_schedule, resolve_task_schedule_list
from .types.coordination import CoordinationListType, CoordinationType
from .types.operation_hub import AskOperationHubType
from .types.session import SessionListType, SessionType
from .types.session_agent import SessionAgentListType, SessionAgentType
from .types.session_run import SessionRunListType, SessionRunType
from .types.task import TaskListType, TaskType
from .types.task_schedule import TaskScheduleListType, TaskScheduleType


def type_class():
    return [
        CoordinationListType,
        SessionListType,
        SessionType,
        CoordinationType,
        TaskType,
        TaskListType,
        TaskScheduleType,
        TaskScheduleListType,
        SessionAgentType,
        SessionAgentListType,
        SessionRunType,
        SessionRunListType,
        AskOperationHubType,
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
        task_uuid=String(required=False),
        user_id=String(required=False),
        statuses=List(String, required=False),
    )

    session_run = Field(
        SessionRunType,
        session_uuid=String(required=True),
        run_uuid=String(required=True),
    )

    session_run_list = Field(
        SessionRunListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        session_uuid=String(required=False),
        coordination_uuid=String(required=False),
        agent_uuid=String(required=False),
        thread_uuid=String(required=False),
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
        coordination_uuid=String(required=False),
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

    ask_operation_hub = Field(
        AskOperationHubType,
        coordination_uuid=String(required=True),
        user_id=String(required=False),
        agent_uuid=String(required=False),
        session_uuid=String(required=False),
        user_query=String(required=True),
        receiver_email=String(required=False),
        thread_uuid=String(required=False),
        stream=Boolean(required=False),
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

    def resolve_session(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> SessionType:
        return resolve_session(info, **kwargs)

    def resolve_session_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> SessionListType:
        return resolve_session_list(info, **kwargs)

    def resolve_session_run(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> SessionRunType:
        return resolve_session_run(info, **kwargs)

    def resolve_session_run_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> SessionRunListType:
        return resolve_session_run_list(info, **kwargs)

    def resolve_task(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> TaskType:
        return resolve_task(info, **kwargs)

    def resolve_task_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> TaskListType:
        return resolve_task_list(info, **kwargs)

    def resolve_session_agent(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> SessionAgentType:
        return resolve_session_agent(info, **kwargs)

    def resolve_session_agent_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> SessionAgentListType:
        return resolve_session_agent_list(info, **kwargs)

    def resolve_task_schedule(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> TaskScheduleType:
        return resolve_task_schedule(info, **kwargs)

    def resolve_task_schedule_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> TaskScheduleListType:
        return resolve_task_schedule_list(info, **kwargs)

    def resolve_ask_operation_hub(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> AskOperationHubType:
        return resolve_ask_operation_hub(info, **kwargs)


class Mutations(ObjectType):
    insert_update_coordination = InsertUpdateCoordination.Field()
    delete_coordination = DeleteCoordination.Field()
    insert_update_session = InsertUpdateSession.Field()
    delete_session = DeleteSession.Field()
    insert_update_session_run = InsertUpdateSessionRun.Field()
    delete_session_run = DeleteSessionRun.Field()
    insert_update_task = InsertUpdateTask.Field()
    delete_task = DeleteTask.Field()
    insert_update_session_agent = InsertUpdateSessionAgent.Field()
    delete_session_agent = DeleteSessionAgent.Field()
    insert_update_task_schedule = InsertUpdateTaskSchedule.Field()
    delete_task_schedule = DeleteTaskSchedule.Field()
    execute_procedure_task_session = ExecuteProcedureTaskSession.Field()
    execute_for_user_input = ExecuteForUserInput.Field()
