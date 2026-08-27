# -*- coding: utf-8 -*-
"""PG batch loader for Coordination entities."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise

from ....handlers.config import Config
from ...postgresql.coordination import CoordinationModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]


class CoordinationLoader(SafeDataLoader):
    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(CoordinationLoader, self).__init__(logger=logger, cache_enabled=cache_enabled, **kwargs)

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        session = Config.db_session
        for pk, cu in unique_keys:
            try:
                row = session.query(CoordinationModel).filter_by(partition_key=pk, coordination_uuid=cu).first()
                if row:
                    key_map[(pk, cu)] = normalize_model(row)
            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)
        return Promise.resolve([key_map.get(key) for key in keys])