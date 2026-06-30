# -*- coding: utf-8 -*-
"""DynamoDB repository wrapper for the Task entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ..base import EntityRepository
from ._base import _normalize
from ...dynamodb.task import (
    get_task,
    get_task_count,
    get_task_type,
    resolve_task,
    resolve_task_list,
    insert_update_task,
    delete_task,
)


class TaskDynamoDBRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "task"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        try:
            model = get_task(keys["coordination_uuid"], keys["task_uuid"])
            return _normalize(model)
        except Exception:
            return None

    def count(self, **keys) -> int:
        return get_task_count(keys["coordination_uuid"], keys["task_uuid"])

    def list(self, info, **filters) -> Any:
        return resolve_task_list(info, **filters)

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        return insert_update_task(info, **kwargs)

    def delete(self, info, **kwargs) -> bool:
        return delete_task(info, **kwargs)

    def get_type(self, info, instance: Any) -> Any:
        # instance may be a PynamoDB model or a normalized dict
        if hasattr(instance, "attribute_values"):
            return get_task_type(info, instance)
        # If it's already a dict, construct the type directly
        from ....types.task import TaskType
        return TaskType(**instance)

    def resolve_single(self, info, **kwargs) -> Any:
        return resolve_task(info, **kwargs)