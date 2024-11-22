#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from .handlers import (
    resolve_agent_handler,
    resolve_agent_list_handler,
    resolve_coordination_handler,
    resolve_coordination_list_handler,
    resolve_session_handler,
    resolve_session_list_handler,
    resolve_thread_handler,
    resolve_thread_list_handler,
)
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


def resolve_coordination(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> CoordinationType:
    return resolve_coordination_handler(info, **kwargs)


def resolve_coordination_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> CoordinationListType:
    return resolve_coordination_list_handler(info, **kwargs)


def resolve_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType:
    return resolve_agent_handler(info, **kwargs)


def resolve_agent_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentListType:
    return resolve_agent_list_handler(info, **kwargs)


def resolve_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType:
    return resolve_session_handler(info, **kwargs)


def resolve_session_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionListType:
    return resolve_session_list_handler(info, **kwargs)


def resolve_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType:
    return resolve_thread_handler(info, **kwargs)


def resolve_thread_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadListType:
    return resolve_thread_list_handler(info, **kwargs)
