#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from ..session import SessionModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]  # (coordination_uuid, session_uuid)


class SessionLoader(SafeDataLoader):
    """
    Batch loader for SessionModel keyed by (coordination_uuid, session_uuid).
    """

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(SessionLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "session"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        """
        Batch load sessions by their composite keys.

        Args:
            keys: List of (coordination_uuid, session_uuid) tuples

        Returns:
            Promise resolving to list of session dicts in same order as keys
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # coordination_uuid:session_uuid
                cached_item = self.cache.get(cache_key)
                if cached_item:
                    key_map[key] = cached_item
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = unique_keys

        # Fetch uncached items from database
        if uncached_keys:
            try:
                for coordination_uuid, session_uuid in uncached_keys:
                    try:
                        session = SessionModel.get(coordination_uuid, session_uuid)
                        normalized = normalize_model(session)
                        key_map[(coordination_uuid, session_uuid)] = normalized

                        # Cache the result if enabled
                        if self.cache_enabled:
                            cache_key = f"{coordination_uuid}:{session_uuid}"
                            self.cache.set(
                                cache_key, normalized, ttl=Config.get_cache_ttl()
                            )
                    except SessionModel.DoesNotExist:
                        pass

            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])
