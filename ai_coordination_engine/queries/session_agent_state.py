#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import session_agent_state
from ..types.session_agent_state import SessionAgentStateListType, SessionAgentStateType


def resolve_session_agent_state(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentStateType:
    return session_agent_state.resolve_session_agent_state(info, **kwargs)


def resolve_session_agent_state_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentStateListType:
    return session_agent_state.resolve_session_agent_state_list(info, **kwargs)
