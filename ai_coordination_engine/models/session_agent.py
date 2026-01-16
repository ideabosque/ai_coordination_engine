#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    MapAttribute,
    NumberAttribute,
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
from silvaengine_utility import method_cache
from silvaengine_utility.serializer import Serializer
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.config import Config
from ..types.session_agent import SessionAgentListType, SessionAgentType


class SessionAgentModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-session_agents"

    session_uuid = UnicodeAttribute(hash_key=True)
    session_agent_uuid = UnicodeAttribute(range_key=True)
    coordination_uuid = UnicodeAttribute()
    agent_uuid = UnicodeAttribute()
    agent_action = MapAttribute(null=True)
    user_input = UnicodeAttribute(null=True)
    agent_input = UnicodeAttribute(null=True)
    agent_output = UnicodeAttribute(null=True)
    in_degree = NumberAttribute(default=0)
    state = UnicodeAttribute(default="initial")
    notes = UnicodeAttribute(null=True)
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
                    entity_keys["session_agent_uuid"] = getattr(
                        entity, "session_agent_uuid", None
                    )
                    entity_keys["session_uuid"] = getattr(entity, "session_uuid", None)

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("session_agent_uuid"):
                    entity_keys["session_agent_uuid"] = kwargs.get("session_agent_uuid")
                    entity_keys["session_uuid"] = kwargs.get("session_uuid")

                # Only purge if we have the required keys
                if entity_keys.get("session_agent_uuid") and entity_keys.get(
                    "session_uuid"
                ):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="session_agent",
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


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "session_agent"),
    cache_enabled=Config.is_cache_enabled,
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
    """
    Get SessionAgentType from SessionAgentModel without embedding nested objects.

    Nested objects (session) are now handled by GraphQL nested resolvers
    with batch loading for optimal performance.

    Args:
        info: GraphQL resolve info (kept for signature compatibility)
        session_agent: SessionAgentModel instance

    Returns:
        SessionAgentType with foreign keys intact for lazy loading via nested resolvers
    """
    _ = info  # Keep for signature compatibility with decorators
    session_agent_dict = session_agent.__dict__["attribute_values"].copy()
    # Keep all fields including FKs - nested resolvers will handle lazy loading
    return SessionAgentType(**Serializer.json_normalize(session_agent_dict))


def resolve_session_agent(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentType | None:
    count = get_session_agent_count(
        kwargs["session_uuid"], kwargs["session_agent_uuid"]
    )
    if count == 0:
        return None

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
def resolve_session_agent_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    session_uuid = kwargs.get("session_uuid")
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_uuid = kwargs.get("agent_uuid")
    primary_path = kwargs.get("primary_path")
    user_in_the_loop = kwargs.get("user_in_the_loop")
    predecessor = kwargs.get("predecessor")
    predecessors = kwargs.get("predecessors")
    in_degree = kwargs.get("in_degree")
    states = kwargs.get("states")

    args = []
    inquiry_funct = SessionAgentModel.scan
    count_funct = SessionAgentModel.count
    if session_uuid:
        args = [session_uuid, None]
        inquiry_funct = SessionAgentModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_uuid is not None:
        the_filters &= SessionAgentModel.coordination_uuid == coordination_uuid
    if agent_uuid is not None:
        the_filters &= SessionAgentModel.agent_uuid == agent_uuid
    if primary_path is not None:
        the_filters &= SessionAgentModel.agent_action["primary_path"] == primary_path
    if user_in_the_loop is not None:
        the_filters &= (
            SessionAgentModel.agent_action["user_in_the_loop"] == user_in_the_loop
        )
    if predecessor is not None:
        the_filters &= SessionAgentModel.agent_action["predecessors"].contains(
            predecessor
        )
    if predecessors is not None:
        the_filters &= SessionAgentModel.agent_uuid.is_in(*predecessors)
    if in_degree is not None:
        the_filters &= SessionAgentModel.in_degree == in_degree
    if states is not None:
        the_filters &= SessionAgentModel.state.is_in(*states)
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
@purge_cache()
def insert_update_session_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    session_uuid = kwargs.get("session_uuid")
    session_agent_uuid = kwargs.get("session_agent_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "agent_uuid": kwargs["agent_uuid"],
            "agent_action": {
                "primary_path": True,
                "user_in_the_loop": None,
                "predecessors": [],
                "action_function": {},
            },
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "agent_action",
            "user_input",
            "agent_input",
            "agent_output",
            "in_degree",
            "state",
            "notes",
        ]:
            if key in kwargs:
                if key == "agent_action":
                    cols[key] = dict(cols[key], **kwargs[key])
                    continue
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
        "agent_action": SessionAgentModel.agent_action,
        "user_input": SessionAgentModel.user_input,
        "agent_input": SessionAgentModel.agent_input,
        "agent_output": SessionAgentModel.agent_output,
        "in_degree": SessionAgentModel.in_degree,
        "state": SessionAgentModel.state,
        "notes": SessionAgentModel.notes,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:
            value = kwargs[key]
            if key == "agent_action":
                value = dict(actions.__dict__["attribute_values"], **value)

            actions.append(field.set(value))

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
@purge_cache()
def delete_session_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
