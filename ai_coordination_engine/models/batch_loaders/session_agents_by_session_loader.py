#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from ..session_agent import SessionAgentModel
from .base import SafeDataLoader, normalize_model


class SessionAgentsBySessionLoader(SafeDataLoader):
    """
    Batch loader for fetching all SessionAgents by session_uuid (one-to-many).

    This loader fetches all session agents for multiple sessions in a batch
    and returns them as lists.
    """

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(SessionAgentsBySessionLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "session_agents_by_session")
            )

    def batch_load_fn(self, keys: List[str]) -> Promise:
        """
        Load all session agents for multiple session_uuids.

        Args:
            keys: List of session_uuids (strings)

        Returns:
            Promise resolving to list of lists of session agent dicts
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[str, List[Dict[str, Any]]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = key  # session_uuid
                cached_item = self.cache.get(cache_key)
                if cached_item:
                    key_map[key] = cached_item
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = unique_keys

        # Batch fetch uncached items
        if uncached_keys:
            try:
                for session_uuid in uncached_keys:
                    # Query all session agents for this session
                    session_agents = list(
                        SessionAgentModel.query(
                            session_uuid,
                            # Could add filters here if needed
                        )
                    )

                    # Normalize all session agents
                    normalized_agents = [
                        normalize_model(agent) for agent in session_agents
                    ]

                    key_map[session_uuid] = normalized_agents

                    # Cache the result if enabled
                    if self.cache_enabled:
                        self.cache.set(
                            session_uuid,
                            normalized_agents,
                            ttl=Config.get_cache_ttl(),
                        )

            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)

        # Return results in same order as input keys, default to empty list
        return Promise.resolve([key_map.get(key, []) for key in keys])
