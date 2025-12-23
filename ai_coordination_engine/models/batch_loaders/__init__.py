#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from ...handlers.config import Config
from .async_task_loader import AsyncTaskLoader
from .coordination_loader import CoordinationLoader
from .session_agent_loader import SessionAgentLoader
from .session_agents_by_session_loader import SessionAgentsBySessionLoader
from .session_loader import SessionLoader
from .session_run_loader import SessionRunLoader
from .session_runs_by_session_loader import SessionRunsBySessionLoader
from .task_loader import TaskLoader

__all__ = [
    "RequestLoaders",
    "get_loaders",
    "clear_loaders",
    "AsyncTaskLoader",
    "CoordinationLoader",
    "TaskLoader",
    "SessionLoader",
    "SessionAgentLoader",
    "SessionRunLoader",
    "SessionAgentsBySessionLoader",
    "SessionRunsBySessionLoader",
]


class RequestLoaders:
    """
    Container for all DataLoaders scoped to a single GraphQL request.

    This class manages all batch loaders for the coordination engine,
    ensuring they are properly initialized and accessible throughout
    the request lifecycle.
    """

    def __init__(self, context: Dict[str, Any], cache_enabled: bool = True):
        """
        Initialize all batch loaders for this request.

        Args:
            context: GraphQL context containing logger and other request-scoped data
            cache_enabled: Whether to enable caching for loaders
        """
        logger = context.get("logger")
        self.cache_enabled = cache_enabled

        # One-to-one loaders (load single entities by key)
        self.coordination_loader = CoordinationLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.task_loader = TaskLoader(logger=logger, cache_enabled=cache_enabled)
        self.session_loader = SessionLoader(logger=logger, cache_enabled=cache_enabled)
        self.session_agent_loader = SessionAgentLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.session_run_loader = SessionRunLoader(
            logger=logger, cache_enabled=cache_enabled
        )

        # One-to-many loaders (load lists of entities by parent key)
        self.session_agents_by_session_loader = SessionAgentsBySessionLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.session_runs_by_session_loader = SessionRunsBySessionLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        
        # Async task loader
        self.async_task_loader = AsyncTaskLoader(
            logger=logger, cache_enabled=cache_enabled, context=context
        )

    def invalidate_cache(self, entity_type: str, entity_keys: Dict[str, str]):
        """
        Invalidate specific cache entries when entities are modified.

        This method is called after mutations to ensure cached data
        stays consistent with the database.

        Args:
            entity_type: Type of entity being invalidated (e.g., "coordination", "session")
            entity_keys: Dictionary of keys identifying the entity
        """
        if not self.cache_enabled:
            return

        if entity_type == "coordination" and "coordination_uuid" in entity_keys:
            cache_key = (
                f"{entity_keys.get('endpoint_id')}:{entity_keys['coordination_uuid']}"
            )
            if hasattr(self.coordination_loader, "cache"):
                self.coordination_loader.cache.delete(cache_key)

        elif entity_type == "task" and "task_uuid" in entity_keys:
            cache_key = (
                f"{entity_keys.get('coordination_uuid')}:{entity_keys['task_uuid']}"
            )
            if hasattr(self.task_loader, "cache"):
                self.task_loader.cache.delete(cache_key)

        elif entity_type == "session" and "session_uuid" in entity_keys:
            cache_key = (
                f"{entity_keys.get('coordination_uuid')}:{entity_keys['session_uuid']}"
            )
            if hasattr(self.session_loader, "cache"):
                self.session_loader.cache.delete(cache_key)
            # Also invalidate child loaders
            if hasattr(self.session_agents_by_session_loader, "cache"):
                self.session_agents_by_session_loader.cache.delete(
                    entity_keys["session_uuid"]
                )
            if hasattr(self.session_runs_by_session_loader, "cache"):
                self.session_runs_by_session_loader.cache.delete(
                    entity_keys["session_uuid"]
                )

        elif entity_type == "session_agent" and "session_agent_uuid" in entity_keys:
            cache_key = (
                f"{entity_keys.get('session_uuid')}:{entity_keys['session_agent_uuid']}"
            )
            if hasattr(self.session_agent_loader, "cache"):
                self.session_agent_loader.cache.delete(cache_key)
            # Also invalidate parent session's agent list
            if hasattr(self.session_agents_by_session_loader, "cache"):
                self.session_agents_by_session_loader.cache.delete(
                    entity_keys.get("session_uuid")
                )

        elif entity_type == "session_run" and "run_uuid" in entity_keys:
            cache_key = f"{entity_keys.get('session_uuid')}:{entity_keys['run_uuid']}"
            if hasattr(self.session_run_loader, "cache"):
                self.session_run_loader.cache.delete(cache_key)
            # Also invalidate parent session's run list
            if hasattr(self.session_runs_by_session_loader, "cache"):
                self.session_runs_by_session_loader.cache.delete(
                    entity_keys.get("session_uuid")
                )
        
        elif entity_type == "async_task" and "async_task_uuid" in entity_keys:
            if hasattr(self.async_task_loader, "cache"):
                self.async_task_loader.cache.delete(entity_keys["async_task_uuid"])


def get_loaders(context: Dict[str, Any]) -> RequestLoaders:
    """
    Fetch or initialize request-scoped loaders from the GraphQL context.

    This function lazily initializes the loaders on first access and
    stores them in the context for subsequent use within the same request.

    Args:
        context: GraphQL context dictionary

    Returns:
        RequestLoaders instance containing all batch loaders
    """
    if context is None:
        context = {}

    loaders = context.get("batch_loaders")
    if not loaders:
        cache_enabled = Config.is_cache_enabled()
        loaders = RequestLoaders(context, cache_enabled=cache_enabled)
        context["batch_loaders"] = loaders
    return loaders


def clear_loaders(context: Dict[str, Any]) -> None:
    """
    Clear loaders from context (useful for tests).

    Args:
        context: GraphQL context dictionary
    """
    if context is None:
        return
    context.pop("batch_loaders", None)
