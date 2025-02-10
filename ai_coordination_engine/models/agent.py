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

from ..types.agent import AgentListType, AgentType
from .utils import _get_coordination


class AgentNameIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "agent_name-index"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    agent_name = UnicodeAttribute(range_key=True)


class AgentModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-agents"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    agent_version_uuid = UnicodeAttribute(range_key=True)
    agent_name = UnicodeAttribute()
    agent_instructions = UnicodeAttribute(null=True)
    endpoint_id = UnicodeAttribute()
    response_format = UnicodeAttribute(null=True)
    json_schema = MapAttribute(null=True)
    tools = ListAttribute(null=True)
    predecessor = UnicodeAttribute(null=True)
    successor = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="active")
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    agent_name_index = AgentNameIndex()


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_agent(coordination_uuid: str, agent_version_uuid: str) -> AgentModel:
    return AgentModel.get(coordination_uuid, agent_version_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def _get_active_agent(coordination_uuid: str, agent_name: str) -> AgentModel:
    try:
        results = AgentModel.agent_name_index.query(
            coordination_uuid,
            AgentModel.agent_name == agent_name,
            filter_condition=(AgentModel.status == "active"),
            scan_index_forward=False,
            limit=1,
        )
        agent = results.next()

        return agent
    except StopIteration:
        return None


def get_agent_count(coordination_uuid: str, agent_version_uuid: str) -> int:
    return AgentModel.count(
        coordination_uuid, AgentModel.agent_version_uuid == agent_version_uuid
    )


def get_agent_type(info: ResolveInfo, agent: AgentModel) -> AgentType:
    try:
        coordination = _get_coordination(agent.endpoint_id, agent.coordination_uuid)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    agent = agent.__dict__["attribute_values"]
    agent["coordination"] = coordination
    agent.pop("endpoint_id")
    agent.pop("coordination_uuid")
    return AgentType(**Utility.json_loads(Utility.json_dumps(agent)))


def resolve_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType:
    if "agent_name" in kwargs:
        return get_agent_type(
            info, _get_active_agent(kwargs["coordination_uuid"], kwargs["agent_name"])
        )

    return get_agent_type(
        info,
        get_agent(kwargs["coordination_uuid"], kwargs["agent_version_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_uuid", "agent_version_uuid"],
    list_type_class=AgentListType,
    type_funct=get_agent_type,
)
def resolve_agent_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_name = kwargs.get("agent_name")
    endpoint_id = info.context["endpoint_id"]
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
    if endpoint_id is not None:
        the_filters &= AgentModel.endpoint_id == endpoint_id
    if response_format is not None:
        the_filters &= AgentModel.response_format == response_format
    if predecessor is not None:
        the_filters &= AgentModel.predecessor == predecessor
    if successor is not None:
        the_filters &= AgentModel.successor == successor
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


def _inactivate_agents(
    info: ResolveInfo, coordination_uuid: str, agent_name: str
) -> None:
    try:
        # Query for active agents matching the type and ID
        agents = AgentModel.agent_name_index.query(
            coordination_uuid,
            AgentModel.agent_name == agent_name,
            filter_condition=AgentModel.status == "active",
        )
        # Update status to inactive for each matching agent
        for agent in agents:
            agent.status = "inactive"
            agent.save()
        return
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e


@insert_update_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "agent_version_uuid",
    },
    model_funct=get_agent,
    count_funct=get_agent_count,
    type_funct=get_agent_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_version_uuid = kwargs.get("agent_version_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "agent_name": kwargs["agent_name"],
            "endpoint_id": info.context["endpoint_id"],
            "status": "active",
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }

        # Handle an existing agent if an ID is provided
        active_agent = None
        if "agent_name" in kwargs:
            active_agent = _get_active_agent(coordination_uuid, kwargs["agent_name"])

            if active_agent:
                # Retain configuration and functions, then deactivate previous versions
                cols.update(
                    {
                        k: v
                        for k, v in active_agent.__dict__["attribute_values"].items()
                        if k
                        not in [
                            "agent_name",
                            "endpoint_id",
                            "status",
                            "updated_by",
                            "created_at",
                            "updated_at",
                        ]
                    }
                )
                _inactivate_agents(info, coordination_uuid, kwargs["agent_name"])

        for key in [
            "agent_instructions",
            "response_format",
            "json_schema",
            "tools",
            "predecessor",
            "successor",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]

        AgentModel(
            coordination_uuid,
            agent_version_uuid,
            **cols,
        ).save()
        return

    agent = kwargs.get("entity")
    actions = [
        AgentModel.updated_by.set(kwargs["updated_by"]),
        AgentModel.updated_at.set(pendulum.now("UTC")),
    ]

    if "status" in kwargs and (
        kwargs["status"] == "active" and agent.status == "inactive"
    ):
        _inactivate_agents(info, coordination_uuid, agent.agent_name)

    # Map of kwargs keys to AgentModel attributes
    field_map = {
        "agent_instructions": AgentModel.agent_instructions,
        "response_format": AgentModel.response_format,
        "json_schema": AgentModel.json_schema,
        "tools": AgentModel.tools,
        "predecessor": AgentModel.predecessor,
        "successor": AgentModel.successor,
        "status": AgentModel.status,
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
        "range_key": "agent_version_uuid",
    },
    model_funct=get_agent,
)
def delete_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    if kwargs["entity"].status == "active":
        results = AgentModel.agent_name_index.query(
            kwargs["entity"].coordination_uuid,
            AgentModel.agent_name == kwargs["entity"].agent_name,
            filter_condition=(AgentModel.status == "inactive"),
        )
        agents = [result for result in results]
        if len(agents) > 0:
            agents = sorted(agents, key=lambda x: x.updated_at, reverse=True)
            last_updated_record = agents[0]
            last_updated_record.status = "active"
            last_updated_record.save()

    kwargs["entity"].delete()

    return True
