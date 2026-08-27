# -*- coding: utf-8 -*-
"""PG batch loader for SessionAgent lists by session_uuid."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

from promise import Promise

from ....handlers.config import Config
from ...postgresql.session_agent import SessionAgentModel
from .base import SafeDataLoader, normalize_model


class SessionAgentsBySessionLoader(SafeDataLoader):
    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(SessionAgentsBySessionLoader, self).__init__(logger=logger, cache_enabled=cache_enabled, **kwargs)

    def batch_load_fn(self, session_uuids: List[str]) -> Promise:
        unique_uuids = list(dict.fromkeys(session_uuids))
        result_map: Dict[str, List[Dict[str, Any]]] = {}
        session = Config.db_session
        for su in unique_uuids:
            try:
                rows = session.query(SessionAgentModel).filter_by(session_uuid=su).order_by(SessionAgentModel.updated_at.desc()).all()
                result_map[su] = [normalize_model(r) for r in rows]
            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)
                result_map[su] = []
        return Promise.resolve([result_map.get(uuid, []) for uuid in session_uuids])