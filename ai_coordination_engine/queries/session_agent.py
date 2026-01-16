#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo
from silvaengine_utility import method_cache

from ..handlers.config import Config
from ..models import session_agent
from ..types.session_agent import SessionAgentListType, SessionAgentType


def resolve_session_agent(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentType | None:
    return session_agent.resolve_session_agent(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "session_agent"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_session_agent_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionAgentListType:
    return session_agent.resolve_session_agent_list(info, **kwargs)
