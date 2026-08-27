#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo
from silvaengine_utility import method_cache

from ..handlers.config import Config
from ..models.repositories import get_repo
from ..types.session import SessionListType, SessionType


def resolve_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType | None:
    return get_repo("session").resolve_single(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "session"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_session_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionListType:
    return get_repo("session").list(info, **kwargs)
