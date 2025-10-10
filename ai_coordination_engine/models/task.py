#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility, method_cache

from ..handlers.config import Config
from ..types.task import TaskListType, TaskType
from .utils import _get_coordination


class TaskModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-tasks"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    task_uuid = UnicodeAttribute(range_key=True)
    task_name = UnicodeAttribute()
    task_description = UnicodeAttribute(null=True)
    initial_task_query = UnicodeAttribute()
    endpoint_id = UnicodeAttribute()
    subtask_queries = ListAttribute(of=MapAttribute)
    agent_actions = MapAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Use cascading cache purging for tasks
                from ..models.cache import purge_entity_cascading_cache

                try:
                    task = resolve_task(args[0], **kwargs)
                except Exception as e:
                    task = None

                entity_keys = {}
                if task:
                    entity_keys["task_uuid"] = task.task_uuid
                    entity_keys["coordination_uuid"] = task.coordination[
                        "coordination_uuid"
                    ]

                result = purge_entity_cascading_cache(
                    args[0].context.get("logger"),
                    entity_type="task",
                    context_keys=None,
                    entity_keys=entity_keys if entity_keys else None,
                    cascade_depth=3,
                )

                ## Original function.
                result = original_function(*args, **kwargs)

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


def create_task_table(logger: logging.Logger) -> bool:
    """Create the Task table if it doesn't exist."""
    if not TaskModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        TaskModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Task table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name("models", "task")
)
def get_task(coordination_uuid: str, task_uuid: str) -> TaskModel:
    return TaskModel.get(coordination_uuid, task_uuid)


def get_task_count(coordination_uuid: str, task_uuid: str) -> int:
    return TaskModel.count(coordination_uuid, TaskModel.task_uuid == task_uuid)


def get_task_type(info: ResolveInfo, task: TaskModel) -> TaskType:
    try:
        coordination = _get_coordination(task.endpoint_id, task.coordination_uuid)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    task = task.__dict__["attribute_values"]
    task["coordination"] = coordination
    task.pop("endpoint_id")
    task.pop("coordination_uuid")
    return TaskType(**Utility.json_normalize(task))


def resolve_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> TaskType:
    count = get_task_count(kwargs["coordination_uuid"], kwargs["task_uuid"])
    if count == 0:
        return None

    return get_task_type(
        info, get_task(kwargs["coordination_uuid"], kwargs["task_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_uuid", "task_uuid"],
    list_type_class=TaskListType,
    type_funct=get_task_type,
)
def resolve_task_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    coordination_uuid = kwargs.get("coordination_uuid")
    task_name = kwargs.get("task_name")
    task_description = kwargs.get("task_description")
    initial_task_query = kwargs.get("initial_task_query")
    endpoint_id = info.context["endpoint_id"]
    args = []
    inquiry_funct = TaskModel.scan
    count_funct = TaskModel.count
    if coordination_uuid:
        args = [coordination_uuid, None]
        inquiry_funct = TaskModel.query

    the_filters = None  # We can add filters for the query.
    if task_name is not None:
        the_filters &= TaskModel.task_name.contains(task_name)
    if task_description is not None:
        the_filters &= TaskModel.task_description.contains(task_description)
    if initial_task_query is not None:
        the_filters &= TaskModel.initial_task_query.contains(initial_task_query)
    if endpoint_id is not None:
        the_filters &= TaskModel.endpoint_id == endpoint_id
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@purge_cache()
@insert_update_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "task_uuid",
    },
    model_funct=get_task,
    count_funct=get_task_count,
    type_funct=get_task_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    coordination_uuid = kwargs.get("coordination_uuid")
    task_uuid = kwargs.get("task_uuid")

    if "subtask_queries" in kwargs or "agent_actions" in kwargs:
        coordination = _get_coordination(info.context["endpoint_id"], coordination_uuid)
        valid_agent_uuids = [agent["agent_uuid"] for agent in coordination["agents"]]

        # Filter subtask queries
        if "subtask_queries" in kwargs:
            kwargs["subtask_queries"] = [
                query
                for query in kwargs["subtask_queries"]
                if query["agent_uuid"] in valid_agent_uuids
            ]

        # Filter agent actions
        if "agent_actions" in kwargs:
            kwargs["agent_actions"] = {
                uuid: action
                for uuid, action in kwargs["agent_actions"].items()
                if uuid in valid_agent_uuids
            }

    if kwargs.get("entity") is None:
        cols = {
            "task_name": kwargs["task_name"],
            "endpoint_id": info.context["endpoint_id"],
            "subtask_queries": [],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "task_description",
            "initial_task_query",
            "subtask_queries",
            "agent_actions",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]
        TaskModel(
            coordination_uuid,
            task_uuid,
            **cols,
        ).save()
        return

    task = kwargs.get("entity")
    actions = [
        TaskModel.updated_by.set(kwargs["updated_by"]),
        TaskModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to TaskModel attributes
    field_map = {
        "task_name": TaskModel.task_name,
        "task_description": TaskModel.task_description,
        "initial_task_query": TaskModel.initial_task_query,
        "subtask_queries": TaskModel.subtask_queries,
        "agent_actions": TaskModel.agent_actions,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(kwargs[key]))

    # Update the task entity
    task.update(actions=actions)
    return


@purge_cache()
@delete_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "task_uuid",
    },
    model_funct=get_task,
)
def delete_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
