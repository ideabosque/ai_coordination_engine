#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo
from silvaengine_utility import method_cache

from ..handlers.config import Config
from ..models.repositories import get_repo
from ..types.task_schedule import TaskScheduleListType, TaskScheduleType


def resolve_task_schedule(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskScheduleType | None:
    return get_repo("task_schedule").resolve_single(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "task_schedule"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_task_schedule_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> TaskScheduleListType:
    return get_repo("task_schedule").list(info, **kwargs)