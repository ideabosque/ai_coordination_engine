# -*- coding: utf-8 -*-
"""SQLAlchemy declarative base and row normalization helpers for PostgreSQL models.

Phase 2 placeholder — will be populated with the full base, normalize_row,
_serialize_value, prefixed_table, and prefixed_index utilities.
"""
from __future__ import print_function

__author__ = "bibow"

import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, String, text
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all PostgreSQL entity models."""
    pass


def _serialize_value(value: Any) -> Any:
    """Serialize a single SQLAlchemy column value for JSON/GraphQL output."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if hasattr(value, "isoformat"):
        # Return the datetime object directly — graphene DateTime serializes it
        # Strip microseconds for graphene DateTime compatibility
        return value.replace(microsecond=0) if hasattr(value, "microsecond") else value
    return value


def normalize_row(row: Any) -> Dict[str, Any]:
    """Normalize a SQLAlchemy row instance to a JSON-serializable dict."""
    if row is None:
        return None
    if isinstance(row, dict):
        return {k: _serialize_value(v) for k, v in row.items()}
    result = {}
    for column in row.__table__.columns:
        result[column.name] = _serialize_value(getattr(row, column.name))
    return result


def prefixed_table(table_name: str) -> str:
    """Apply PG_TABLE_PREFIX to a table name."""
    from ...handlers.config import Config
    prefix = getattr(Config, "PG_TABLE_PREFIX", "")
    return f"{prefix}{table_name}" if prefix else table_name


def prefixed_index(index_name: str) -> str:
    """Apply PG_TABLE_PREFIX to an index name."""
    from ...handlers.config import Config
    prefix = getattr(Config, "PG_TABLE_PREFIX", "")
    return f"{prefix}{index_name}" if prefix else index_name