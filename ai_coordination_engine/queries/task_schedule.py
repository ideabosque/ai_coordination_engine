#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import task_schedule
from ..types.task_schedule import TaskScheduleListType, TaskScheduleType


def resolve_task_schedule(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskScheduleType:
    return task_schedule.resolve_task_schedule(info, **kwargs)


def resolve_task_schedule_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskScheduleListType:
    return task_schedule.resolve_task_schedule_list(info, **kwargs)
