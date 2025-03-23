#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
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

from ..types.session_thread import SessionThreadListType, SessionThreadType
from .utils import _get_session


class AgentUuidIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "agent_uuid-index"

    session_uuid = UnicodeAttribute(hash_key=True)
    agent_uuid = UnicodeAttribute(range_key=True)


class SessionThreadModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-session_threads"

    session_uuid = UnicodeAttribute(hash_key=True)
    thread_uuid = UnicodeAttribute(range_key=True)
    agent_uuid = UnicodeAttribute()
    coordination_uuid = UnicodeAttribute()
    endpoint_id = UnicodeAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    agent_uuid_index = AgentUuidIndex()


def create_session_thread_table(logger: logging.Logger) -> bool:
    """Create the SessionThread table if it doesn't exist."""
    if not SessionThreadModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        SessionThreadModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The SessionThread table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_session_thread(session_uuid: str, thread_uuid: str) -> SessionThreadModel:
    return SessionThreadModel.get(session_uuid, thread_uuid)


def get_session_thread_count(session_uuid: str, thread_uuid: str) -> int:
    return SessionThreadModel.count(
        session_uuid, SessionThreadModel.thread_uuid == thread_uuid
    )


def get_session_thread_type(
    info: ResolveInfo, session_thread: SessionThreadModel
) -> SessionThreadType:
    try:
        session = _get_session(
            session_thread.coordination_uuid, session_thread.session_uuid
        )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    session_thread = session_thread.__dict__["attribute_values"]
    session_thread["session"] = session
    session_thread.pop("coordination_uuid")
    session_thread.pop("session_uuid")
    return SessionThreadType(**Utility.json_loads(Utility.json_dumps(session_thread)))


def resolve_session_thread(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionThreadType:
    return get_session_thread_type(
        info,
        get_session_thread(kwargs["session_uuid"], kwargs["thread_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["session_uuid", "thread_uuid", "agent_uuid"],
    list_type_class=SessionThreadListType,
    type_funct=get_session_thread_type,
)
def resolve_session_thread_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    session_uuid = kwargs.get("session_uuid")
    endpoint_id = info.context["endpoint_id"]
    agent_uuid = kwargs.get("agent_uuid")
    coordination_uuid = kwargs.get("coordination_uuid")
    args = []
    inquiry_funct = SessionThreadModel.scan
    count_funct = SessionThreadModel.count
    if session_uuid:
        args = [session_uuid, None]
        inquiry_funct = SessionThreadModel.query
        if agent_uuid:
            inquiry_funct = SessionThreadModel.agent_uuid_index.query
            args[1] = SessionThreadModel.agent_uuid == agent_uuid
            count_funct = SessionThreadModel.agent_uuid_index.count

    the_filters = None  # We can add filters for the query.
    if endpoint_id is not None:
        the_filters &= SessionThreadModel.endpoint_id == endpoint_id
    if coordination_uuid is not None:
        the_filters &= SessionThreadModel.coordination_uuid == coordination_uuid
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "thread_uuid",
    },
    range_key_required=True,
    model_funct=get_session_thread,
    count_funct=get_session_thread_count,
    type_funct=get_session_thread_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_update_session_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    session_uuid = kwargs.get("session_uuid")
    thread_uuid = kwargs.get("thread_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "agent_uuid": kwargs["agent_uuid"],
            "coordination_uuid": kwargs["coordination_uuid"],
            "endpoint_id": info.context["endpoint_id"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        SessionThreadModel(
            session_uuid,
            thread_uuid,
            **cols,
        ).save()
        return

    session_thread = kwargs.get("entity")
    actions = [
        SessionThreadModel.updated_by.set(kwargs["updated_by"]),
        SessionThreadModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to SessionThreadModel attributes
    field_map = {
        "agent_uuid": SessionThreadModel.agent_uuid,
        "coordination_uuid": SessionThreadModel.coordination_uuid,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:  # Only add to actions if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the session_thread entity
    session_thread.update(actions=actions)


@delete_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "thread_uuid",
    },
    model_funct=get_session_thread,
)
def delete_session_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
