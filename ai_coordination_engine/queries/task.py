#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import task
from ..types.task import TaskListType, TaskType


def resolve_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> TaskType:
    return task.resolve_task(info, **kwargs)


def resolve_task_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> TaskListType:
    return task.resolve_task_list(info, **kwargs)
