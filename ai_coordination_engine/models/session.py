#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility

from ..models.thread import ThreadModel
from ..types.session import SessionListType, SessionType
from .utils import _get_coordination, _get_thread_ids


class SessionModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-sessions"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    session_uuid = UnicodeAttribute(range_key=True)
    coordination_type = UnicodeAttribute()
    status = UnicodeAttribute(default="initial")
    notes = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_session(coordination_uuid: str, session_uuid: str) -> SessionModel:
    return SessionModel.get(coordination_uuid, session_uuid)


def get_session_count(coordination_uuid: str, session_uuid: str) -> int:
    return SessionModel.count(
        coordination_uuid, SessionModel.session_uuid == session_uuid
    )


def get_session_type(info: ResolveInfo, session: SessionModel) -> SessionType:
    try:
        coordination = _get_coordination(
            session.coordination_type,
            session.coordination_uuid,
        )
        thread_ids = _get_thread_ids(session.session_uuid)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    session = session.__dict__["attribute_values"]
    session["coordination"] = coordination
    session["thread_ids"] = thread_ids
    session.pop("coordination_type")
    session.pop("coordination_uuid")
    return SessionType(**Utility.json_loads(Utility.json_dumps(session)))


def resolve_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType:
    return get_session_type(
        info,
        get_session(kwargs["coordination_uuid"], kwargs["session_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_uuid", "session_uuid"],
    list_type_class=SessionListType,
    type_funct=get_session_type,
)
def resolve_session_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    coordination_uuid = kwargs.get("coordination_uuid")
    coordination_types = kwargs.get("coordination_types")
    statuses = kwargs.get("statuses")
    args = []
    inquiry_funct = SessionModel.scan
    count_funct = SessionModel.count
    if coordination_uuid:
        args = [coordination_uuid, None]
        inquiry_funct = SessionModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_types is not None:
        the_filters &= SessionModel.coordination_type.is_in(*coordination_types)
    if statuses is not None:
        the_filters &= SessionModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "session_uuid",
    },
    model_funct=get_session,
    count_funct=get_session_count,
    type_funct=get_session_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    coordination_uuid = kwargs.get("coordination_uuid")
    session_uuid = kwargs.get("session_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_type": kwargs["coordination_type"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if kwargs.get("status") is not None:
            cols["status"] = kwargs["status"]
        if kwargs.get("notes") is not None:
            cols["notes"] = kwargs["notes"]
        SessionModel(
            coordination_uuid,
            session_uuid,
            **cols,
        ).save()
        return

    session = kwargs.get("entity")
    actions = [
        SessionModel.updated_by.set(kwargs["updated_by"]),
        SessionModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of kwargs keys to SessionModel attributes
    field_map = {
        "coordination_type": SessionModel.coordination_type,
        "status": SessionModel.status,
        "notes": SessionModel.notes,
    }

    # Add actions dynamically based on the presence of keys in kwargs
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the session
    session.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "session_uuid",
    },
    model_funct=get_session,
)
def delete_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
