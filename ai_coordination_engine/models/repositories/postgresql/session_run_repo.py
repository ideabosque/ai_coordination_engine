# -*- coding: utf-8 -*-
"""PostgreSQL repository for SessionRun entity."""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, Optional

import pendulum
from graphene import ResolveInfo

from ....handlers.config import Config
from ....types.session_run import SessionRunListType, SessionRunType
from ...postgresql.base import normalize_row
from ...postgresql.session_run import SessionRunModel as PGModel
from ..base import EntityRepository

logger = logging.getLogger(__name__)


class SessionRunPGRepository(EntityRepository):
    """PostgreSQL repository for SessionRun entities."""

    @property
    def entity_type(self) -> str:
        return "session_run"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        row = session.query(PGModel).filter_by(
            session_uuid=keys["session_uuid"],
            run_uuid=keys["run_uuid"],
        ).first()
        return normalize_row(row) if row else None

    def count(self, **keys) -> int:
        session = Config.db_session
        q = session.query(PGModel)
        if "partition_key" in keys:
            q = q.filter_by(partition_key=keys["partition_key"])
        if "session_uuid" in keys:
            q = q.filter_by(session_uuid=keys["session_uuid"])
        if "run_uuid" in keys:
            q = q.filter_by(run_uuid=keys["run_uuid"])
        if "agent_uuid" in keys:
            q = q.filter_by(agent_uuid=keys["agent_uuid"])
        if "thread_uuid" in keys:
            q = q.filter_by(thread_uuid=keys["thread_uuid"])
        if "coordination_uuid" in keys:
            q = q.filter_by(coordination_uuid=keys["coordination_uuid"])
        return q.count()

    def list(self, info, **filters) -> Any:
        session = Config.db_session
        q = session.query(PGModel)

        partition_key = filters.get("partition_key") or info.context.get("partition_key")
        if partition_key:
            q = q.filter(PGModel.partition_key == partition_key)

        session_uuid = filters.get("session_uuid")
        if session_uuid:
            q = q.filter(PGModel.session_uuid == session_uuid)

        agent_uuid = filters.get("agent_uuid")
        if agent_uuid:
            q = q.filter(PGModel.agent_uuid == agent_uuid)

        thread_uuid = filters.get("thread_uuid")
        if thread_uuid:
            q = q.filter(PGModel.thread_uuid == thread_uuid)

        coordination_uuid = filters.get("coordination_uuid")
        if coordination_uuid:
            q = q.filter(PGModel.coordination_uuid == coordination_uuid)

        total = q.count()
        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        offset = (page_number - 1) * limit if page_number > 0 else 0

        rows = q.order_by(PGModel.updated_at.desc()).offset(offset).limit(limit).all()
        items = [self.get_type(info, normalize_row(r)) for r in rows]

        return SessionRunListType(
            session_run_list=items,
            total=total,
            page_size=limit,
            page_number=page_number,
        )

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        pk = kwargs.get("partition_key") or info.context.get("partition_key")
        su = kwargs.get("session_uuid")
        ru = kwargs.get("run_uuid")

        existing = None
        if su and ru:
            existing = session.query(PGModel).filter_by(
                session_uuid=su, run_uuid=ru,
            ).first()

        try:
            if existing is None:
                row = PGModel(
                    partition_key=pk,
                    session_uuid=su,
                    run_uuid=ru,
                    thread_uuid=kwargs["thread_uuid"],
                    agent_uuid=kwargs["agent_uuid"],
                    coordination_uuid=kwargs["coordination_uuid"],
                    async_task_uuid=kwargs["async_task_uuid"],
                    session_agent_uuid=kwargs.get("session_agent_uuid"),
                    updated_by=kwargs["updated_by"],
                )
                session.add(row)
                session.commit()
                session.refresh(row)
            else:
                if "thread_uuid" in kwargs:
                    existing.thread_uuid = kwargs["thread_uuid"]
                if "agent_uuid" in kwargs:
                    existing.agent_uuid = kwargs["agent_uuid"]
                if "coordination_uuid" in kwargs:
                    existing.coordination_uuid = kwargs["coordination_uuid"]
                if "async_task_uuid" in kwargs:
                    existing.async_task_uuid = kwargs["async_task_uuid"]
                if "session_agent_uuid" in kwargs:
                    existing.session_agent_uuid = kwargs["session_agent_uuid"]
                existing.updated_by = kwargs["updated_by"]
                existing.updated_at = pendulum.now("UTC")
                session.commit()
                session.refresh(existing)
                row = existing

            result = normalize_row(row)
            self._purge_cache(info, result)
            return self.get_type(info, result)
        except Exception:
            session.rollback()
            raise

    def delete(self, info, **kwargs) -> bool:
        session = Config.db_session
        su = kwargs["session_uuid"]
        ru = kwargs["run_uuid"]
        row = session.query(PGModel).filter_by(
            session_uuid=su, run_uuid=ru,
        ).first()
        if not row:
            return False
        try:
            session.delete(row)
            session.commit()
            self._purge_cache(info, {"session_uuid": su, "run_uuid": ru})
            return True
        except Exception:
            session.rollback()
            raise

    def get_type(self, info, instance: Any) -> Any:
        if isinstance(instance, dict):
            return SessionRunType(**instance)
        return SessionRunType(**normalize_row(instance))

    def resolve_single(self, info, **kwargs) -> Any:
        result = self.get(
            session_uuid=kwargs["session_uuid"],
            run_uuid=kwargs["run_uuid"],
        )
        if result is None:
            return None
        return self.get_type(info, result)

    def _purge_cache(self, info, entity_keys) -> None:
        try:
            from ...dynamodb.cache import purge_entity_cascading_cache
            purge_entity_cascading_cache(
                info.context.get("logger"),
                entity_type="session_run",
                entity_keys=entity_keys,
                cascade_depth=3,
            )
        except Exception:
            pass