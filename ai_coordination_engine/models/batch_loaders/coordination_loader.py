#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from ..coordination import CoordinationModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]  # (partition_key, coordination_uuid)


class CoordinationLoader(SafeDataLoader):
    """
    Batch loader for CoordinationModel keyed by (partition_key, coordination_uuid).

    This loader fetches coordination entities in batches and caches the results
    to minimize database queries.
    """

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        """
        Initialize CoordinationLoader.

        Args:
            logger: Logger instance for error logging
            cache_enabled: Whether to enable caching
            **kwargs: Additional arguments passed to SafeDataLoader
        """
        super(CoordinationLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "coordination")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        """
        Batch load coordinations by their composite keys.

        Args:
            keys: List of (partition_key, coordination_uuid) tuples

        Returns:
            Promise resolving to list of coordination dicts in same order as keys
        """
        # Deduplicate keys while preserving order
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # partition_key:coordination_uuid
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
                for partition_key, coordination_uuid in uncached_keys:
                    try:
                        coordination = CoordinationModel.get(
                            partition_key, coordination_uuid
                        )
                        normalized = normalize_model(coordination)
                        key_map[(partition_key, coordination_uuid)] = normalized

                        # Cache the result if enabled
                        if self.cache_enabled:
                            cache_key = f"{partition_key}:{coordination_uuid}"
                            self.cache.set(
                                cache_key, normalized, ttl=Config.get_cache_ttl()
                            )
                    except CoordinationModel.DoesNotExist:
                        # Coordination not found, leave as None
                        pass

            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)

        # Return results in same order as input keys
        return Promise.resolve([key_map.get(key) for key in keys])
