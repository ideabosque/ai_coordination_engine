#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import task_session
from ..types.task_session import TaskSessionListType, TaskSessionType


def resolve_task_session(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskSessionType:
    return task_session.resolve_task_session(info, **kwargs)


def resolve_task_session_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskSessionListType:
    return task_session.resolve_task_session_list(info, **kwargs)
