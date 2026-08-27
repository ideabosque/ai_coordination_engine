# -*- coding: utf-8 -*-
"""PostgreSQL repository registration."""
from __future__ import print_function

__author__ = "bibow"

import importlib
import logging
from typing import Dict

from ..base import EntityRepository

logger = logging.getLogger(__name__)

_REPO_MAP = [
    ("coordination", "coordination_repo", "CoordinationPGRepository"),
    ("session", "session_repo", "SessionPGRepository"),
    ("session_agent", "session_agent_repo", "SessionAgentPGRepository"),
    ("session_run", "session_run_repo", "SessionRunPGRepository"),
    ("task", "task_repo", "TaskPGRepository"),
    ("task_schedule", "task_schedule_repo", "TaskSchedulePGRepository"),
]


def register_all(registry: Dict[str, EntityRepository]) -> None:
    """Register all PostgreSQL repositories into the registry."""
    for entity_type, module_name, class_name in _REPO_MAP:
        try:
            mod = importlib.import_module(f".{module_name}", __name__)
            repo_cls = getattr(mod, class_name)
            registry[entity_type] = repo_cls()
        except ImportError as exc:
            logger.debug(f"PostgreSQL repository '{module_name}' not yet available: {exc}")
        except Exception as exc:
            logger.warning(f"Failed to register PostgreSQL repository '{module_name}': {exc}")