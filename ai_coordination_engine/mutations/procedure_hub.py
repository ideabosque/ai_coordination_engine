#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from ..handlers.procedure_hub import procedure_hub, user_in_the_loop
from ..types.procedure_hub import ProcedureTaskSessionType


class ExecuteProcedureTaskSession(Mutation):
    procedure_task_session = Field(ProcedureTaskSessionType)

    class Arguments:
        coordination_uuid = String(required=True)
        task_uuid = String(required=True)
        user_id = String(required=False)
        task_query = String(required=False)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "ExecuteProcedureTaskSession":
        try:
            procedure_task_session = procedure_hub.execute_procedure_task_session(
                info, **kwargs
            )
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return ExecuteProcedureTaskSession(
            procedure_task_session=procedure_task_session
        )


class ExecuteForUserInput(Mutation):
    ok = Boolean()

    class Arguments:
        session_uuid = String(required=True)
        session_agent_uuid = String(required=True)
        user_input = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "ExecuteForUserInput":
        try:
            ok = user_in_the_loop.execute_for_user_input(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return ExecuteForUserInput(ok=ok)
