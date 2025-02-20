#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.task_schedule import delete_task_schedule, insert_update_task_schedule
from ..types.task_schedule import TaskScheduleType


class InsertUpdateTaskSchedule(Mutation):
    task_schedule = Field(TaskScheduleType)

    class Arguments:
        task_uuid = String(required=True)
        task_schedule = JSON(required=False)
        coordination_uuid = String(required=False)
        schedule = String(required=False)
        status = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateTaskSchedule":
        try:
            task_schedule = insert_update_task_schedule(info, **kwargs)
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
            ok = delete_task_schedule(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteTaskSchedule(ok=ok)
