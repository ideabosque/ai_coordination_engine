#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"


import logging
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import MapAttribute, UnicodeAttribute, UTCDateTimeAttribute
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility

from ..types.coordination import CoordinationListType, CoordinationType


class CoordinationModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-coordinations"

    endpoint_id = UnicodeAttribute(hash_key=True)
    coordination_uuid = UnicodeAttribute(range_key=True)
    coordination_name = UnicodeAttribute()
    coordination_description = UnicodeAttribute()
    agents = MapAttribute(default={})
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


def create_coordination_table(logger: logging.Logger) -> bool:
    """Create the Coordination table if it doesn't exist."""
    if not CoordinationModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        CoordinationModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Coordination table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_coordination(endpoint_id: str, coordination_uuid: str) -> CoordinationModel:
    return CoordinationModel.get(endpoint_id, coordination_uuid)


def get_coordination_count(endpoint_id: str, coordination_uuid: str) -> int:
    return CoordinationModel.count(
        endpoint_id, CoordinationModel.coordination_uuid == coordination_uuid
    )


def get_coordination_type(
    info: ResolveInfo, coordination: CoordinationModel
) -> CoordinationType:
    coordination = coordination.__dict__["attribute_values"]
    return CoordinationType(**Utility.json_loads(Utility.json_dumps(coordination)))


def resolve_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    return get_coordination_type(
        info,
        get_coordination(info.context["endpoint_id"], kwargs["coordination_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "coordination_uuid"],
    list_type_class=CoordinationListType,
    type_funct=get_coordination_type,
)
def resolve_coordination_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    coordination_name = kwargs.get("coordination_name")
    coordination_description = kwargs.get("coordination_description")
    args = []
    inquiry_funct = CoordinationModel.scan
    count_funct = CoordinationModel.count
    if endpoint_id:
        args = [endpoint_id, None]
        inquiry_funct = CoordinationModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_name is not None:
        the_filters &= CoordinationModel.coordination_name.contains(coordination_name)
    if coordination_description is not None:
        the_filters &= CoordinationModel.coordination_description.contains(
            coordination_description
        )
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
    count_funct=get_coordination_count,
    type_funct=get_coordination_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    endpoint_id = kwargs.get("endpoint_id")
    coordination_uuid = kwargs.get("coordination_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_name": kwargs["coordination_name"],
            "coordination_description": kwargs["coordination_description"],
            "agents": kwargs["agents"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if "additional_instructions" in kwargs:
            cols["additional_instructions"] = kwargs["additional_instructions"]
        CoordinationModel(
            endpoint_id,
            coordination_uuid,
            **cols,
        ).save()
        return

    coordination = kwargs.get("entity")
    actions = [
        CoordinationModel.updated_by.set(kwargs["updated_by"]),
        CoordinationModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to CoordinationModel attributes
    field_map = {
        "coordination_name": CoordinationModel.coordination_name,
        "coordination_description": CoordinationModel.coordination_description,
        "agents": CoordinationModel.agents,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:  # Only add to actions if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the coordination entity
    coordination.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
)
def delete_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
