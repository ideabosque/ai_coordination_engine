# -*- coding: utf-8 -*-
"""PostgreSQL repository for Session entity."""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, Optional

import pendulum
from graphene import ResolveInfo

from ....handlers.config import Config
from ....types.session import SessionListType, SessionType
from ...postgresql.base import normalize_row
from ...postgresql.session import SessionModel as PGModel
from ..base import EntityRepository

logger = logging.getLogger(__name__)


class SessionPGRepository(EntityRepository):
    """PostgreSQL repository for Session entities."""

    @property
    def entity_type(self) -> str:
        return "session"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        row = session.query(PGModel).filter_by(
            coordination_uuid=keys["coordination_uuid"],
            session_uuid=keys["session_uuid"],
        ).first()
        return normalize_row(row) if row else None

    def count(self, **keys) -> int:
        session = Config.db_session
        q = session.query(PGModel)
        if "partition_key" in keys:
            q = q.filter_by(partition_key=keys["partition_key"])
        if "coordination_uuid" in keys:
            q = q.filter_by(coordination_uuid=keys["coordination_uuid"])
        if "session_uuid" in keys:
            q = q.filter_by(session_uuid=keys["session_uuid"])
        if "task_uuid" in keys:
            q = q.filter_by(task_uuid=keys["task_uuid"])
        if "user_id" in keys:
            q = q.filter_by(user_id=keys["user_id"])
        return q.count()

    def list(self, info, **filters) -> Any:
        session = Config.db_session
        q = session.query(PGModel)

        partition_key = filters.get("partition_key") or info.context.get("partition_key")
        if partition_key:
            q = q.filter(PGModel.partition_key == partition_key)

        coordination_uuid = filters.get("coordination_uuid")
        if coordination_uuid:
            q = q.filter(PGModel.coordination_uuid == coordination_uuid)

        task_uuid = filters.get("task_uuid")
        if task_uuid:
            q = q.filter(PGModel.task_uuid == task_uuid)

        user_id = filters.get("user_id")
        if user_id:
            q = q.filter(PGModel.user_id == user_id)

        statuses = filters.get("statuses")
        if statuses:
            q = q.filter(PGModel.status.in_(statuses))

        total = q.count()
        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        offset = (page_number - 1) * limit if page_number > 0 else 0

        rows = q.order_by(PGModel.updated_at.desc()).offset(offset).limit(limit).all()
        items = [self.get_type(info, normalize_row(r)) for r in rows]

        return SessionListType(
            session_list=items,
            total=total,
            page_size=limit,
            page_number=page_number,
        )

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        pk = kwargs.get("partition_key") or info.context.get("partition_key")
        cu = kwargs.get("coordination_uuid")
        su = kwargs.get("session_uuid")

        existing = None
        if cu and su:
            existing = session.query(PGModel).filter_by(
                coordination_uuid=cu, session_uuid=su,
            ).first()

        try:
            if existing is None:
                row = PGModel(
                    partition_key=pk,
                    coordination_uuid=cu,
                    session_uuid=su,
                    task_uuid=kwargs.get("task_uuid"),
                    user_id=kwargs.get("user_id"),
                    task_query=kwargs.get("task_query"),
                    input_files=kwargs.get("input_files", []),
                    iteration_count=kwargs.get("iteration_count", 0),
                    subtask_queries=kwargs.get("subtask_queries", []),
                    status=kwargs.get("status", "initial"),
                    logs=kwargs.get("logs"),
                    updated_by=kwargs["updated_by"],
                )
                session.add(row)
                session.commit()
                session.refresh(row)
            else:
                if "task_uuid" in kwargs:
                    existing.task_uuid = kwargs["task_uuid"]
                if "user_id" in kwargs:
                    existing.user_id = kwargs["user_id"]
                if "task_query" in kwargs:
                    existing.task_query = kwargs["task_query"]
                if "input_files" in kwargs:
                    existing.input_files = kwargs["input_files"]
                if "iteration_count" in kwargs:
                    existing.iteration_count = kwargs["iteration_count"]
                if "subtask_queries" in kwargs:
                    existing.subtask_queries = kwargs["subtask_queries"]
                if "status" in kwargs:
                    existing.status = kwargs["status"]
                if "logs" in kwargs:
                    existing.logs = kwargs["logs"]
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
        cu = kwargs["coordination_uuid"]
        su = kwargs["session_uuid"]
        row = session.query(PGModel).filter_by(
            coordination_uuid=cu, session_uuid=su,
        ).first()
        if not row:
            return False
        try:
            session.delete(row)
            session.commit()
            self._purge_cache(info, {"coordination_uuid": cu, "session_uuid": su})
            return True
        except Exception:
            session.rollback()
            raise

    def get_type(self, info, instance: Any) -> Any:
        if isinstance(instance, dict):
            return SessionType(**instance)
        return SessionType(**normalize_row(instance))

    def resolve_single(self, info, **kwargs) -> Any:
        result = self.get(
            coordination_uuid=kwargs["coordination_uuid"],
            session_uuid=kwargs["session_uuid"],
        )
        if result is None:
            return None
        return self.get_type(info, result)

    def _purge_cache(self, info, entity_keys) -> None:
        try:
            from ...dynamodb.cache import purge_entity_cascading_cache
            purge_entity_cascading_cache(
                info.context.get("logger"),
                entity_type="session",
                entity_keys=entity_keys,
                cascade_depth=3,
            )
        except Exception:
            pass