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

from ..types.agent import AgentListType, AgentType
from .utils import _get_coordination


class AgentModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-agents"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    agent_uuid = UnicodeAttribute(range_key=True)
    agent_name = UnicodeAttribute()
    agent_instructions = UnicodeAttribute(null=True)
    coordination_type = UnicodeAttribute()
    response_format = UnicodeAttribute(null=True)
    json_schema = MapAttribute(null=True)
    tools = ListAttribute(null=True)
    predecessor = UnicodeAttribute(null=True)
    successor = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_agent(coordination_uuid: str, agent_uuid: str) -> AgentModel:
    return AgentModel.get(coordination_uuid, agent_uuid)


def get_agent_count(coordination_uuid: str, agent_uuid: str) -> int:
    return AgentModel.count(coordination_uuid, AgentModel.agent_uuid == agent_uuid)


def get_agent_type(info: ResolveInfo, agent: AgentModel) -> AgentType:
    try:
        coordination = _get_coordination(
            agent.coordination_type, agent.coordination_uuid
        )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    agent = agent.__dict__["attribute_values"]
    agent["coordination"] = coordination
    agent.pop("coordination_type")
    agent.pop("coordination_uuid")
    return AgentType(**Utility.json_loads(Utility.json_dumps(agent)))


def resolve_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType:
    return get_agent_type(
        info,
        get_agent(kwargs["coordination_uuid"], kwargs["agent_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_uuid", "agent_uuid"],
    list_type_class=AgentListType,
    type_funct=get_agent_type,
)
def resolve_agent_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_name = kwargs.get("agent_name")
    coordination_types = kwargs.get("coordination_types")
    response_format = kwargs.get("response_format")
    predecessor = kwargs.get("predecessor")
    successor = kwargs.get("successor")

    args = []
    inquiry_funct = AgentModel.scan
    count_funct = AgentModel.count
    if coordination_uuid:
        args = [coordination_uuid, None]
        inquiry_funct = AgentModel.query

    the_filters = None  # We can add filters for the query.
    if agent_name is not None:
        the_filters &= AgentModel.agent_name.contains(agent_name)
    if coordination_types is not None:
        the_filters &= AgentModel.coordination_type.is_in(*coordination_types)
    if response_format is not None:
        the_filters &= AgentModel.response_format == response_format
    if predecessor is not None:
        the_filters &= AgentModel.predecessor == predecessor
    if successor is not None:
        the_filters &= AgentModel.successor == successor
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "agent_uuid",
    },
    model_funct=get_agent,
    count_funct=get_agent_count,
    type_funct=get_agent_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_uuid = kwargs.get("agent_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "agent_name": kwargs["agent_name"],
            "coordination_type": kwargs["coordination_type"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if kwargs.get("agent_instructions") is not None:
            cols["agent_instructions"] = kwargs["agent_instructions"]
        if kwargs.get("response_format") is not None:
            cols["response_format"] = kwargs["response_format"]
        if kwargs.get("json_schema") is not None:
            cols["json_schema"] = kwargs["json_schema"]
        if kwargs.get("tools") is not None:
            cols["tools"] = kwargs["tools"]
        if kwargs.get("predecessor") is not None:
            cols["predecessor"] = kwargs["predecessor"]
        if kwargs.get("successor") is not None:
            cols["successor"] = kwargs["successor"]
        AgentModel(
            coordination_uuid,
            agent_uuid,
            **cols,
        ).save()
        return

    agent = kwargs.get("entity")
    actions = [
        AgentModel.updated_by.set(kwargs["updated_by"]),
        AgentModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of kwargs keys to AgentModel attributes
    field_map = {
        "agent_name": AgentModel.agent_name,
        "coordination_type": AgentModel.coordination_type,
        "agent_instructions": AgentModel.agent_instructions,
        "response_format": AgentModel.response_format,
        "json_schema": AgentModel.json_schema,
        "tools": AgentModel.tools,
        "predecessor": AgentModel.predecessor,
        "successor": AgentModel.successor,
    }

    # Build actions dynamically based on the presence of keys in kwargs
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the agent
    agent.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "agent_uuid",
    },
    model_funct=get_agent,
)
def delete_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
