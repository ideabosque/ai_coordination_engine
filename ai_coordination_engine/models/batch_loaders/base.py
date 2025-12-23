#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from promise.dataloader import DataLoader
from silvaengine_utility.serializer import Serializer

from ...handlers.config import Config


def normalize_model(model: Any) -> Dict[str, Any]:
    """
    Safely convert a PynamoDB model into a plain dict.

    Args:
        model: PynamoDB model instance

    Returns:
        Dictionary representation of the model
    """
    if hasattr(model, "__dict__") and "attribute_values" in model.__dict__:
        return Serializer.json_normalize(model.__dict__["attribute_values"])
    return {}


class SafeDataLoader(DataLoader):
    """
    Base DataLoader that swallows and logs errors rather than breaking the entire
    request. This keeps individual load failures isolated.

    All batch loaders should inherit from this class to ensure consistent
    error handling and caching behavior.
    """

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        """
        Initialize SafeDataLoader.

        Args:
            logger: Logger instance for error logging
            cache_enabled: Whether to enable caching for this loader
            **kwargs: Additional arguments passed to DataLoader
        """
        super(SafeDataLoader, self).__init__(**kwargs)
        self.logger = logger
        self.cache_enabled = cache_enabled and Config.is_cache_enabled()

    def dispatch(self):
        """
        Dispatch the batch load, catching and logging any errors.

        Returns:
            Result of batch load operation

        Raises:
            Exception: Re-raises caught exceptions after logging
        """
        try:
            return super(SafeDataLoader, self).dispatch()
        except Exception as exc:
            if self.logger:
                self.logger.exception(exc)
            raise
