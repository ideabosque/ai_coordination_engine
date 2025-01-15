#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"


import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility
from tenacity import retry, stop_after_attempt, wait_exponential

from ..types.thread import ThreadListType, ThreadType
from .utils import _get_agent, _get_session


class ThreadModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-threads"

    session_uuid = UnicodeAttribute(hash_key=True)
    thread_id = UnicodeAttribute(range_key=True)
    coordination_uuid = UnicodeAttribute()
    agent_uuid = UnicodeAttribute(null=True)
    last_assistant_message = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="initial")
    log = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_thread(session_uuid: str, thread_id: str) -> ThreadModel:
    return ThreadModel.get(session_uuid, thread_id)


def get_thread_count(session_uuid: str, thread_id: str) -> int:
    return ThreadModel.count(session_uuid, ThreadModel.thread_id == thread_id)


def get_thread_type(info: ResolveInfo, thread: ThreadModel) -> ThreadType:
    try:
        session = _get_session(
            thread.coordination_uuid,
            thread.session_uuid,
        )
        agent = None
        if thread.agent_uuid is not None:
            agent = _get_agent(
                thread.coordination_uuid,
                thread.agent_uuid,
            )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    thread = thread.__dict__["attribute_values"]
    thread["session"] = session
    thread["agent"] = agent
    thread.pop("coordination_uuid")
    thread.pop("session_uuid")
    thread.pop("agent_uuid", None)
    return ThreadType(**Utility.json_loads(Utility.json_dumps(thread)))


def resolve_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType:
    return get_thread_type(
        info,
        get_thread(kwargs["session_uuid"], kwargs["thread_id"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["session_uuid", "thread_id"],
    list_type_class=ThreadListType,
    type_funct=get_thread_type,
    suffix="_list",
)
def resolve_thread_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    session_uuid = kwargs.get("session_uuid")
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_uuid = kwargs.get("agent_uuid")
    args = []
    inquiry_funct = ThreadModel.scan
    count_funct = ThreadModel.count
    if session_uuid:
        args = [session_uuid, None]
        inquiry_funct = ThreadModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_uuid is not None:
        the_filters &= ThreadModel.coordination_uuid == coordination_uuid
    if agent_uuid is not None:
        the_filters &= ThreadModel.agent_uuid == agent_uuid
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "thread_id",
    },
    range_key_required=True,
    model_funct=get_thread,
    count_funct=get_thread_count,
    type_funct=get_thread_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    session_uuid = kwargs.get("session_uuid")
    thread_id = kwargs.get("thread_id")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if kwargs.get("agent_uuid") is not None:
            cols["agent_uuid"] = kwargs["agent_uuid"]
        if kwargs.get("last_assistant_message") is not None:
            cols["last_assistant_message"] = kwargs["last_assistant_message"]
        if kwargs.get("status") is not None:
            cols["status"] = kwargs["status"]
        if kwargs.get("log") is not None:
            cols["log"] = kwargs["log"]
        ThreadModel(
            session_uuid,
            thread_id,
            **cols,
        ).save()
        return

    thread = kwargs.get("entity")
    actions = [
        ThreadModel.updated_by.set(kwargs["updated_by"]),
        ThreadModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of kwargs keys to ThreadModel attributes
    field_map = {
        "coordination_uuid": ThreadModel.coordination_uuid,
        "agent_uuid": ThreadModel.agent_uuid,
        "last_assistant_message": ThreadModel.last_assistant_message,
        "status": ThreadModel.status,
        "log": ThreadModel.log,
    }

    # Add actions dynamically based on the presence of keys in kwargs
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the thread
    thread.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "thread_id",
    },
    model_funct=get_thread,
)
def delete_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
