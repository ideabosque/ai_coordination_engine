# -*- coding: utf-8 -*-
"""DynamoDB repository wrapper for the Coordination entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ..base import EntityRepository
from ._base import _normalize
from ...dynamodb.coordination import (
    get_coordination,
    get_coordination_count,
    get_coordination_type,
    resolve_coordination,
    resolve_coordination_list,
    insert_update_coordination,
    delete_coordination,
)


class CoordinationDynamoDBRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "coordination"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        try:
            model = get_coordination(keys["partition_key"], keys["coordination_uuid"])
            return _normalize(model)
        except Exception:
            return None

    def count(self, **keys) -> int:
        return get_coordination_count(keys["partition_key"], keys["coordination_uuid"])

    def list(self, info, **filters) -> Any:
        return resolve_coordination_list(info, **filters)

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        return insert_update_coordination(info, **kwargs)

    def delete(self, info, **kwargs) -> bool:
        return delete_coordination(info, **kwargs)

    def get_type(self, info, instance: Any) -> Any:
        # instance may be a PynamoDB model or a normalized dict
        if hasattr(instance, "attribute_values"):
            return get_coordination_type(info, instance)
        # If it's already a dict, construct the type directly
        from ....types.coordination import CoordinationType
        return CoordinationType(**instance)

    def resolve_single(self, info, **kwargs) -> Any:
        return resolve_coordination(info, **kwargs)