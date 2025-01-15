#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import session
from ..types.session import SessionListType, SessionType


def resolve_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType:
    return session.resolve_session(info, **kwargs)


def resolve_session_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionListType:
    return session.resolve_session_list(info, **kwargs)
