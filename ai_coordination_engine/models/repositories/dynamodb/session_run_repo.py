# -*- coding: utf-8 -*-
"""DynamoDB repository wrapper for the SessionRun entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ..base import EntityRepository
from ._base import _normalize
from ...dynamodb.session_run import (
    get_session_run,
    get_session_run_count,
    get_session_run_type,
    resolve_session_run,
    resolve_session_run_list,
    insert_update_session_run,
    delete_session_run,
)


class SessionRunDynamoDBRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "session_run"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        try:
            model = get_session_run(keys["session_uuid"], keys["run_uuid"])
            return _normalize(model)
        except Exception:
            return None

    def count(self, **keys) -> int:
        return get_session_run_count(keys["session_uuid"], keys["run_uuid"])

    def list(self, info, **filters) -> Any:
        return resolve_session_run_list(info, **filters)

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        return insert_update_session_run(info, **kwargs)

    def delete(self, info, **kwargs) -> bool:
        return delete_session_run(info, **kwargs)

    def get_type(self, info, instance: Any) -> Any:
        # instance may be a PynamoDB model or a normalized dict
        if hasattr(instance, "attribute_values"):
            return get_session_run_type(info, instance)
        # If it's already a dict, construct the type directly
        from ....types.session_run import SessionRunType
        return SessionRunType(**instance)

    def resolve_single(self, info, **kwargs) -> Any:
        return resolve_session_run(info, **kwargs)