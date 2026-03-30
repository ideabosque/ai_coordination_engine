#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Base module for AI Coordination Engine models.

Provides common utilities, decorators, and base classes for model implementations.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Callable, Dict, List, TypeVar, Union

from silvaengine_dynamodb_base import BaseModel

from ..handlers.config import Config

F = TypeVar("F", bound=Callable[..., Any])


def get_model_key_fields(model_class: Type[BaseModel]) -> List[str]:
    """Get the key field names for a DynamoDB model.

    Args:
        model_class: The DynamoDB model class

    Returns:
        List of key field names
    """
    key_fields = []
    for attr_name in dir(model_class):
        attr = getattr(model_class, attr_name, None)
        if attr is not None and hasattr(attr, "is_hash_key") and attr.is_hash_key:
            key_fields.append(attr_name)
        if attr is not None and hasattr(attr, "is_range_key") and attr.is_range_key:
            key_fields.append(attr_name)
    return key_fields


def get_entity_id_from_kwargs(
    model_class: Type[BaseModel],
    kwargs: Dict[str, Any]
) -> Union[str, None]:
    """Extract entity ID from kwargs based on model key fields.

    Args:
        model_class: The DynamoDB model class
        kwargs: Keyword arguments

    Returns:
        The entity ID if found, None otherwise
    """
    key_fields = get_model_key_fields(model_class)
    for field in key_fields:
        if field in kwargs:
            return kwargs[field]
        if field == "partition_key" and "endpoint_id" in kwargs:
            return kwargs["endpoint_id"]
    return None
