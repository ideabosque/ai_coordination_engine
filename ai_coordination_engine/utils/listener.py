#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo


def create_listener_info(
    logger,
    field_name: str,
    setting: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> ResolveInfo:
    """
    Build a minimal ResolveInfo for async listener contexts.
    """
    return ResolveInfo(
        field_name=field_name,
        field_nodes=[],  # legacy GraphQL AST field nodes
        return_type=None,
        parent_type=None,
        schema=None,
        fragments={},
        root_value=None,
        operation=None,
        variable_values={},
        is_awaitable=True,
        context={
            "setting": setting,
            "endpoint_id": kwargs.get("endpoint_id"),
            "logger": logger,
            "connection_id": kwargs.get("connection_id"),
            "part_id": kwargs.get("part_id"),
            "partition_key": kwargs.get(
                "partition_key", kwargs.get("context", {}).get("partition_key")
            ),
        },
        path=None,
    )
