# -*- coding: utf-8 -*-
"""DynamoDB repository wrapper for the SessionAgent entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ..base import EntityRepository
from ._base import _normalize
from ...dynamodb.session_agent import (
    get_session_agent,
    get_session_agent_count,
    get_session_agent_type,
    resolve_session_agent,
    resolve_session_agent_list,
    insert_update_session_agent,
    delete_session_agent,
)


class SessionAgentDynamoDBRepository(EntityRepository):
    @property
    def entity_type(self) -> str:
        return "session_agent"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        try:
            model = get_session_agent(keys["session_uuid"], keys["session_agent_uuid"])
            return _normalize(model)
        except Exception:
            return None

    def count(self, **keys) -> int:
        return get_session_agent_count(keys["session_uuid"], keys["session_agent_uuid"])

    def list(self, info, **filters) -> Any:
        return resolve_session_agent_list(info, **filters)

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        return insert_update_session_agent(info, **kwargs)

    def delete(self, info, **kwargs) -> bool:
        return delete_session_agent(info, **kwargs)

    def get_type(self, info, instance: Any) -> Any:
        # instance may be a PynamoDB model or a normalized dict
        if hasattr(instance, "attribute_values"):
            return get_session_agent_type(info, instance)
        # If it's already a dict, construct the type directly
        from ....types.session_agent import SessionAgentType
        return SessionAgentType(**instance)

    def resolve_single(self, info, **kwargs) -> Any:
        return resolve_session_agent(info, **kwargs)