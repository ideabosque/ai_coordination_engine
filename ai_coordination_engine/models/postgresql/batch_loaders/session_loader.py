# -*- coding: utf-8 -*-
"""PG batch loader for Session entities."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise

from ....handlers.config import Config
from ...postgresql.session import SessionModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]


class SessionLoader(SafeDataLoader):
    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(SessionLoader, self).__init__(logger=logger, cache_enabled=cache_enabled, **kwargs)

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        session = Config.db_session
        for cu, su in unique_keys:
            try:
                row = session.query(SessionModel).filter_by(coordination_uuid=cu, session_uuid=su).first()
                if row:
                    key_map[(cu, su)] = normalize_model(row)
            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)
        return Promise.resolve([key_map.get(key) for key in keys])