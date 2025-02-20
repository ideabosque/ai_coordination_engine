#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
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
from silvaengine_utility import Utility

from ..types.task_schedule import TaskScheduleListType, TaskScheduleType
from .utils import _get_coordination, _get_task


class TaskScheduleModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-task_schedules"

    task_uuid = UnicodeAttribute(hash_key=True)
    schedule_uuid = UnicodeAttribute(range_key=True)
    coordination_uuid = UnicodeAttribute()
    endpoint_id = UnicodeAttribute()
    schedule = UnicodeAttribute()
    status = UnicodeAttribute(default="initial")
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_task_schedule(task_uuid: str, schedule_uuid: str) -> TaskScheduleType:
    return TaskScheduleModel.get(
        hash_key=task_uuid,
        range_key=schedule_uuid,
    )


def get_task_schedule_count(task_uuid: str, schedule_uuid: str) -> int:
    return TaskScheduleModel.count(
        task_uuid,
        TaskScheduleModel.schedule_uuid == schedule_uuid,
    )


def get_task_schedule_type(
    info: ResolveInfo, task_schedule: TaskScheduleModel
) -> TaskScheduleType:
    try:
        task = _get_task(task_schedule.coordination_uuid, task_schedule.task_uuid)
        coordination = _get_coordination(
            info.context["endpoint_id"], task_schedule.coordination_uuid
        )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    task_schedule = task_schedule.__dict__["attribute_values"]
    task_schedule["task"] = task
    task_schedule["coordination"] = coordination
    task_schedule.pop("coordination_uuid")
    task_schedule.pop("endpoint_id")
    task_schedule.pop("task_uuid")
    return TaskScheduleType(**Utility.json_loads(Utility.json_dumps(task_schedule)))


def resolve_task_schedule(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskScheduleType:
    return get_task_schedule_type(
        info, get_task_schedule(kwargs["task_uuid"], kwargs["schedule_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["task_uuid", "schedule_uuid"],
    list_type_class=TaskScheduleListType,
    type_funct=get_task_schedule_type,
)
def resolve_task_schedule_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskScheduleListType:
    task_uuid = kwargs.get("task_uuid")
    coordination_uuid = kwargs.get("coordination_uuid")
    endpoint_id = info.context.get("endpoint_id")
    statuses = kwargs.get("statuses")

    args = []
    inquiry_funct = TaskScheduleModel.scan
    count_funct = TaskScheduleModel.count
    if task_uuid:
        args = [task_uuid, None]
        inquiry_funct = TaskScheduleModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_uuid is not None:
        the_filters &= TaskScheduleModel.coordination_uuid == coordination_uuid
    if endpoint_id is not None:
        the_filters &= TaskScheduleModel.endpoint_id == endpoint_id
    if statuses is not None:
        the_filters &= TaskScheduleModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "task_uuid",
        "range_key": "schedule_uuid",
    },
    model_funct=get_task_schedule,
    count_funct=get_task_schedule_count,
    type_funct=get_task_schedule_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_task_schedule(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskScheduleType:
    task_uuid = kwargs.get("task_uuid")
    schedule_uuid = kwargs.get("schedule_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "endpoint_id": info.context["endpoint_id"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in ["schedule", "status"]:
            if key in kwargs:
                cols[key] = kwargs[key]
        TaskScheduleModel(
            task_uuid,
            schedule_uuid,
            **cols,
        ).save()
        return

    task_schedule = kwargs.get("entity")
    actions = [
        TaskScheduleModel.updated_by.set(kwargs["updated_by"]),
        TaskScheduleModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to TaskScheduleModel attributes
    field_map = {
        "schedule": TaskScheduleModel.schedule,
        "status": TaskScheduleModel.status,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(kwargs[key]))

    # Update the task_session entity
    task_schedule.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "task_uuid",
        "range_key": "schedule_uuid",
    },
    model_funct=get_task_schedule,
)
def delete_task_schedule(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
