# -*- coding: utf-8 -*-
"""Shared helpers for DynamoDB repository wrappers."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from ....utils.normalization import normalize_to_json


def _normalize(model: Any) -> Dict[str, Any]:
    """Normalize a PynamoDB model instance to a JSON-serializable dict."""
    if hasattr(model, "attribute_values"):
        return normalize_to_json(model.attribute_values)
    if isinstance(model, dict):
        return normalize_to_json(model)
    return normalize_to_json({"value": model})