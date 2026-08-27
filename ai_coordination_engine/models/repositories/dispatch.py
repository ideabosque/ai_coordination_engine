# -*- coding: utf-8 -*-
"""Repository dispatch — routes get_repo()/get_loaders() to the active backend.

Mirrors the verified pattern from rfq_engine and ai_agent_core_engine.
"""
from __future__ import print_function

__author__ = "bibow"

import importlib
import logging
from typing import Any, Dict, Optional

from .base import EntityRepository

logger = logging.getLogger(__name__)

_repo_registry: Dict[str, Dict[str, EntityRepository]] = {
    "dynamodb": {},
    "postgresql": {},
}
_dynamodb_initialized = False
_postgresql_initialized = False


def _get_backend() -> str:
    """Return the active backend from Config.DB_BACKEND."""
    from ...handlers.config import Config
    backend = getattr(Config, "DB_BACKEND", "dynamodb")
    if backend not in ("dynamodb", "postgresql"):
        raise ValueError(f"Unknown db_backend: {backend}")
    return backend


def _init_dynamodb_repos() -> None:
    """Lazily register all DynamoDB repositories."""
    global _dynamodb_initialized
    if _dynamodb_initialized:
        return
    try:
        mod = importlib.import_module(
            "ai_coordination_engine.models.repositories.dynamodb"
        )
        mod.register_all(_repo_registry["dynamodb"])
    except Exception as exc:
        logger.error("Failed to initialize DynamoDB repositories: %s", exc)
        raise
    _dynamodb_initialized = True


def _init_postgresql_repos() -> None:
    """Lazily register all PostgreSQL repositories."""
    global _postgresql_initialized
    if _postgresql_initialized:
        return
    try:
        mod = importlib.import_module(
            "ai_coordination_engine.models.repositories.postgresql"
        )
        mod.register_all(_repo_registry["postgresql"])
    except Exception as exc:
        logger.error("Failed to initialize PostgreSQL repositories: %s", exc)
        raise
    _postgresql_initialized = True


def get_repo(entity_type: str) -> EntityRepository:
    """Return the active backend's repository for the given entity type.

    Raises KeyError if no repository is registered for the requested entity.
    """
    backend = _get_backend()
    if backend == "dynamodb":
        _init_dynamodb_repos()
    else:
        _init_postgresql_repos()

    registry = _repo_registry.get(backend, {})
    repo = registry.get(entity_type)
    if repo is None:
        raise KeyError(
            f"No repository registered for entity '{entity_type}' on backend '{backend}'"
        )
    return repo


def get_loaders(context: Dict[str, Any]) -> Any:
    """Return request-scoped DataLoaders for the active backend.

    Memoized on context['batch_loaders']. Returns DynamoDB RequestLoaders
    or PostgreSQL PGRequestLoaders depending on Config.DB_BACKEND.
    """
    if context is None:
        context = {}

    existing = context.get("batch_loaders")
    if existing is not None:
        return existing

    backend = _get_backend()

    if backend == "dynamodb":
        from ..dynamodb.batch_loaders import RequestLoaders, get_loaders as _dd_get
        # Use the existing get_loaders which memoizes on context['batch_loaders']
        return _dd_get(context)
    elif backend == "postgresql":
        from ..postgresql.batch_loaders import PGRequestLoaders
        from ...handlers.config import Config
        cache_enabled = Config.is_cache_enabled()
        loaders = PGRequestLoaders(context, cache_enabled=cache_enabled)
        context["batch_loaders"] = loaders
        return loaders
    else:
        raise ValueError(f"Unknown backend: {backend}")


def register_repo(backend: str, entity_type: str, repo: EntityRepository) -> None:
    """Manually register a repository instance."""
    if backend not in _repo_registry:
        raise ValueError(f"Unknown backend: {backend}")
    _repo_registry[backend][entity_type] = repo


def clear_registry() -> None:
    """Reset both registries and init flags (used by tests)."""
    global _dynamodb_initialized, _postgresql_initialized
    _repo_registry["dynamodb"].clear()
    _repo_registry["postgresql"].clear()
    _dynamodb_initialized = False
    _postgresql_initialized = False