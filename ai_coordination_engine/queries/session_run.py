#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo
from silvaengine_utility import method_cache

from ..handlers.config import Config
from ..models import session_run
from ..types.session_run import SessionRunListType, SessionRunType


def resolve_session_run(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionRunType | None:
    return session_run.resolve_session_run(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "session_run"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_session_run_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionRunListType:
    return session_run.resolve_session_run_list(info, **kwargs)
