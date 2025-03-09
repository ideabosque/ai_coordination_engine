#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.task_session import delete_task_session, insert_update_task_session
from ..types.task_session import TaskSessionType


class InsertUpdateTaskSession(Mutation):
    task_session = Field(TaskSessionType)

    class Arguments:
        task_uuid = String(required=True)
        session_uuid = String(required=True)
        coordination_uuid = String(required=False)
        task_query = String(required=False)
        iteration_count = Int(required=False)
        status = String(required=False)
        notes = List(JSON, required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateTaskSession":
        try:
            task_session = insert_update_task_session(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateTaskSession(task_session=task_session)


class DeleteTaskSession(Mutation):
    ok = Boolean()

    class Arguments:
        task_uuid = String(required=True)
        session_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteTaskSession":
        try:
            ok = delete_task_session(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteTaskSession(ok=ok)
