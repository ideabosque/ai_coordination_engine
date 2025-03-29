#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
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

from ..types.session import SessionListType, SessionType
from .utils import _get_coordination, _get_task


class UserIdIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "user_id-index"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute(range_key=True)


class TaskUuidIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "task_uuid-index"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    task_uuid = UnicodeAttribute(range_key=True)


class SessionModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-sessions"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    session_uuid = UnicodeAttribute(range_key=True)
    task_uuid = UnicodeAttribute(null=True)
    user_id = UnicodeAttribute(null=True)
    endpoint_id = UnicodeAttribute()
    task_query = UnicodeAttribute(null=True)
    iteration_count = NumberAttribute(default=0)
    subtask_queries = ListAttribute(of=MapAttribute, default=[])
    status = UnicodeAttribute(default="initial")
    logs = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    task_uuid_index = TaskUuidIndex()
    user_id_index = UserIdIndex()


def create_session_table(logger: logging.Logger) -> bool:
    """Create the Session table if it doesn't exist."""
    if not SessionModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        SessionModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Session table has been created.")
    return True


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
            session.endpoint_id,
            session.coordination_uuid,
        )
        task = None
        if session.task_uuid:
            task = _get_task(
                session.coordination_uuid,
                session.task_uuid,
            )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    session = session.__dict__["attribute_values"]
    session["coordination"] = coordination
    session.pop("endpoint_id")
    session.pop("coordination_uuid")
    if task:
        session["task"] = task
        session.pop("task_uuid")
    return SessionType(**Utility.json_loads(Utility.json_dumps(session)))


def resolve_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType:
    return get_session_type(
        info,
        get_session(kwargs["coordination_uuid"], kwargs["session_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_uuid", "session_uuid", "task_uuid", "user_id"],
    list_type_class=SessionListType,
    type_funct=get_session_type,
)
def resolve_session_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    coordination_uuid = kwargs.get("coordination_uuid")
    task_uuid = kwargs.get("task_uuid")
    user_id = kwargs.get("user_id")
    endpoint_id = info.context["endpoint_id"]
    statuses = kwargs.get("statuses")
    args = []
    inquiry_funct = SessionModel.scan
    count_funct = SessionModel.count
    if coordination_uuid:
        args = [coordination_uuid, None]
        inquiry_funct = SessionModel.query
        if task_uuid:
            count_funct = SessionModel.task_uuid_index.count
            args[1] = SessionModel.task_uuid_index == task_uuid
            inquiry_funct = SessionModel.task_uuid_index.query
        if user_id:
            count_funct = SessionModel.user_id_index.count
            args[1] = SessionModel.user_id_index == user_id
            inquiry_funct = SessionModel.user_id_index.query

    the_filters = None  # We can add filters for the query.
    if endpoint_id is not None:
        the_filters &= SessionModel.endpoint_id == endpoint_id
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
)
def insert_update_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    coordination_uuid = kwargs.get("coordination_uuid")
    session_uuid = kwargs.get("session_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "endpoint_id": info.context["endpoint_id"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "status",
            "logs",
            "task_uuid",
            "user_id",
            "task_query",
            "iteration_count",
            "subtask_queries",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]
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
        "status": SessionModel.status,
        "logs": SessionModel.logs,
        "task_query": SessionModel.task_query,
        "iteration_count": SessionModel.iteration_count,
        "subtask_queries": SessionModel.subtask_queries,
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
