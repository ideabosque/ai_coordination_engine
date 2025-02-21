#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import session_agent
from ..types.session_agent import SessionAgentListType, SessionAgentType


def resolve_session_agent(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentType:
    return session_agent.resolve_session_agent(info, **kwargs)


def resolve_session_agent_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentListType:
    return session_agent.resolve_session_agent_list(info, **kwargs)
