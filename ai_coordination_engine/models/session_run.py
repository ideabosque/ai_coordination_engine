#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import method_cache
from ..utils.normalization import normalize_to_json
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.config import Config
from ..types.session_run import SessionRunListType, SessionRunType


class ThreadUuidIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "thread_uuid-index"

    session_uuid = UnicodeAttribute(hash_key=True)
    thread_uuid = UnicodeAttribute(range_key=True)


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


class SessionRunModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-session_runs"

    session_uuid = UnicodeAttribute(hash_key=True)
    run_uuid = UnicodeAttribute(range_key=True)
    thread_uuid = UnicodeAttribute()
    agent_uuid = UnicodeAttribute()
    coordination_uuid = UnicodeAttribute()
    partition_key = UnicodeAttribute(null=True)
    async_task_uuid = UnicodeAttribute()
    session_agent_uuid = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    agent_uuid_index = AgentUuidIndex()
    thread_uuid_index = ThreadUuidIndex()


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
                    entity_keys["run_uuid"] = getattr(entity, "run_uuid", None)
                    entity_keys["session_uuid"] = getattr(entity, "session_uuid", None)

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("run_uuid"):
                    entity_keys["run_uuid"] = kwargs.get("run_uuid")
                    entity_keys["session_uuid"] = kwargs.get("session_uuid")

                # Only purge if we have the required keys
                if entity_keys.get("run_uuid") and entity_keys.get("session_uuid"):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="session_run",
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
    cache_name=Config.get_cache_name("models", "session_run"),
    cache_enabled=Config.is_cache_enabled,
)
def get_session_run(session_uuid: str, run_uuid: str) -> SessionRunModel:
    return SessionRunModel.get(session_uuid, run_uuid)


def get_session_run_count(session_uuid: str, run_uuid: str) -> int:
    return SessionRunModel.count(session_uuid, SessionRunModel.run_uuid == run_uuid)


def get_session_run_type(
    info: ResolveInfo, session_run: SessionRunModel
) -> SessionRunType:
    """
    Get SessionRunType from SessionRunModel without embedding nested objects.

    Nested objects (session, session_agent) are now handled by GraphQL nested resolvers
    with batch loading for optimal performance.

    Args:
        info: GraphQL resolve info
        session_run: SessionRunModel instance

    Returns:
        SessionRunType with foreign keys intact for lazy loading via nested resolvers
    """
    _ = info  # Keep for signature compatibility with decorators
    session_run_dict = session_run.__dict__["attribute_values"].copy()
    return SessionRunType(**normalize_to_json(session_run_dict))


def resolve_session_run(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionRunType | None:
    count = get_session_run_count(kwargs["session_uuid"], kwargs["run_uuid"])
    if count == 0:
        return None

    return get_session_run_type(
        info,
        get_session_run(kwargs["session_uuid"], kwargs["run_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["session_uuid", "run_uuid", "agent_uuid", "thread_uuid"],
    list_type_class=SessionRunListType,
    type_funct=get_session_run_type,
)
def resolve_session_run_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    session_uuid = kwargs.get("session_uuid")
    partition_key = info.context["partition_key"]
    agent_uuid = kwargs.get("agent_uuid")
    thread_uuid = kwargs.get("thread_uuid")
    coordination_uuid = kwargs.get("coordination_uuid")
    args = []
    inquiry_funct = SessionRunModel.scan
    count_funct = SessionRunModel.count
    if session_uuid:
        args = [session_uuid, None]
        inquiry_funct = SessionRunModel.query
        if agent_uuid:
            inquiry_funct = SessionRunModel.agent_uuid_index.query
            args[1] = SessionRunModel.agent_uuid == agent_uuid
            count_funct = SessionRunModel.agent_uuid_index.count
        if thread_uuid:
            inquiry_funct = SessionRunModel.thread_uuid_index.query
            args[1] = SessionRunModel.thread_uuid == thread_uuid
            count_funct = SessionRunModel.thread_uuid_index.count

    the_filters = None  # We can add filters for the query.
    if partition_key is not None:
        the_filters &= SessionRunModel.partition_key == partition_key
    if coordination_uuid is not None:
        the_filters &= SessionRunModel.coordination_uuid == coordination_uuid
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "run_uuid",
    },
    range_key_required=True,
    model_funct=get_session_run,
    count_funct=get_session_run_count,
    type_funct=get_session_run_type,
)
@purge_cache()
def insert_update_session_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    session_uuid = kwargs.get("session_uuid")
    run_uuid = kwargs.get("run_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "thread_uuid": kwargs["thread_uuid"],
            "agent_uuid": kwargs["agent_uuid"],
            "coordination_uuid": kwargs["coordination_uuid"],
            "partition_key": info.context.get("partition_key"),
            "async_task_uuid": kwargs["async_task_uuid"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in ["session_agent_uuid"]:
            if key in kwargs:
                cols[key] = kwargs[key]

        SessionRunModel(
            session_uuid,
            run_uuid,
            **cols,
        ).save()
        return

    session_run = kwargs.get("entity")
    actions = [
        SessionRunModel.updated_by.set(kwargs["updated_by"]),
        SessionRunModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to SessionRunModel attributes
    field_map = {
        "thread_uuid": SessionRunModel.thread_uuid,
        "agent_uuid": SessionRunModel.agent_uuid,
        "coordination_uuid": SessionRunModel.coordination_uuid,
        "async_task_uuid": SessionRunModel.async_task_uuid,
        "session_agent_uuid": SessionRunModel.session_agent_uuid,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:  # Only add to actions if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the session_run entity
    session_run.update(actions=actions)


@delete_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "run_uuid",
    },
    model_funct=get_session_run,
)
@purge_cache()
def delete_session_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
