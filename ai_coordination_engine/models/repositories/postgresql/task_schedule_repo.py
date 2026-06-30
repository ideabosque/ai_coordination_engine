# -*- coding: utf-8 -*-
"""PostgreSQL repository for TaskSchedule entity."""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, Optional

import pendulum
from graphene import ResolveInfo

from ....handlers.config import Config
from ....types.task_schedule import TaskScheduleListType, TaskScheduleType
from ...postgresql.base import normalize_row
from ...postgresql.task_schedule import TaskScheduleModel as PGModel
from ..base import EntityRepository

logger = logging.getLogger(__name__)


class TaskSchedulePGRepository(EntityRepository):
    """PostgreSQL repository for TaskSchedule entities."""

    @property
    def entity_type(self) -> str:
        return "task_schedule"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        row = session.query(PGModel).filter_by(
            task_uuid=keys["task_uuid"],
            schedule_uuid=keys["schedule_uuid"],
        ).first()
        return normalize_row(row) if row else None

    def count(self, **keys) -> int:
        session = Config.db_session
        q = session.query(PGModel)
        if "partition_key" in keys:
            q = q.filter_by(partition_key=keys["partition_key"])
        if "task_uuid" in keys:
            q = q.filter_by(task_uuid=keys["task_uuid"])
        if "schedule_uuid" in keys:
            q = q.filter_by(schedule_uuid=keys["schedule_uuid"])
        if "coordination_uuid" in keys:
            q = q.filter_by(coordination_uuid=keys["coordination_uuid"])
        return q.count()

    def list(self, info, **filters) -> Any:
        session = Config.db_session
        q = session.query(PGModel)

        partition_key = filters.get("partition_key") or info.context.get("partition_key")
        if partition_key:
            q = q.filter(PGModel.partition_key == partition_key)

        task_uuid = filters.get("task_uuid")
        if task_uuid:
            q = q.filter(PGModel.task_uuid == task_uuid)

        coordination_uuid = filters.get("coordination_uuid")
        if coordination_uuid:
            q = q.filter(PGModel.coordination_uuid == coordination_uuid)

        statuses = filters.get("statuses")
        if statuses:
            q = q.filter(PGModel.status.in_(statuses))

        total = q.count()
        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        offset = (page_number - 1) * limit if page_number > 0 else 0

        rows = q.order_by(PGModel.updated_at.desc()).offset(offset).limit(limit).all()
        items = [self.get_type(info, normalize_row(r)) for r in rows]

        return TaskScheduleListType(
            task_schedule_list=items,
            total=total,
            page_size=limit,
            page_number=page_number,
        )

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        pk = kwargs.get("partition_key") or info.context.get("partition_key")
        tu = kwargs.get("task_uuid")
        sch_u = kwargs.get("schedule_uuid")

        existing = None
        if tu and sch_u:
            existing = session.query(PGModel).filter_by(
                task_uuid=tu, schedule_uuid=sch_u,
            ).first()

        try:
            if existing is None:
                row = PGModel(
                    partition_key=pk,
                    task_uuid=tu,
                    schedule_uuid=sch_u,
                    coordination_uuid=kwargs["coordination_uuid"],
                    schedule=kwargs["schedule"],
                    status=kwargs.get("status", "initial"),
                    updated_by=kwargs["updated_by"],
                )
                session.add(row)
                session.commit()
                session.refresh(row)
            else:
                if "coordination_uuid" in kwargs:
                    existing.coordination_uuid = kwargs["coordination_uuid"]
                if "schedule" in kwargs:
                    existing.schedule = kwargs["schedule"]
                if "status" in kwargs:
                    existing.status = kwargs["status"]
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
        tu = kwargs["task_uuid"]
        sch_u = kwargs["schedule_uuid"]
        row = session.query(PGModel).filter_by(
            task_uuid=tu, schedule_uuid=sch_u,
        ).first()
        if not row:
            return False
        try:
            session.delete(row)
            session.commit()
            self._purge_cache(info, {"task_uuid": tu, "schedule_uuid": sch_u})
            return True
        except Exception:
            session.rollback()
            raise

    def get_type(self, info, instance: Any) -> Any:
        if isinstance(instance, dict):
            return TaskScheduleType(**instance)
        return TaskScheduleType(**normalize_row(instance))

    def resolve_single(self, info, **kwargs) -> Any:
        result = self.get(
            task_uuid=kwargs["task_uuid"],
            schedule_uuid=kwargs["schedule_uuid"],
        )
        if result is None:
            return None
        return self.get_type(info, result)

    def _purge_cache(self, info, entity_keys) -> None:
        try:
            from ...dynamodb.cache import purge_entity_cascading_cache
            purge_entity_cascading_cache(
                info.context.get("logger"),
                entity_type="task_schedule",
                entity_keys=entity_keys,
                cascade_depth=3,
            )
        except Exception:
            pass