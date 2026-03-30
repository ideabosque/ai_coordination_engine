#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

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
from ..utils.normalization import normalize_to_json
from tenacity import retry, stop_after_attempt, wait_exponential

from ..constants import SessionAgentState
from ..handlers.config import Config
from ..types.session_agent import SessionAgentListType, SessionAgentType
from .decorators import cache_purger_session_agent


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
    state = UnicodeAttribute(default=SessionAgentState.INITIAL.value)
    notes = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


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
    return SessionAgentType(**normalize_to_json(session_agent_dict))


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
        args = [session_uuid]
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
@cache_purger_session_agent
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
@cache_purger_session_agent
def delete_session_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True


def batch_insert_session_agents(
    info: ResolveInfo, agents_data: List[Dict[str, Any]]
) -> List[SessionAgentType]:
    """Batch create session agents using DynamoDB batch write.
    
    This function provides optimized batch creation of session agents,
    reducing the number of DynamoDB write operations from N individual
    writes to a single batch write operation.
    
    Args:
        info: GraphQL resolve info containing context
        agents_data: List of dictionaries containing session agent data
            Each dict should contain:
            - session_uuid: UUID of the session
            - session_agent_uuid: UUID for the new session agent
            - coordination_uuid: UUID of the coordination
            - agent_uuid: UUID of the agent
            - agent_action: Agent action configuration
            - updated_by: User who initiated the update
            
    Returns:
        List of created SessionAgentType objects
    """
    import uuid
    from ..handlers.config_manager import get_performance_config
    
    logger = info.context.get("logger")
    config = get_performance_config()
    
    if not agents_data:
        return []
    
    created_agents = []
    
    # Check if batch write is enabled
    enable_batch = config.enable_batch_session_agent_create
    
    if enable_batch:
        logger.info(
            f"Batch creating {len(agents_data)} session agents (batch mode)"
        )
        
        # Use batch write for better performance
        with SessionAgentModel.batch_write() as batch:
            for data in agents_data:
                session_agent_uuid = data.get(
                    "session_agent_uuid", str(uuid.uuid4())
                )
                
                agent = SessionAgentModel(
                    data["session_uuid"],
                    session_agent_uuid,
                    coordination_uuid=data["coordination_uuid"],
                    agent_uuid=data["agent_uuid"],
                    agent_action=data.get("agent_action", {
                        "primary_path": True,
                        "user_in_the_loop": None,
                        "predecessors": [],
                        "action_function": {},
                    }),
                    updated_by=data["updated_by"],
                    created_at=pendulum.now("UTC"),
                    updated_at=pendulum.now("UTC"),
                )
                batch.save(agent)
                created_agents.append(agent)
        
        logger.info(
            f"Successfully batch created {len(created_agents)} session agents"
        )
    else:
        # Fall back to individual inserts
        logger.info(
            f"Creating {len(agents_data)} session agents (individual mode)"
        )
        
        for data in agents_data:
            session_agent = insert_update_session_agent(info, **data)
            created_agents.append(session_agent)
    
    # Convert to SessionAgentType
    return [get_session_agent_type(info, agent) for agent in created_agents]


def batch_update_session_agents_in_degree(
    info: ResolveInfo, updates: List[Dict[str, Any]]
) -> List[SessionAgentType]:
    """Batch update in_degree for multiple session agents.
    
    This function provides optimized batch update of in_degree values,
    reducing the number of DynamoDB update operations.
    
    Args:
        info: GraphQL resolve info containing context
        updates: List of dictionaries containing update data
            Each dict should contain:
            - session_uuid: UUID of the session
            - session_agent_uuid: UUID of the session agent
            - in_degree: New in_degree value
            - updated_by: User who initiated the update
            
    Returns:
        List of updated SessionAgentType objects
    """
    from ..handlers.config_manager import get_performance_config
    
    logger = info.context.get("logger")
    config = get_performance_config()
    
    if not updates:
        return []
    
    updated_agents = []
    
    # Check if batch write is enabled
    enable_batch = config.enable_batch_session_agent_create
    
    if enable_batch:
        logger.info(
            f"Batch updating in_degree for {len(updates)} session agents"
        )
        
        # Batch update using batch_write with overwrite
        with SessionAgentModel.batch_write() as batch:
            for update_data in updates:
                session_agent = get_session_agent(
                    update_data["session_uuid"],
                    update_data["session_agent_uuid"]
                )
                
                if session_agent:
                    session_agent.in_degree = update_data["in_degree"]
                    session_agent.updated_by = update_data["updated_by"]
                    session_agent.updated_at = pendulum.now("UTC")
                    batch.save(session_agent)
                    updated_agents.append(session_agent)
        
        logger.info(
            f"Successfully batch updated {len(updated_agents)} session agents"
        )
    else:
        # Fall back to individual updates
        logger.info(
            f"Updating in_degree for {len(updates)} session agents (individual mode)"
        )
        
        for update_data in updates:
            session_agent = insert_update_session_agent(info, **update_data)
            updated_agents.append(session_agent)
    
    return [get_session_agent_type(info, agent) for agent in updated_agents]
