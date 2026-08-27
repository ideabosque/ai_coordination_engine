# -*- coding: utf-8 -*-
"""DynamoDB repository wrapper for the Session entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ..base import EntityRepository
from ._base import _normalize
from ...dynamodb.session import (
    get_session,
    get_session_count,
    get_session_type,
    resolve_session,
    resolve_session_list,
    insert_update_session,
    delete_session,
)


class SessionDynamoDBRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "session"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        try:
            model = get_session(keys["coordination_uuid"], keys["session_uuid"])
            return _normalize(model)
        except Exception:
            return None

    def count(self, **keys) -> int:
        return get_session_count(keys["coordination_uuid"], keys["session_uuid"])

    def list(self, info, **filters) -> Any:
        return resolve_session_list(info, **filters)

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        return insert_update_session(info, **kwargs)

    def delete(self, info, **kwargs) -> bool:
        return delete_session(info, **kwargs)

    def get_type(self, info, instance: Any) -> Any:
        # instance may be a PynamoDB model or a normalized dict
        if hasattr(instance, "attribute_values"):
            return get_session_type(info, instance)
        # If it's already a dict, construct the type directly
        from ....types.session import SessionType
        return SessionType(**instance)

    def resolve_single(self, info, **kwargs) -> Any:
        return resolve_session(info, **kwargs)