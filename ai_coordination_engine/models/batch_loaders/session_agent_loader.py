#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from ..session_agent import SessionAgentModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]  # (session_uuid, session_agent_uuid)


class SessionAgentLoader(SafeDataLoader):
    """
    Batch loader for SessionAgentModel keyed by (session_uuid, session_agent_uuid).
    """

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(SessionAgentLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "session_agent")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        """
        Batch load session agents by their composite keys.

        Args:
            keys: List of (session_uuid, session_agent_uuid) tuples

        Returns:
            Promise resolving to list of session agent dicts in same order as keys
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # session_uuid:session_agent_uuid
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
                for session_uuid, session_agent_uuid in uncached_keys:
                    try:
                        session_agent = SessionAgentModel.get(
                            session_uuid, session_agent_uuid
                        )
                        normalized = normalize_model(session_agent)
                        key_map[(session_uuid, session_agent_uuid)] = normalized

                        # Cache the result if enabled
                        if self.cache_enabled:
                            cache_key = f"{session_uuid}:{session_agent_uuid}"
                            self.cache.set(
                                cache_key, normalized, ttl=Config.get_cache_ttl()
                            )
                    except SessionAgentModel.DoesNotExist:
                        pass

            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])
