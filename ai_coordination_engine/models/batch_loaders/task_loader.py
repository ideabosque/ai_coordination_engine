#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from ..task import TaskModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]  # (coordination_uuid, task_uuid)


class TaskLoader(SafeDataLoader):
    """
    Batch loader for TaskModel keyed by (coordination_uuid, task_uuid).
    """

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(TaskLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "task"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        """
        Batch load tasks by their composite keys.

        Args:
            keys: List of (coordination_uuid, task_uuid) tuples

        Returns:
            Promise resolving to list of task dicts in same order as keys
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # coordination_uuid:task_uuid
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
                for coordination_uuid, task_uuid in uncached_keys:
                    try:
                        task = TaskModel.get(coordination_uuid, task_uuid)
                        normalized = normalize_model(task)
                        key_map[(coordination_uuid, task_uuid)] = normalized

                        # Cache the result if enabled
                        if self.cache_enabled:
                            cache_key = f"{coordination_uuid}:{task_uuid}"
                            self.cache.set(
                                cache_key, normalized, ttl=Config.get_cache_ttl()
                            )
                    except TaskModel.DoesNotExist:
                        pass

            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])
