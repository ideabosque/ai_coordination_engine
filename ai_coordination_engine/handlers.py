#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from silvaengine_dynamodb_base import (
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import (
    CoordinationAgentModel,
    CoordinationMessageModel,
    CoordinationModel,
    CoordinationSessionModel,
)
from .types import (
    CoordinationAgentListType,
    CoordinationAgentType,
    CoordinationListType,
    CoordinationMessageListType,
    CoordinationMessageType,
    CoordinationSessionListType,
    CoordinationSessionType,
    CoordinationType,
)


def handlers_init(logger: logging.Logger, **setting: Dict[str, Any]) -> None:
    try:
        pass
    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e


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


def resolve_coordination_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
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
def resolve_coordination_list_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:
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
def insert_update_coordination_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> None:
    coordination_type = kwargs.get("coordination_type")
    coordination_uuid = kwargs.get("coordination_uuid")
    if kwargs.get("entity") is None:
        CoordinationModel(
            coordination_type,
            coordination_uuid,
            **{
                "coordination_name": kwargs["coordination_name"],
                "coordination_description": kwargs["coordination_description"],
                "assistant_id": kwargs["assistant_id"],
                "assistant_type": kwargs["assistant_type"],
                "updated_by": kwargs["updated_by"],
                "created_at": pendulum.now("UTC"),
                "updated_at": pendulum.now("UTC"),
            },
        ).save()
        return

    coordination = kwargs.get("entity")
    actions = [
        CoordinationModel.updated_by.set(kwargs["updated_by"]),
        CoordinationModel.updated_at.set(pendulum.now("UTC")),
    ]
    if kwargs.get("coordination_name") is not None:
        actions.append(
            CoordinationModel.coordination_name.set(kwargs["coordination_name"])
        )
    if kwargs.get("coordination_description") is not None:
        actions.append(
            CoordinationModel.coordination_description.set(
                kwargs.get("coordination_description")
            )
        )
    if kwargs.get("assistant_id") is not None:
        actions.append(CoordinationModel.assistant_id.set(kwargs["assistant_id"]))
    if kwargs.get("assistant_type") is not None:
        actions.append(CoordinationModel.assistant_type.set(kwargs["assistant_type"]))
    coordination.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "coordination_type",
        "range_key": "coordination_uuid",
    },
    model_funct=get_coordination,
)
def delete_coordination_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_coordination_agent(
    coordination_uuid: str, agent_uuid: str
) -> CoordinationAgentModel:
    return CoordinationAgentModel.get(coordination_uuid, agent_uuid)


def get_coordination_agent_count(coordination_uuid: str, agent_uuid: str) -> int:
    return CoordinationAgentModel.count(
        coordination_uuid, CoordinationAgentModel.agent_uuid == agent_uuid
    )


def get_coordination_agent_type(
    info: ResolveInfo, coordination_agent: CoordinationAgentModel
) -> CoordinationAgentType:
    coordination_agent = coordination_agent.__dict__["attribute_values"]
    return CoordinationAgentType(
        **Utility.json_loads(Utility.json_dumps(coordination_agent))
    )


def resolve_coordination_agent_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> CoordinationAgentType:
    return get_coordination_agent_type(
        info,
        get_coordination_agent(kwargs["coordination_uuid"], kwargs["agent_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_uuid", "agent_uuid"],
    list_type_class=CoordinationAgentListType,
    type_funct=get_coordination_agent_type,
)
def resolve_coordination_agent_list_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_name = kwargs.get("agent_name")
    agent_description = kwargs.get("agent_description")
    coordination_types = kwargs.get("coordination_types")
    response_format = kwargs.get("response_format")
    predecessor = kwargs.get("predecessor")
    successor = kwargs.get("successor")

    args = []
    inquiry_funct = CoordinationAgentModel.scan
    count_funct = CoordinationAgentModel.count
    if coordination_uuid:
        args = [coordination_uuid, None]
        inquiry_funct = CoordinationAgentModel.query

    the_filters = None  # We can add filters for the query.
    if agent_name is not None:
        the_filters &= CoordinationAgentModel.agent_name.contains(agent_name)
    if agent_description is not None:
        the_filters &= CoordinationAgentModel.agent_description.contains(
            agent_description
        )
    if coordination_types is not None:
        the_filters &= CoordinationAgentModel.coordination_type.is_in(
            *coordination_types
        )
    if response_format is not None:
        the_filters &= CoordinationAgentModel.response_format == response_format
    if predecessor is not None:
        the_filters &= CoordinationAgentModel.predecessor == predecessor
    if successor is not None:
        the_filters &= CoordinationAgentModel.successor == successor
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "agent_uuid",
    },
    model_funct=get_coordination_agent,
    count_funct=get_coordination_agent_count,
    type_funct=get_coordination_agent_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_coordination_agent_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> None:
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_uuid = kwargs.get("agent_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "agent_name": kwargs["agent_name"],
            "agent_description": kwargs["agent_description"],
            "coordination_type": kwargs["coordination_type"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if kwargs.get("agent_instructions") is not None:
            cols["agent_instructions"] = kwargs["agent_instructions"]
        if kwargs.get("agent_additional_instructions") is not None:
            cols["agent_additional_instructions"] = kwargs[
                "agent_additional_instructions"
            ]
        if kwargs.get("response_format") is not None:
            cols["response_format"] = kwargs["response_format"]
        if kwargs.get("predecessor") is not None:
            cols["predecessor"] = kwargs["predecessor"]
        if kwargs.get("successor") is not None:
            cols["successor"] = kwargs["successor"]
        CoordinationAgentModel(
            coordination_uuid,
            agent_uuid,
            **cols,
        ).save()
        return

    coordination_agent = kwargs.get("entity")
    actions = [
        CoordinationAgentModel.updated_by.set(kwargs["updated_by"]),
        CoordinationAgentModel.updated_at.set(pendulum.now("UTC")),
    ]
    if kwargs.get("agent_name") is not None:
        actions.append(CoordinationAgentModel.agent_name.set(kwargs["agent_name"]))
    if kwargs.get("agent_description") is not None:
        actions.append(
            CoordinationAgentModel.agent_description.set(kwargs["agent_description"])
        )
    if kwargs.get("coordination_type") is not None:
        actions.append(
            CoordinationAgentModel.coordination_type.set(kwargs["coordination_type"])
        )
    if kwargs.get("agent_instructions") is not None:
        actions.append(
            CoordinationAgentModel.agent_instructions.set(kwargs["agent_instructions"])
        )
    if kwargs.get("agent_additional_instructions") is not None:
        actions.append(
            CoordinationAgentModel.agent_additional_instructions.set(
                kwargs["agent_additional_instructions"]
            )
        )
    if kwargs.get("response_format") is not None:
        actions.append(
            CoordinationAgentModel.response_format.set(kwargs["response_format"])
        )
    if kwargs.get("predecessor") is not None:
        actions.append(CoordinationAgentModel.predecessor.set(kwargs["predecessor"]))
    if kwargs.get("successor") is not None:
        actions.append(CoordinationAgentModel.successor.set(kwargs["successor"]))
    coordination_agent.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "agent_uuid",
    },
    model_funct=get_coordination_agent,
)
def delete_coordination_agent_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> bool:
    kwargs.get("entity").delete()
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_coordination_session(
    coordination_uuid: str, session_uuid: str
) -> CoordinationSessionModel:
    return CoordinationSessionModel.get(coordination_uuid, session_uuid)


def get_coordination_session_count(coordination_uuid: str, session_uuid: str) -> int:
    return CoordinationSessionModel.count(
        coordination_uuid, CoordinationSessionModel.session_uuid == session_uuid
    )


def get_coordination_session_type(
    info: ResolveInfo, coordination_session: CoordinationSessionModel
) -> CoordinationSessionType:
    coordination_session = coordination_session.__dict__["attribute_values"]
    return CoordinationSessionType(
        **Utility.json_loads(Utility.json_dumps(coordination_session))
    )


def resolve_coordination_session_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> CoordinationSessionType:
    return get_coordination_session_type(
        info,
        get_coordination_session(kwargs["coordination_uuid"], kwargs["session_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_uuid", "session_uuid"],
    list_type_class=CoordinationSessionListType,
    type_funct=get_coordination_session_type,
)
def resolve_coordination_session_list_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:
    coordination_uuid = kwargs.get("coordination_uuid")
    coordination_types = kwargs.get("coordination_types")
    thread_id = kwargs.get("thread_id")
    current_agent_uuid = kwargs.get("current_agent_uuid")
    statuses = kwargs.get("statuses")
    args = []
    inquiry_funct = CoordinationSessionModel.scan
    count_funct = CoordinationSessionModel.count
    if coordination_uuid:
        args = [coordination_uuid, None]
        inquiry_funct = CoordinationSessionModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_types is not None:
        the_filters &= CoordinationSessionModel.coordination_type.is_in(
            *coordination_types
        )
    if thread_id is not None:
        the_filters &= CoordinationSessionModel.thread_id == thread_id
    if current_agent_uuid is not None:
        the_filters &= CoordinationSessionModel.current_agent_uuid == current_agent_uuid
    if statuses is not None:
        the_filters &= CoordinationSessionModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "session_uuid",
    },
    model_funct=get_coordination_session,
    count_funct=get_coordination_session_count,
    type_funct=get_coordination_session_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_coordination_session_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> None:
    coordination_uuid = kwargs.get("coordination_uuid")
    session_uuid = kwargs.get("session_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_type": kwargs["coordination_type"],
            "thread_id": kwargs["thread_id"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if kwargs.get("current_agent_uuid") is not None:
            cols["current_agent_uuid"] = kwargs["current_agent_uuid"]
        if kwargs.get("last_assistant_message") is not None:
            cols["last_assistant_message"] = kwargs["last_assistant_message"]
        if kwargs.get("status") is not None:
            cols["status"] = kwargs["status"]
        if kwargs.get("log") is not None:
            cols["log"] = kwargs["log"]
        CoordinationSessionModel(
            coordination_uuid,
            session_uuid,
            **cols,
        ).save()
        return

    coordination_session = kwargs.get("entity")
    actions = [
        CoordinationSessionModel.updated_by.set(kwargs["updated_by"]),
        CoordinationSessionModel.updated_at.set(pendulum.now("UTC")),
    ]
    if kwargs.get("coordination_type") is not None:
        actions.append(
            CoordinationSessionModel.coordination_type.set(kwargs["coordination_type"])
        )
    if kwargs.get("thread_id") is not None:
        actions.append(CoordinationSessionModel.thread_id.set(kwargs["thread_id"]))
    if kwargs.get("current_agent_uuid") is not None:
        actions.append(
            CoordinationSessionModel.current_agent_uuid.set(
                kwargs["current_agent_uuid"]
            )
        )
    if kwargs.get("last_assistant_message") is not None:
        actions.append(
            CoordinationSessionModel.last_assistant_message.set(
                kwargs["last_assistant_message"]
            )
        )
    if kwargs.get("status") is not None:
        actions.append(CoordinationSessionModel.status.set(kwargs["status"]))
    if kwargs.get("log") is not None:
        actions.append(CoordinationSessionModel.log.set(kwargs["log"]))
    coordination_session.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "session_uuid",
    },
    model_funct=get_coordination_session,
)
def delete_coordination_session_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> bool:
    kwargs.get("entity").delete()
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_coordination_message(
    session_uuid: str, message_id: str
) -> CoordinationMessageModel:
    return CoordinationMessageModel.get(session_uuid, message_id)


def get_coordination_message_count(session_uuid: str, message_id: str) -> int:
    return CoordinationMessageModel.count(
        session_uuid, CoordinationMessageModel.message_id == message_id
    )


def get_coordination_message_type(
    info: ResolveInfo, coordination_message: CoordinationMessageModel
) -> CoordinationMessageType:
    coordination_message = coordination_message.__dict__["attribute_values"]
    return CoordinationMessageType(
        **Utility.json_loads(Utility.json_dumps(coordination_message))
    )


def resolve_coordination_message_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> CoordinationMessageType:
    return get_coordination_message_type(
        info,
        get_coordination_message(kwargs["session_uuid"], kwargs["message_id"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["session_uuid", "message_id"],
    list_type_class=CoordinationMessageListType,
    type_funct=get_coordination_message_type,
)
def resolve_coordination_message_list_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:
    session_uuid = kwargs.get("session_uuid")
    coordination_uuid = kwargs.get("coordination_uuid")
    thread_id = kwargs.get("thread_id")
    agent_uuid = kwargs.get("agent_uuid")
    args = []
    inquiry_funct = CoordinationMessageModel.scan
    count_funct = CoordinationMessageModel.count
    if session_uuid:
        args = [session_uuid, None]
        inquiry_funct = CoordinationMessageModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_uuid is not None:
        the_filters &= CoordinationMessageModel.coordination_uuid == coordination_uuid
    if thread_id is not None:
        the_filters &= CoordinationMessageModel.thread_id == thread_id
    if agent_uuid is not None:
        the_filters &= CoordinationMessageModel.agent_uuid == agent_uuid
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "message_id",
    },
    model_funct=get_coordination_message,
    count_funct=get_coordination_message_count,
    type_funct=get_coordination_message_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_coordination_message_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> None:
    session_uuid = kwargs.get("session_uuid")
    message_id = kwargs.get("message_id")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "thread_id": kwargs["thread_id"],
            "agent_uuid": kwargs["agent_uuid"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        CoordinationMessageModel(
            session_uuid,
            message_id,
            **cols,
        ).save()
        return

    coordination_message = kwargs.get("entity")
    actions = [
        CoordinationMessageModel.updated_at.set(pendulum.now("UTC")),
    ]
    if kwargs.get("coordination_uuid") is not None:
        actions.append(
            CoordinationMessageModel.coordination_uuid.set(kwargs["coordination_uuid"])
        )
    if kwargs.get("thread_id") is not None:
        actions.append(CoordinationMessageModel.thread_id.set(kwargs["thread_id"]))
    if kwargs.get("agent_uuid") is not None:
        actions.append(CoordinationMessageModel.agent_uuid.set(kwargs["agent_uuid"]))
    coordination_message.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "message_id",
    },
    model_funct=get_coordination_message,
)
def delete_coordination_message_handler(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> bool:
    kwargs.get("entity").delete()
    return True
