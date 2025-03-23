#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import session_thread
from ..types.session_thread import SessionThreadListType, SessionThreadType


def resolve_session_thread(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionThreadType:
    return session_thread.resolve_session_thread(info, **kwargs)


def resolve_session_thread_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionThreadListType:
    return session_thread.resolve_session_thread_list(info, **kwargs)
