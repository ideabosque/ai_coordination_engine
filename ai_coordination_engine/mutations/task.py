#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.task import delete_task, insert_update_task
from ..types.task import TaskType


class InsertUpdateTask(Mutation):
    task = Field(TaskType)

    class Arguments:
        coordination_uuid = String(required=True)
        task_uuid = String(required=False)
        task_name = String(required=True)
        task_description = String(required=False)
        initial_task_query = String(required=False)
        subtask_queries = List(JSON, required=False)
        agent_actions = JSON(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateTask":
        try:
            task = insert_update_task(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateTask(task=task)


class DeleteTask(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        task_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteTask":
        try:
            ok = delete_task(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteTask(ok=ok)
