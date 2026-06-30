# -*- coding: utf-8 -*-
"""PG batch loader for SessionAgent entities."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise

from ....handlers.config import Config
from ...postgresql.session_agent import SessionAgentModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]


class SessionAgentLoader(SafeDataLoader):
    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(SessionAgentLoader, self).__init__(logger=logger, cache_enabled=cache_enabled, **kwargs)

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        session = Config.db_session
        for su, sau in unique_keys:
            try:
                row = session.query(SessionAgentModel).filter_by(session_uuid=su, session_agent_uuid=sau).first()
                if row:
                    key_map[(su, sau)] = normalize_model(row)
            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)
        return Promise.resolve([key_map.get(key) for key in keys])