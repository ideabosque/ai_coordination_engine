# -*- coding: utf-8 -*-
"""PostgreSQL repository for Coordination entity."""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, Optional

import pendulum
from graphene import ResolveInfo

from ....handlers.config import Config
from ....types.coordination import CoordinationListType, CoordinationType
from ...postgresql.base import normalize_row
from ...postgresql.coordination import CoordinationModel as PGModel
from ..base import EntityRepository

logger = logging.getLogger(__name__)


class CoordinationPGRepository(EntityRepository):
    """PostgreSQL repository for Coordination entities."""

    @property
    def entity_type(self) -> str:
        return "coordination"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        row = session.query(PGModel).filter_by(
            partition_key=keys["partition_key"],
            coordination_uuid=keys["coordination_uuid"],
        ).first()
        return normalize_row(row) if row else None

    def count(self, **keys) -> int:
        session = Config.db_session
        q = session.query(PGModel)
        if "partition_key" in keys:
            q = q.filter_by(partition_key=keys["partition_key"])
        if "coordination_uuid" in keys:
            q = q.filter_by(coordination_uuid=keys["coordination_uuid"])
        return q.count()

    def list(self, info, **filters) -> Any:
        session = Config.db_session
        q = session.query(PGModel)

        partition_key = info.context.get("partition_key")
        if partition_key:
            q = q.filter(PGModel.partition_key == partition_key)

        coordination_name = filters.get("coordination_name")
        if coordination_name:
            q = q.filter(PGModel.coordination_name.ilike(f"%{coordination_name}%"))

        coordination_description = filters.get("coordination_description")
        if coordination_description:
            q = q.filter(PGModel.coordination_description.ilike(f"%{coordination_description}%"))

        total = q.count()
        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        offset = (page_number - 1) * limit if page_number > 0 else 0

        rows = q.order_by(PGModel.updated_at.desc()).offset(offset).limit(limit).all()
        items = [self.get_type(info, normalize_row(r)) for r in rows]

        return CoordinationListType(
            coordination_list=items,
            total=total,
            page_size=limit,
            page_number=page_number,
        )

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        pk = kwargs.get("partition_key") or info.context.get("partition_key")
        cu = kwargs.get("coordination_uuid")

        existing = None
        if cu:
            existing = session.query(PGModel).filter_by(
                partition_key=pk, coordination_uuid=cu,
            ).first()

        try:
            if existing is None:
                row = PGModel(
                    partition_key=pk,
                    coordination_uuid=cu,
                    endpoint_id=info.context.get("endpoint_id"),
                    part_id=info.context.get("part_id"),
                    coordination_name=kwargs.get("coordination_name", ""),
                    coordination_description=kwargs.get("coordination_description"),
                    agents=kwargs.get("agents", []),
                    updated_by=kwargs["updated_by"],
                )
                session.add(row)
                session.commit()
                session.refresh(row)
            else:
                if "coordination_name" in kwargs:
                    existing.coordination_name = kwargs["coordination_name"]
                if "coordination_description" in kwargs:
                    existing.coordination_description = kwargs["coordination_description"]
                if "agents" in kwargs:
                    existing.agents = kwargs["agents"]
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
        pk = kwargs.get("partition_key") or info.context.get("partition_key")
        cu = kwargs["coordination_uuid"]
        row = session.query(PGModel).filter_by(partition_key=pk, coordination_uuid=cu).first()
        if not row:
            return False
        try:
            session.delete(row)
            session.commit()
            self._purge_cache(info, {"partition_key": pk, "coordination_uuid": cu})
            return True
        except Exception:
            session.rollback()
            raise

    def get_type(self, info, instance: Any) -> Any:
        if isinstance(instance, dict):
            return CoordinationType(**instance)
        return CoordinationType(**normalize_row(instance))

    def resolve_single(self, info, **kwargs) -> Any:
        pk = info.context.get("partition_key") or info.context.get("endpoint_id")
        result = self.get(partition_key=pk, coordination_uuid=kwargs["coordination_uuid"])
        if result is None:
            return None
        return self.get_type(info, result)

    def _purge_cache(self, info, entity_keys) -> None:
        try:
            from ...dynamodb.cache import purge_entity_cascading_cache
            purge_entity_cascading_cache(
                info.context.get("logger"),
                entity_type="coordination",
                entity_keys=entity_keys,
                cascade_depth=3,
            )
        except Exception:
            pass