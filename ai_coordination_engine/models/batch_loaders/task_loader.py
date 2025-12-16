#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from .base import SafeDataLoader, normalize_model, Key


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
            cache_meta = Config.get_cache_entity_config().get("task")
            self.cache_func_prefix = ""
            if cache_meta:
                self.cache_func_prefix = ".".join([cache_meta.get("module"), cache_meta.get("getter")])

    def generate_cache_key(self, key: Key) -> str:
        if not isinstance(key, tuple):
            key = (key,)
        key_data = ":".join([str(key), str({})])
        return self.cache._generate_key(
            self.cache_func_prefix,
            key_data
        )
    
    def get_cache_data(self, key: Key) -> Dict[str, Any] | None | List[Dict[str, Any]]:
        cache_key = self.generate_cache_key(key)
        cached_item = self.cache.get(cache_key)
        if cached_item is None:  # pragma: no cover - defensive
            return None
        if isinstance(cached_item, dict):  # pragma: no cover - defensive
            return cached_item
        if isinstance(cached_item, list):  # pragma: no cover - defensive
            return [normalize_model(item) for item in cached_item]
        return normalize_model(cached_item)

    def set_cache_data(self, key: Key, data: Any) -> None:
        cache_key = self.generate_cache_key(key)
        self.cache.set(cache_key, data, ttl=Config.get_cache_ttl())

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        from ..task import TaskModel
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
                cached_item = self.get_cache_data(key)
                if cached_item:
                    key_map[key] = cached_item
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = unique_keys

        # Fetch uncached items from database
        if uncached_keys:
            try:
                for task in TaskModel.batch_get(uncached_keys):
                    key = (task.coordination_uuid, task.task_uuid)

                    # Cache the result if enabled
                    if self.cache_enabled:
                        self.set_cache_data(key, task)
                    normalized = normalize_model(task)
                    key_map[key] = normalized
                # for coordination_uuid, task_uuid in uncached_keys:
                #     try:
                #         task = TaskModel.get(coordination_uuid, task_uuid)
                #         normalized = normalize_model(task)
                #         key_map[(coordination_uuid, task_uuid)] = normalized

                #         # Cache the result if enabled
                #         if self.cache_enabled:
                #             cache_key = f"{coordination_uuid}:{task_uuid}"
                #             self.cache.set(
                #                 cache_key, normalized, ttl=Config.get_cache_ttl()
                #             )
                #     except TaskModel.DoesNotExist:
                #         pass

            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])
