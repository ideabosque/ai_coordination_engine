#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import ObjectType

from ..mutations.coordination import DeleteCoordination, InsertUpdateCoordination
from ..mutations.procedure_hub import ExecuteForUserInput, ExecuteProcedureTaskSession
from ..mutations.session import DeleteSession, InsertUpdateSession
from ..mutations.session_agent import DeleteSessionAgent, InsertUpdateSessionAgent
from ..mutations.session_run import DeleteSessionRun, InsertUpdateSessionRun
from ..mutations.task import DeleteTask, InsertUpdateTask
from ..mutations.task_schedule import DeleteTaskSchedule, InsertUpdateTaskSchedule


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
