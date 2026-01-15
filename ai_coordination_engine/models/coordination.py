#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"


import functools
import logging
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
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Debugger, method_cache
from silvaengine_utility.serializer import Serializer
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.config import Config
from ..types.coordination import CoordinationListType, CoordinationType


class CoordinationModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-coordinations"

    partition_key = UnicodeAttribute(hash_key=True)
    coordination_uuid = UnicodeAttribute(range_key=True)
    endpoint_id = UnicodeAttribute()
    part_id = UnicodeAttribute()
    coordination_name = UnicodeAttribute()
    coordination_description = UnicodeAttribute()
    agents = ListAttribute(of=MapAttribute)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Execute original function first
                result = original_function(*args, **kwargs)

                # Then purge cache after successful operation
                from ..models.cache import purge_entity_cascading_cache

                # Get entity keys from kwargs or entity parameter
                entity_keys = {}

                # Try to get from entity parameter first (for updates)
                entity = kwargs.get("entity")
                if entity:
                    entity_keys["coordination_uuid"] = getattr(
                        entity, "coordination_uuid", None
                    )
                    entity_keys["partition_key"] = getattr(
                        entity, "partition_key", None
                    )

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("coordination_uuid"):
                    entity_keys["coordination_uuid"] = kwargs.get("coordination_uuid")
                    entity_keys["partition_key"] = kwargs.get("partition_key")

                # Only purge if we have the required keys
                if entity_keys.get("coordination_uuid") and entity_keys.get(
                    "partition_key"
                ):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="coordination",
                        context_keys=None,
                        entity_keys=entity_keys,
                        cascade_depth=3,
                    )

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


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
# @method_cache(
#     ttl=Config.get_cache_ttl(),
#     cache_name=Config.get_cache_name("models", "coordination"),
# )
def get_coordination(partition_key: str, coordination_uuid: str) -> CoordinationModel:
    return CoordinationModel.get(partition_key, coordination_uuid)


def get_coordination_count(partition_key: str, coordination_uuid: str) -> int:
    return CoordinationModel.count(
        partition_key, CoordinationModel.coordination_uuid == coordination_uuid
    )


def get_coordination_type(
    info: ResolveInfo, coordination: CoordinationModel
) -> CoordinationType:
    _ = info  # Keep for signature compatibility with decorators
    coordination_dict = coordination.__dict__["attribute_values"].copy()
    # Keep all fields including FKs - nested resolvers will handle lazy loading
    return CoordinationType(**Serializer.json_normalize(coordination_dict))


def resolve_coordination(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> CoordinationType | None:
    partition_key = info.context.get("partition_key") or info.context.get("endpoint_id")
    count = get_coordination_count(partition_key, kwargs["coordination_uuid"])

    if count == 0:
        return None

    return get_coordination_type(
        info,
        get_coordination(partition_key, kwargs["coordination_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "coordination_uuid"],
    list_type_class=CoordinationListType,
    type_funct=get_coordination_type,
)
def resolve_coordination_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = info.context.get("partition_key")
    coordination_name = kwargs.get("coordination_name")
    coordination_description = kwargs.get("coordination_description")
    args = []
    inquiry_funct = CoordinationModel.scan
    count_funct = CoordinationModel.count
    if partition_key:
        args = [partition_key, None]
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
        "hash_key": "partition_key",
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
    count_funct=get_coordination_count,
    type_funct=get_coordination_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
@purge_cache()
def insert_update_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    partition_key = kwargs.get("partition_key")
    coordination_uuid = kwargs.get("coordination_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "endpoint_id": info.context.get("endpoint_id"),
            "part_id": info.context.get("part_id"),
            "agents": [],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "coordination_name",
            "coordination_description",
            "agents",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]

        CoordinationModel(
            partition_key,
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
        "hash_key": "partition_key",
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
)
@purge_cache()
def delete_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
