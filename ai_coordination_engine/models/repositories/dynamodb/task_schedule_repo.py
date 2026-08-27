# -*- coding: utf-8 -*-
"""DynamoDB repository wrapper for the TaskSchedule entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ..base import EntityRepository
from ._base import _normalize
from ...dynamodb.task_schedule import (
    get_task_schedule,
    get_task_schedule_count,
    get_task_schedule_type,
    resolve_task_schedule,
    resolve_task_schedule_list,
    insert_update_task_schedule,
    delete_task_schedule,
)


class TaskScheduleDynamoDBRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "task_schedule"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        try:
            model = get_task_schedule(keys["task_uuid"], keys["schedule_uuid"])
            return _normalize(model)
        except Exception:
            return None

    def count(self, **keys) -> int:
        return get_task_schedule_count(keys["task_uuid"], keys["schedule_uuid"])

    def list(self, info, **filters) -> Any:
        return resolve_task_schedule_list(info, **filters)

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        return insert_update_task_schedule(info, **kwargs)

    def delete(self, info, **kwargs) -> bool:
        return delete_task_schedule(info, **kwargs)

    def get_type(self, info, instance: Any) -> Any:
        # instance may be a PynamoDB model or a normalized dict
        if hasattr(instance, "attribute_values"):
            return get_task_schedule_type(info, instance)
        # If it's already a dict, construct the type directly
        from ....types.task_schedule import TaskScheduleType
        return TaskScheduleType(**instance)

    def resolve_single(self, info, **kwargs) -> Any:
        return resolve_task_schedule(info, **kwargs)