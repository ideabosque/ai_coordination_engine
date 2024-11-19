#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from .handlers import (
    resolve_coordination_agent_handler,
    resolve_coordination_agent_list_handler,
    resolve_coordination_handler,
    resolve_coordination_list_handler,
    resolve_coordination_message_handler,
    resolve_coordination_message_list_handler,
    resolve_coordination_session_handler,
    resolve_coordination_session_list_handler,
)


def resolve_coordination(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    return resolve_coordination_handler(info, **kwargs)


def resolve_coordination_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    return resolve_coordination_list_handler(info, **kwargs)


def resolve_coordination_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    return resolve_coordination_agent_handler(info, **kwargs)


def resolve_coordination_agent_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    return resolve_coordination_agent_list_handler(info, **kwargs)


def resolve_coordination_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    return resolve_coordination_session_handler(info, **kwargs)


def resolve_coordination_session_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:
    return resolve_coordination_session_list_handler(info, **kwargs)


def resolve_coordination_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    return resolve_coordination_message_handler(info, **kwargs)


def resolve_coordination_message_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:
    return resolve_coordination_message_list_handler(info, **kwargs)
