#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    BooleanAttribute,
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

from ..types.session_agent import SessionAgentListType, SessionAgentType
from .utils import _get_task_session


class SessionAgentModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-session_agents"

    session_uuid = UnicodeAttribute(hash_key=True)
    session_agent_uuid = UnicodeAttribute(range_key=True)
    thread_id = UnicodeAttribute(null=True)
    task_uuid = UnicodeAttribute()
    agent_name = UnicodeAttribute()
    user_in_the_loop = UnicodeAttribute(null=True)
    user_input = UnicodeAttribute(null=True)
    action_rules = ListAttribute(of=MapAttribute, default={})
    agent_input = UnicodeAttribute(null=True)
    agent_output = UnicodeAttribute(null=True)
    predecessor = UnicodeAttribute(null=True)
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
def get_session_agent(session_uuid: str, session_agent_uuid: str) -> SessionAgentModel:
    return SessionAgentModel.get(session_uuid, session_agent_uuid)


def get_session_agent_count(session_uuid: str, session_agent_uuid: str) -> int:
    return SessionAgentModel.count(
        session_uuid,
        SessionAgentModel.session_agent_uuid == session_agent_uuid,
    )


def get_session_agent_type(
    info: ResolveInfo, session_agent: SessionAgentModel
) -> SessionAgentType:
    try:
        task_session = _get_task_session(
            session_agent.task_uuid, session_agent.session_uuid
        )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    session_agent = session_agent.__dict__["attribute_values"]
    session_agent["task_session"] = task_session
    session_agent.pop("task_uuid")
    session_agent.pop("session_uuid")
    return SessionAgentType(**Utility.json_loads(Utility.json_dumps(session_agent)))


def resolve_session_agent(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentType:
    return get_session_agent_type(
        info,
        get_session_agent(kwargs["session_uuid"], kwargs["session_agent_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["session_uuid", "session_agent_uuid"],
    list_type_class=SessionAgentListType,
    type_funct=get_session_agent_type,
)
def resolve_session_agent_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentListType:
    session_uuid = kwargs.get("session_uuid")
    thread_id = kwargs.get("thread_id")
    task_uuid = kwargs.get("task_uuid")
    agent_name = kwargs.get("agent_name")
    user_in_the_loop = kwargs.get("user_in_the_loop")
    predecessor = kwargs.get("predecessor")
    in_degree = kwargs.get("in_degree")
    states = kwargs.get("states")

    args = []
    inquiry_funct = SessionAgentModel.scan
    count_funct = SessionAgentModel.count
    if session_uuid:
        args = [session_uuid, None]
        inquiry_funct = SessionAgentModel.query

    the_filters = None  # We can add filters for the query.
    if thread_id is not None:
        the_filters &= SessionAgentModel.thread_id == thread_id
    if task_uuid is not None:
        the_filters &= SessionAgentModel.task_uuid == task_uuid
    if agent_name is not None:
        the_filters &= SessionAgentModel.agent_name == agent_name
    if user_in_the_loop is not None:
        the_filters &= SessionAgentModel.user_in_the_loop == user_in_the_loop
    if predecessor is not None:
        the_filters &= SessionAgentModel.predecessor == predecessor
    if in_degree is not None:
        the_filters &= SessionAgentModel.in_degree == in_degree
    if states is not None:
        the_filters &= SessionAgentModel.state.is_in(states)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "session_agent_uuid",
    },
    model_funct=get_session_agent,
    count_funct=get_session_agent_count,
    type_funct=get_session_agent_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_session_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    session_uuid = kwargs.get("session_uuid")
    session_agent_uuid = kwargs.get("session_agent_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "task_uuid": kwargs["task_uuid"],
            "agent_name": kwargs["agent_name"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "thread_id",
            "user_in_the_loop",
            "user_input",
            "action_rules",
            "agent_input",
            "agent_output",
            "predecessor",
            "in_degree",
            "state",
            "notes",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]
        SessionAgentModel(
            session_uuid,
            session_agent_uuid,
            **cols,
        ).save()
        return

    session_agent = kwargs.get("entity")
    actions = [
        SessionAgentModel.updated_by.set(kwargs["updated_by"]),
        SessionAgentModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to SessionAgentModel attributes
    field_map = {
        "thread_id": SessionAgentModel.thread_id,
        "user_in_the_loop": SessionAgentModel.user_in_the_loop,
        "user_input": SessionAgentModel.user_input,
        "action_rules": SessionAgentModel.action_rules,
        "agent_input": SessionAgentModel.agent_input,
        "agent_output": SessionAgentModel.agent_output,
        "predecessor": SessionAgentModel.predecessor,
        "in_degree": SessionAgentModel.in_degree,
        "state": SessionAgentModel.state,
        "notes": SessionAgentModel.notes,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(kwargs[key]))

    # Update the session_agent entity
    session_agent.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "session_agent_uuid",
    },
    model_funct=get_session_agent,
)
def delete_session_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
