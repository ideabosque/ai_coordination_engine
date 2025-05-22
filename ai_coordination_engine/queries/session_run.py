#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import session_run
from ..types.session_run import SessionRunListType, SessionRunType


def resolve_session_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionRunType:
    return session_run.resolve_session_run(info, **kwargs)


def resolve_session_run_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionRunListType:
    return session_run.resolve_session_run_list(info, **kwargs)
