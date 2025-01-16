#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"


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

from ..types.coordination import CoordinationListType, CoordinationType


class CoordinationModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-coordinations"

    coordination_type = UnicodeAttribute(hash_key=True)
    coordination_uuid = UnicodeAttribute(range_key=True)
    coordination_name = UnicodeAttribute()
    coordination_description = UnicodeAttribute()
    assistant_id = UnicodeAttribute()
    assistant_type = UnicodeAttribute()
    additional_instructions = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_coordination(
    coordination_type: str, coordination_uuid: str
) -> CoordinationModel:
    return CoordinationModel.get(coordination_type, coordination_uuid)


def get_coordination_count(coordination_type: str, coordination_uuid: str) -> int:
    return CoordinationModel.count(
        coordination_type, CoordinationModel.coordination_uuid == coordination_uuid
    )


def get_coordination_type(
    info: ResolveInfo, coordination: CoordinationModel
) -> CoordinationType:
    coordination = coordination.__dict__["attribute_values"]
    return CoordinationType(**Utility.json_loads(Utility.json_dumps(coordination)))


def resolve_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    return get_coordination_type(
        info,
        get_coordination(kwargs["coordination_type"], kwargs["coordination_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_type", "coordination_uuid"],
    list_type_class=CoordinationListType,
    type_funct=get_coordination_type,
)
def resolve_coordination_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    coordination_type = kwargs.get("coordination_type")
    coordination_name = kwargs.get("coordination_name")
    coordination_description = kwargs.get("coordination_description")
    assistant_id = kwargs.get("assistant_id")
    assistant_types = kwargs.get("assistant_types")
    args = []
    inquiry_funct = CoordinationModel.scan
    count_funct = CoordinationModel.count
    if coordination_type:
        args = [coordination_type, None]
        inquiry_funct = CoordinationModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_name is not None:
        the_filters &= CoordinationModel.coordination_name.contains(coordination_name)
    if coordination_description is not None:
        the_filters &= CoordinationModel.coordination_description.contains(
            coordination_description
        )
    if assistant_id is not None:
        the_filters &= CoordinationModel.assistant_id == assistant_id
    if assistant_types is not None:
        the_filters &= CoordinationModel.assistant_type.is_in(*assistant_types)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "coordination_type",
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
    count_funct=get_coordination_count,
    type_funct=get_coordination_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    coordination_type = kwargs.get("coordination_type")
    coordination_uuid = kwargs.get("coordination_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_name": kwargs["coordination_name"],
            "coordination_description": kwargs["coordination_description"],
            "assistant_id": kwargs["assistant_id"],
            "assistant_type": kwargs["assistant_type"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if kwargs.get("additional_instructions") is not None:
            cols["additional_instructions"] = kwargs["additional_instructions"]
        CoordinationModel(
            coordination_type,
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
        "assistant_id": CoordinationModel.assistant_id,
        "assistant_type": CoordinationModel.assistant_type,
        "additional_instructions": CoordinationModel.additional_instructions,
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
        "hash_key": "coordination_type",
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
)
def delete_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
