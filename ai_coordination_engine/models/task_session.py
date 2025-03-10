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
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility

from ..types.task_session import TaskSessionListType, TaskSessionType
from .utils import _get_session, _get_task


class TaskSessionModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-task_sessions"

    task_uuid = UnicodeAttribute(hash_key=True)
    session_uuid = UnicodeAttribute(range_key=True)
    coordination_uuid = UnicodeAttribute()
    endpoint_id = UnicodeAttribute()
    task_query = UnicodeAttribute()
    iteration_count = NumberAttribute(default=0)
    status = UnicodeAttribute(default="initial")
    notes = ListAttribute(of=MapAttribute, default=[])
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_task_session(task_uuid: str, session_uuid: str) -> TaskSessionModel:
    return TaskSessionModel.get(task_uuid, session_uuid)


def get_task_session_count(task_uuid: str, session_uuid: str) -> int:
    return TaskSessionModel.count(
        task_uuid, TaskSessionModel.session_uuid == session_uuid
    )


def get_task_session_type(
    info: ResolveInfo, task_session: TaskSessionModel
) -> TaskSessionType:
    try:
        task = _get_task(task_session.coordination_uuid, task_session.task_uuid)
        session = _get_session(
            task_session.coordination_uuid, task_session.session_uuid
        )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    task_session = task_session.__dict__["attribute_values"]
    task_session["task"] = task
    task_session["session"] = session
    task_session.pop("coordination_uuid")
    task_session.pop("task_uuid")
    task_session.pop("session_uuid")
    return TaskSessionType(**Utility.json_loads(Utility.json_dumps(task_session)))


def resolve_task_session(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskSessionType:
    return get_task_session_type(
        info, get_task_session(kwargs["task_uuid"], kwargs["session_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["task_uuid", "session_uuid"],
    list_type_class=TaskSessionListType,
    type_funct=get_task_session_type,
)
def resolve_task_session_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskSessionListType:
    task_uuid = kwargs.get("task_uuid")
    coordination_uuid = kwargs.get("coordination_uuid")
    endpoint_id = info.context.get("endpoint_id")
    task_query = kwargs.get("task_query")
    statuses = kwargs.get("statuses")

    args = []
    inquiry_funct = TaskSessionModel.scan
    count_funct = TaskSessionModel.count
    if task_uuid:
        args = [task_uuid, None]
        inquiry_funct = TaskSessionModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_uuid is not None:
        the_filters &= TaskSessionModel.coordination_uuid == coordination_uuid
    if endpoint_id is not None:
        the_filters &= TaskSessionModel.endpoint_id == endpoint_id
    if task_query is not None:
        the_filters &= TaskSessionModel.task_query.contains(task_query)
    if statuses is not None:
        the_filters &= TaskSessionModel.status.is_in(statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "task_uuid",
        "range_key": "session_uuid",
    },
    range_key_required=True,
    model_funct=get_task_session,
    count_funct=get_task_session_count,
    type_funct=get_task_session_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_task_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    task_uuid = kwargs.get("task_uuid")
    session_uuid = kwargs.get("session_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "endpoint_id": info.context["endpoint_id"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in ["task_query", "status", "notes", "iteration_count"]:
            if key in kwargs:
                cols[key] = kwargs[key]
        TaskSessionModel(
            task_uuid,
            session_uuid,
            **cols,
        ).save()
        return

    task_session = kwargs.get("entity")
    actions = [
        TaskSessionModel.updated_by.set(kwargs["updated_by"]),
        TaskSessionModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to TaskSessionModel attributes
    field_map = {
        "task_query": TaskSessionModel.task_query,
        "iteration_count": TaskSessionModel.iteration_count,
        "status": TaskSessionModel.status,
        "notes": TaskSessionModel.notes,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(kwargs[key]))

    # Update the task_session entity
    task_session.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "task_uuid",
        "range_key": "session_uuid",
    },
    model_funct=get_task_session,
)
def delete_task_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
