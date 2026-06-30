# -*- coding: utf-8 -*-
"""PostgreSQL request-scoped DataLoaders — mirrors DynamoDB RequestLoaders interface.

Uses lazy importlib per loader so missing loader modules raise explicit errors.
"""
from __future__ import print_function

__author__ = "bibow"

import importlib
import logging
from typing import Any, Dict

from ....handlers.config import Config

logger = logging.getLogger(__name__)

# Loader property name -> (module path, class name)
_LOADER_MAP = {
    "coordination_loader": ("coordination_loader", "CoordinationLoader"),
    "session_loader": ("session_loader", "SessionLoader"),
    "session_agent_loader": ("session_agent_loader", "SessionAgentLoader"),
    "session_run_loader": ("session_run_loader", "SessionRunLoader"),
    "task_loader": ("task_loader", "TaskLoader"),
    "session_agents_by_session_loader": ("session_agents_by_session_loader", "SessionAgentsBySessionLoader"),
    "session_runs_by_session_loader": ("session_runs_by_session_loader", "SessionRunsBySessionLoader"),
    # async_task_loader is backend-agnostic (GraphQL loopback) — share the same implementation
    "async_task_loader": None,  # special: use the DynamoDB async_task_loader
}


class PGRequestLoaders:
    """Container for PostgreSQL DataLoaders scoped to a single GraphQL request.

    Mirrors the DynamoDB RequestLoaders interface with identical property names.
    Each loader is lazily instantiated on first access.
    """

    def __init__(self, context: Dict[str, Any], cache_enabled: bool = True):
        self.context = context
        self.cache_enabled = cache_enabled
        self._loaders: Dict[str, Any] = {}

    def _get_loader(self, prop_name: str) -> Any:
        """Lazily instantiate and cache a loader."""
        if prop_name in self._loaders:
            return self._loaders[prop_name]

        spec = _LOADER_MAP.get(prop_name)
        if spec is None and prop_name == "async_task_loader":
            # async_task_loader is backend-agnostic — use the shared implementation
            from ...dynamodb.batch_loaders.async_task_loader import AsyncTaskLoader
            loader = AsyncTaskLoader(
                logger=self.context.get("logger"),
                cache_enabled=self.cache_enabled,
                context=self.context,
            )
            self._loaders[prop_name] = loader
            return loader

        if spec is None:
            raise RuntimeError(f"Unknown loader property: {prop_name}")

        module_name, class_name = spec
        try:
            mod = importlib.import_module(f".{module_name}", __name__)
            loader_cls = getattr(mod, class_name)
            loader = loader_cls(
                logger=self.context.get("logger"),
                cache_enabled=self.cache_enabled,
            )
            self._loaders[prop_name] = loader
            return loader
        except ImportError as exc:
            raise RuntimeError(
                f"PostgreSQL loader '{module_name}' not yet implemented: {exc}"
            ) from exc

    @property
    def coordination_loader(self) -> Any:
        return self._get_loader("coordination_loader")

    @property
    def session_loader(self) -> Any:
        return self._get_loader("session_loader")

    @property
    def session_agent_loader(self) -> Any:
        return self._get_loader("session_agent_loader")

    @property
    def session_run_loader(self) -> Any:
        return self._get_loader("session_run_loader")

    @property
    def task_loader(self) -> Any:
        return self._get_loader("task_loader")

    @property
    def session_agents_by_session_loader(self) -> Any:
        return self._get_loader("session_agents_by_session_loader")

    @property
    def session_runs_by_session_loader(self) -> Any:
        return self._get_loader("session_runs_by_session_loader")

    @property
    def async_task_loader(self) -> Any:
        return self._get_loader("async_task_loader")

    def invalidate_cache(self, entity_type: str, entity_keys: Dict[str, str]) -> None:
        """Invalidate specific cache entries when entities are modified."""
        if not self.cache_enabled:
            return
        # Delegate to the same logic as DynamoDB RequestLoaders
        # For now, this is a no-op — PG loaders use SafeDataLoader caching
        pass