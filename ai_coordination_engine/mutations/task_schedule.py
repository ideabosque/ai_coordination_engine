#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String
from silvaengine_utility import JSONCamelCase

from ..models.repositories import get_repo
from ..types.task_schedule import TaskScheduleType


class InsertUpdateTaskSchedule(Mutation):
    task_schedule = Field(TaskScheduleType)

    class Arguments:
        task_uuid = String(required=True)
        schedule_uuid = String(required=False)
        task_schedule = JSONCamelCase(required=False)
        coordination_uuid = String(required=False)
        schedule = String(required=False)
        status = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateTaskSchedule":
        try:
            task_schedule = get_repo("task_schedule").insert_update(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateTaskSchedule(task_schedule=task_schedule)


class DeleteTaskSchedule(Mutation):
    ok = Boolean()

    class Arguments:
        task_uuid = String(required=True)
        schedule_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteTaskSchedule":
        try:
            ok = get_repo("task_schedule").delete(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteTaskSchedule(ok=ok)
