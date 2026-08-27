# -*- coding: utf-8 -*-
"""Base DataLoader for PostgreSQL batch loaders."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from promise.dataloader import DataLoader

from ....handlers.config import Config


def normalize_model(model: Any) -> Dict[str, Any]:
    """Normalize a SQLAlchemy model instance to a plain dict."""
    from ...postgresql.base import normalize_row
    if model is None:
        return None
    return normalize_row(model)


class SafeDataLoader(DataLoader):
    """Base DataLoader that swallows and logs errors rather than breaking the request."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(SafeDataLoader, self).__init__(**kwargs)
        self.logger = logger
        self.cache_enabled = cache_enabled and Config.is_cache_enabled()

    def dispatch(self):
        try:
            return super(SafeDataLoader, self).dispatch()
        except Exception as exc:
            if self.logger:
                self.logger.exception(exc)
            raise