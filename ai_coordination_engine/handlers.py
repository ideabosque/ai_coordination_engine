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

from .models import AgentModel, CoordinationModel, SessionModel, ThreadModel
from .types import (
    AgentListType,
    AgentType,
    CoordinationListType,
    CoordinationType,
    SessionListType,
    SessionType,
    ThreadListType,
    ThreadType,
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


def _get_coordination(coordination_type: str, coordination_uuid: str) -> Dict[str, Any]:
    coordination = get_coordination(coordination_type, coordination_uuid)
    return {
        "coordination_type": coordination.coordination_type,
        "coordination_uuid": coordination.coordination_uuid,
        "coordination_name": coordination.coordination_name,
        "coordination_description": coordination.coordination_description,
        "assistant_id": coordination.assistant_id,
        "assistant_type": coordination.assistant_type,
        "additional_instructions": coordination.additional_instructions,
    }


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
    if kwargs.get("additional_instructions") is not None:
        actions.append(
            CoordinationModel.additional_instructions.set(
                kwargs["additional_instructions"]
            )
        )
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
def get_agent(coordination_uuid: str, agent_uuid: str) -> AgentModel:
    return AgentModel.get(coordination_uuid, agent_uuid)


def _get_agent(coordination_uuid: str, agent_uuid: str) -> Dict[str, Any]:
    agent = get_agent(coordination_uuid, agent_uuid)
    return {
        "coordination_uuid": agent.coordination_uuid,
        "agent_uuid": agent.agent_uuid,
        "agent_name": agent.agent_name,
        "agent_instructions": agent.agent_instructions,
        "coordination_type": agent.coordination_type,
        "response_format": agent.response_format,
        "json_schema": agent.json_schema,
        "tools": agent.tools,
        "predecessor": agent.predecessor,
        "successor": agent.successor,
    }


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


def resolve_agent_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType:
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
def resolve_agent_list_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
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
def insert_update_agent_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
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
    if kwargs.get("agent_name") is not None:
        actions.append(AgentModel.agent_name.set(kwargs["agent_name"]))
    if kwargs.get("coordination_type") is not None:
        actions.append(AgentModel.coordination_type.set(kwargs["coordination_type"]))
    if kwargs.get("agent_instructions") is not None:
        actions.append(AgentModel.agent_instructions.set(kwargs["agent_instructions"]))
    if kwargs.get("response_format") is not None:
        actions.append(AgentModel.response_format.set(kwargs["response_format"]))
    if kwargs.get("json_schema") is not None:
        actions.append(AgentModel.json_schema.set(kwargs["json_schema"]))
    if kwargs.get("tools") is not None:
        actions.append(AgentModel.tools.set(kwargs["tools"]))
    if kwargs.get("predecessor") is not None:
        actions.append(AgentModel.predecessor.set(kwargs["predecessor"]))
    if kwargs.get("successor") is not None:
        actions.append(AgentModel.successor.set(kwargs["successor"]))
    agent.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "agent_uuid",
    },
    model_funct=get_agent,
)
def delete_agent_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_session(coordination_uuid: str, session_uuid: str) -> SessionModel:
    return SessionModel.get(coordination_uuid, session_uuid)


def _get_session(coordination_uuid: str, session_uuid: str) -> Dict[str, Any]:
    session = get_session(coordination_uuid, session_uuid)
    return {
        "coordination": _get_coordination(
            session.coordination_type,
            session.coordination_uuid,
        ),
        "session_uuid": session.session_uuid,
        "status": session.status,
        "notes": session.notes,
    }


def get_session_count(coordination_uuid: str, session_uuid: str) -> int:
    return SessionModel.count(
        coordination_uuid, SessionModel.session_uuid == session_uuid
    )


def get_session_type(info: ResolveInfo, session: SessionModel) -> SessionType:
    try:
        coordination = _get_coordination(
            session.coordination_type,
            session.coordination_uuid,
        )
        results = ThreadModel.query(session.session_uuid, None)
        thread_ids = [result.thread_id for result in results]
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    session = session.__dict__["attribute_values"]
    session["coordination"] = coordination
    session["thread_ids"] = thread_ids
    session.pop("coordination_type")
    session.pop("coordination_uuid")
    return SessionType(**Utility.json_loads(Utility.json_dumps(session)))


def resolve_session_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType:
    return get_session_type(
        info,
        get_session(kwargs["coordination_uuid"], kwargs["session_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["coordination_uuid", "session_uuid"],
    list_type_class=SessionListType,
    type_funct=get_session_type,
)
def resolve_session_list_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    coordination_uuid = kwargs.get("coordination_uuid")
    coordination_types = kwargs.get("coordination_types")
    statuses = kwargs.get("statuses")
    args = []
    inquiry_funct = SessionModel.scan
    count_funct = SessionModel.count
    if coordination_uuid:
        args = [coordination_uuid, None]
        inquiry_funct = SessionModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_types is not None:
        the_filters &= SessionModel.coordination_type.is_in(*coordination_types)
    if statuses is not None:
        the_filters &= SessionModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "session_uuid",
    },
    model_funct=get_session,
    count_funct=get_session_count,
    type_funct=get_session_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_session_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    coordination_uuid = kwargs.get("coordination_uuid")
    session_uuid = kwargs.get("session_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_type": kwargs["coordination_type"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if kwargs.get("status") is not None:
            cols["status"] = kwargs["status"]
        if kwargs.get("notes") is not None:
            cols["notes"] = kwargs["notes"]
        SessionModel(
            coordination_uuid,
            session_uuid,
            **cols,
        ).save()
        return

    session = kwargs.get("entity")
    actions = [
        SessionModel.updated_by.set(kwargs["updated_by"]),
        SessionModel.updated_at.set(pendulum.now("UTC")),
    ]
    if kwargs.get("coordination_type") is not None:
        actions.append(SessionModel.coordination_type.set(kwargs["coordination_type"]))
    if kwargs.get("status") is not None:
        actions.append(SessionModel.status.set(kwargs["status"]))
    if kwargs.get("notes") is not None:
        actions.append(SessionModel.notes.set(kwargs["notes"]))
    session.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "coordination_uuid",
        "range_key": "session_uuid",
    },
    model_funct=get_session,
)
def delete_session_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_thread(session_uuid: str, thread_id: str) -> ThreadModel:
    return ThreadModel.get(session_uuid, thread_id)


def get_thread_count(session_uuid: str, thread_id: str) -> int:
    return ThreadModel.count(session_uuid, ThreadModel.thread_id == thread_id)


def get_thread_type(info: ResolveInfo, thread: ThreadModel) -> ThreadType:
    try:
        session = _get_session(
            thread.coordination_uuid,
            thread.session_uuid,
        )
        agent = None
        if thread.agent_uuid is not None:
            agent = _get_agent(
                thread.coordination_uuid,
                thread.agent_uuid,
            )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    thread = thread.__dict__["attribute_values"]
    thread["session"] = session
    thread["agent"] = agent
    thread.pop("coordination_uuid")
    thread.pop("session_uuid")
    thread.pop("agent_uuid", None)
    return ThreadType(**Utility.json_loads(Utility.json_dumps(thread)))


def resolve_thread_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType:
    return get_thread_type(
        info,
        get_thread(kwargs["session_uuid"], kwargs["thread_id"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["session_uuid", "thread_id"],
    list_type_class=ThreadListType,
    type_funct=get_thread_type,
)
def resolve_thread_list_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    session_uuid = kwargs.get("session_uuid")
    coordination_uuid = kwargs.get("coordination_uuid")
    agent_uuid = kwargs.get("agent_uuid")
    args = []
    inquiry_funct = ThreadModel.scan
    count_funct = ThreadModel.count
    if session_uuid:
        args = [session_uuid, None]
        inquiry_funct = ThreadModel.query

    the_filters = None  # We can add filters for the query.
    if coordination_uuid is not None:
        the_filters &= ThreadModel.coordination_uuid == coordination_uuid
    if agent_uuid is not None:
        the_filters &= ThreadModel.agent_uuid == agent_uuid
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "thread_id",
    },
    range_key_required=True,
    model_funct=get_thread,
    count_funct=get_thread_count,
    type_funct=get_thread_type,
    # data_attributes_except_for_data_diff=data_attributes_except_for_data_diff,
    # activity_history_funct=None,
)
def insert_update_thread_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    session_uuid = kwargs.get("session_uuid")
    thread_id = kwargs.get("thread_id")
    if kwargs.get("entity") is None:
        cols = {
            "coordination_uuid": kwargs["coordination_uuid"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        if kwargs.get("agent_uuid") is not None:
            cols["agent_uuid"] = kwargs["agent_uuid"]
        if kwargs.get("last_assistant_message") is not None:
            cols["last_assistant_message"] = kwargs["last_assistant_message"]
        if kwargs.get("status") is not None:
            cols["status"] = kwargs["status"]
        if kwargs.get("log") is not None:
            cols["log"] = kwargs["log"]
        ThreadModel(
            session_uuid,
            thread_id,
            **cols,
        ).save()
        return

    thread = kwargs.get("entity")
    actions = [
        SessionModel.updated_by.set(kwargs["updated_by"]),
        ThreadModel.updated_at.set(pendulum.now("UTC")),
    ]
    if kwargs.get("coordination_uuid") is not None:
        actions.append(ThreadModel.coordination_uuid.set(kwargs["coordination_uuid"]))
    if kwargs.get("agent_uuid") is not None:
        actions.append(ThreadModel.agent_uuid.set(kwargs["agent_uuid"]))
    if kwargs.get("last_assistant_message") is not None:
        actions.append(
            ThreadModel.last_assistant_message.set(kwargs["last_assistant_message"])
        )
    if kwargs.get("status") is not None:
        actions.append(ThreadModel.status.set(kwargs["status"]))
    if kwargs.get("log") is not None:
        actions.append(ThreadModel.log.set(kwargs["log"]))
    thread.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "session_uuid",
        "range_key": "thread_id",
    },
    model_funct=get_thread,
)
def delete_thread_handler(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
