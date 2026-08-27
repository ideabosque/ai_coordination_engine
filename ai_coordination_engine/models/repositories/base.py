# -*- coding: utf-8 -*-
"""Repository base classes and error types for the dual-backend dispatch boundary.

Mirrors the pattern from rfq_engine and ai_agent_core_engine.
"""
from __future__ import print_function

__author__ = "bibow"

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class RepositoryError(Exception):
    """Base error for repository operations."""
    pass


class EntityNotFoundError(RepositoryError):
    """Raised when a single-entity lookup returns no result."""
    pass


class DependencyExistsError(RepositoryError):
    """Raised when a delete is blocked by existing child dependencies."""
    pass


class EntityRepository(ABC):
    """Abstract base class for all entity repositories.

    Each repository returns normalized dictionaries or explicit scalar results.
    PynamoDB and SQLAlchemy instances must not leak above the repository boundary.
    """

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Return the entity type string (e.g. 'coordination', 'session')."""
        ...

    @abstractmethod
    def get(self, **keys) -> Optional[Dict[str, Any]]:
        """Fetch a single entity by its primary key components."""
        ...

    @abstractmethod
    def count(self, **keys) -> int:
        """Count entities matching the given key components."""
        ...

    @abstractmethod
    def list(self, info, **filters) -> Any:
        """List entities with optional filters, returning a *ListType connection."""
        ...

    @abstractmethod
    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        """Insert or update an entity, returning the normalized result."""
        ...

    @abstractmethod
    def delete(self, info, **kwargs) -> bool:
        """Delete an entity, returning True on success."""
        ...

    # -- Convenience methods used by the GraphQL layer --

    def get_type(self, info, instance: Any) -> Any:
        """Convert a backend row/model to the GraphQL type instance.

        Default implementation expects a normalized dict and the type class
        to be resolvable from the entity_type. Subclasses may override.
        """
        return instance

    def resolve_single(self, info, **kwargs) -> Any:
        """Return the GraphQL type instance directly for single-record queries."""
        result = self.get(**kwargs)
        if result is None:
            return None
        return self.get_type(info, result)