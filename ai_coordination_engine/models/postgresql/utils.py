# -*- coding: utf-8 -*-
"""PostgreSQL table initialization — creates tables and applies RLS policies.

Phase 2 placeholder — will be expanded with full RLS policy creation.
"""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any


def initialize_tables(logger: logging.Logger, db_session: Any, engine: Any) -> None:
    """Create all PostgreSQL tables and apply RLS policies.

    Phase 2 implementation: runs Base.metadata.create_all(checkfirst=True)
    then applies RLS policies via create_rls_policies().
    """
    from .base import Base

    # Import all entity models so they register with Base.metadata
    try:
        from . import coordination  # noqa: F401
        from . import session  # noqa: F401
        from . import session_agent  # noqa: F401
        from . import session_run  # noqa: F401
        from . import task  # noqa: F401
        from . import task_schedule  # noqa: F401
    except ImportError as exc:
        logger.warning(f"Some PostgreSQL models not yet implemented: {exc}")

    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("PostgreSQL tables created (checkfirst=True).")

    # Apply RLS policies
    try:
        from ...utils.rls import create_rls_policies
        create_rls_policies(engine)
        logger.info("RLS policies applied to all tables.")
    except Exception as exc:
        logger.warning(f"Failed to apply RLS policies: {exc}")