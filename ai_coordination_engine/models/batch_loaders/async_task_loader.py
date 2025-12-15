#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from .base import SafeDataLoader


class AsyncTaskLoader(SafeDataLoader):
    """
    Batch loader for async tasks keyed by async_task_uuid.

    This loader fetches async task entities in batches and caches the results
    to minimize external API calls or database queries.
    """

    def __init__(self, logger=None, cache_enabled=True, context=None, **kwargs):
        """
        Initialize AsyncTaskLoader.

        Args:
            logger: Logger instance for error logging
            cache_enabled: Whether to enable caching
            context: GraphQL context for async task resolution
            **kwargs: Additional arguments passed to SafeDataLoader
        """
        super(AsyncTaskLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        self.context = context or {}
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "async_task")
            )

    def batch_load_fn(self, async_task_uuids: List[str]) -> Promise:
        """
        Batch load async tasks by their UUIDs.

        Args:
            async_task_uuids: List of async task UUID strings

        Returns:
            Promise resolving to list of async task dicts in same order as keys
        """
        # Deduplicate keys while preserving order
        unique_uuids = list(dict.fromkeys(async_task_uuids))
        task_map: Dict[str, Dict[str, Any]] = {}
        uncached_uuids = []

        # Check cache first if enabled
        if self.cache_enabled:
            for uuid in unique_uuids:
                cached_item = self.cache.get(uuid)
                if cached_item:
                    task_map[uuid] = cached_item
                else:
                    uncached_uuids.append(uuid)
        else:
            uncached_uuids = unique_uuids

        # Fetch uncached items from external service/database
        if uncached_uuids:
            try:
                for uuid in uncached_uuids:
                    try:
                        async_task = self._resolve_async_task(uuid)
                        if async_task:
                            task_map[uuid] = async_task

                            # Cache the result if enabled
                            if self.cache_enabled:
                                self.cache.set(
                                    uuid, async_task, ttl=Config.get_cache_ttl()
                                )
                    except Exception as exc:
                        if self.logger:
                            self.logger.warning(f"Failed to resolve async task {uuid}: {exc}")
                        # Leave as None for failed resolutions

            except Exception as exc:
                if self.logger:
                    self.logger.exception(exc)

        # Return results in same order as input keys
        return Promise.resolve([task_map.get(uuid) for uuid in async_task_uuids])

    def _resolve_async_task(self, async_task_uuid: str) -> Dict[str, Any] | None:
        """
        Resolve a single async task by UUID using the ai_coordination_utility.

        Args:
            async_task_uuid: UUID of the async task to resolve

        Returns:
            Dict containing async task data or None if not found
        """
        try:
            from ...handlers.ai_coordination_utility import get_async_task
            
            # Use the context passed during initialization, with fallback
            context = self.context.copy() if self.context else {}
            if "logger" not in context:
                context["logger"] = self.logger
            
            return get_async_task(
                context,
                functionName="async_execute_ask_model",
                asyncTaskUuid=async_task_uuid,
            )
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Failed to resolve async task {async_task_uuid}: {exc}")
            return None