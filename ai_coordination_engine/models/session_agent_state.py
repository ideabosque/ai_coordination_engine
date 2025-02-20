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

from ..types.session_agent_state import SessionAgentStateListType, SessionAgentStateType
from .utils import _get_task_session


class SessionAgentStateModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-session_agent_states"

    session_uuid = UnicodeAttribute(hash_key=True)
    session_agent_state_uuid = UnicodeAttribute(range_key=True)
    thread_id = UnicodeAttribute()
    task_uuid = UnicodeAttribute()
    agent_name = UnicodeAttribute()
    user_in_the_loop = UnicodeAttribute(null=True)
    user_action = UnicodeAttribute(null=True)
    agent_input = UnicodeAttribute(null=True)
    agent_output = UnicodeAttribute(null=True)
    predecessors = ListAttribute(of=UnicodeAttribute, default=[])
    in_degree = NumberAttribute(default=0)
    state = UnicodeAttribute(default="initial")
    notes = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_session_agent_state(
    session_uuid: str, session_agent_state_uuid: str
) -> SessionAgentStateModel:
    return SessionAgentStateModel.get(session_uuid, session_agent_state_uuid)


def get_session_agent_state_count(
    session_uuid: str, session_agent_state_uuid: str
) -> int:
    return SessionAgentStateModel.count(
        session_uuid,
        SessionAgentStateModel.session_agent_state_uuid == session_agent_state_uuid,
    )


def get_session_agent_state_type(
    info: ResolveInfo, session_agent_state: SessionAgentStateModel
) -> SessionAgentStateType:
    try:
        task_session = _get_task_session(
            session_agent_state.task_uuid, session_agent_state.session_uuid
        )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    session_agent_state = session_agent_state.__dict__["attribute_values"]
    session_agent_state["task_session"] = task_session
    session_agent_state.pop("task_uuid")
    session_agent_state.pop("session_uuid")
    return SessionAgentStateType(
        **Utility.json_loads(Utility.json_dumps(session_agent_state))
    )


def resolve_session_agent_state(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentStateType:
    return get_session_agent_state_type(
        info,
        get_session_agent_state(
            kwargs["session_uuid"], kwargs["session_agent_state_uuid"]
        ),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["session_uuid", "session_agent_state_uuid"],
    list_type_class=SessionAgentStateListType,
    type_funct=get_session_agent_state_type,
)
def resolve_session_agent_state_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentStateListType:
    session_uuid = kwargs.get("session_uuid")
    thread_id = kwargs.get("thread_id")
    task_uuid = kwargs.get("task_uuid")
    agent_name = kwargs.get("agent_name")
    user_in_the_loop = kwargs.get("user_in_the_loop")
    in_degree = kwargs.get("in_degree")
    states = kwargs.get("states")

    args = []
    inquiry_funct = SessionAgentStateModel.scan
    count_funct = SessionAgentStateModel.count
    if session_uuid:
        args = [session_uuid, None]
        inquiry_funct = SessionAgentStateModel.query

    the_filters = None  # We can add filters for the query.
    if thread_id is not None:
        the_filters &= SessionAgentStateModel.thread_id == thread_id
    if task_uuid is not None:
        the_filters &= SessionAgentStateModel.task_uuid == task_uuid
    if agent_name is not None:
        the_filters &= SessionAgentStateModel.agent_name == agent_name
    if user_in_the_loop is not None:
        the_filters &= SessionAgentStateModel.user_in_the_loop == user_in_the_loop
    if in_degree is not None:
        the_filters &= SessionAgentStateModel.in_degree == in_degree
    if states is not None:
        the_filters &= SessionAgentStateModel.state.is_in(states)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "session_agent_state_uuid",
    },
    model_funct=get_session_agent_state,
    count_funct=get_session_agent_state_count,
    type_funct=get_session_agent_state_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_session_agent_state(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> None:
    session_uuid = kwargs.get("session_uuid")
    session_agent_state_uuid = kwargs.get("session_agent_state_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "thread_id": kwargs["thread_id"],
            "task_uuid": kwargs["task_uuid"],
            "agent_name": kwargs["agent_name"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "user_in_the_loop",
            "user_action",
            "agent_input",
            "agent_output",
            "predecessors",
            "in_degree",
            "state",
            "notes",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]
        SessionAgentStateModel(
            session_uuid,
            session_agent_state_uuid,
            **cols,
        ).save()
        return

    session_agent_state = kwargs.get("entity")
    actions = [
        SessionAgentStateModel.updated_by.set(kwargs["updated_by"]),
        SessionAgentStateModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to SessionAgentStateModel attributes
    field_map = {
        "user_in_the_loop": SessionAgentStateModel.user_in_the_loop,
        "user_action": SessionAgentStateModel.user_action,
        "agent_input": SessionAgentStateModel.agent_input,
        "agent_output": SessionAgentStateModel.agent_output,
        "predecessors": SessionAgentStateModel.predecessors,
        "in_degree": SessionAgentStateModel.in_degree,
        "state": SessionAgentStateModel.state,
        "notes": SessionAgentStateModel.notes,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(kwargs[key]))

    # Update the session_agent_state entity
    session_agent_state.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "session_agent_state_uuid",
    },
    model_funct=get_session_agent_state,
)
def delete_session_agent_state(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
