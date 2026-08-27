# -*- coding: utf-8 -*-
"""PostgreSQL repository for Task entity."""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, Optional

import pendulum
from graphene import ResolveInfo

from ....handlers.config import Config
from ....types.task import TaskListType, TaskType
from ...postgresql.base import normalize_row
from ...postgresql.task import TaskModel as PGModel
from ..base import EntityRepository
from ..dispatch import get_repo

logger = logging.getLogger(__name__)


class TaskPGRepository(EntityRepository):
    """PostgreSQL repository for Task entities."""

    @property
    def entity_type(self) -> str:
        return "task"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        row = session.query(PGModel).filter_by(
            coordination_uuid=keys["coordination_uuid"],
            task_uuid=keys["task_uuid"],
        ).first()
        return normalize_row(row) if row else None

    def count(self, **keys) -> int:
        session = Config.db_session
        q = session.query(PGModel)
        if "partition_key" in keys:
            q = q.filter_by(partition_key=keys["partition_key"])
        if "coordination_uuid" in keys:
            q = q.filter_by(coordination_uuid=keys["coordination_uuid"])
        if "task_uuid" in keys:
            q = q.filter_by(task_uuid=keys["task_uuid"])
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

        task_name = filters.get("task_name")
        if task_name:
            q = q.filter(PGModel.task_name.ilike(f"%{task_name}%"))

        task_description = filters.get("task_description")
        if task_description:
            q = q.filter(PGModel.task_description.ilike(f"%{task_description}%"))

        initial_task_query = filters.get("initial_task_query")
        if initial_task_query:
            q = q.filter(PGModel.initial_task_query.ilike(f"%{initial_task_query}%"))

        total = q.count()
        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        offset = (page_number - 1) * limit if page_number > 0 else 0

        rows = q.order_by(PGModel.updated_at.desc()).offset(offset).limit(limit).all()
        items = [self.get_type(info, normalize_row(r)) for r in rows]

        return TaskListType(
            task_list=items,
            total=total,
            page_size=limit,
            page_number=page_number,
        )

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        pk = kwargs.get("partition_key") or info.context.get("partition_key")
        cu = kwargs.get("coordination_uuid")
        tu = kwargs.get("task_uuid")

        # Validate subtask_queries and agent_actions against coordination's agents.
        coordination_repo = get_repo("coordination")
        coordination = coordination_repo.get(partition_key=pk, coordination_uuid=cu)
        if coordination is None:
            raise ValueError(f"Coordination {cu} not found for task insert/update")
        coordination_agents = coordination.get("agents", [])

        subtask_queries = kwargs.get("subtask_queries") or []
        agent_actions = kwargs.get("agent_actions") or {}

        # Filter out agents not in coordination's agents list (matching DynamoDB behavior)
        if coordination_agents:
            valid_agent_uuids = set()
            for a in coordination_agents:
                if isinstance(a, dict):
                    valid_agent_uuids.add(a.get("agent_uuid") or a.get("agentUuid"))
                else:
                    valid_agent_uuids.add(a)
            subtask_queries = [sq for sq in subtask_queries
                             if not isinstance(sq, dict)
                             or not sq.get("agent_uuid")
                             or sq.get("agent_uuid") in valid_agent_uuids]
            agent_actions = {k: v for k, v in agent_actions.items()
                           if not k or k in valid_agent_uuids}

        existing = None
        if cu and tu:
            existing = session.query(PGModel).filter_by(
                coordination_uuid=cu, task_uuid=tu,
            ).first()

        try:
            if existing is None:
                row = PGModel(
                    partition_key=pk,
                    coordination_uuid=cu,
                    task_uuid=tu,
                    task_name=kwargs["task_name"],
                    task_description=kwargs.get("task_description"),
                    initial_task_query=kwargs["initial_task_query"],
                    subtask_queries=subtask_queries,
                    agent_actions=agent_actions,
                    updated_by=kwargs["updated_by"],
                )
                session.add(row)
                session.commit()
                session.refresh(row)
            else:
                if "task_name" in kwargs:
                    existing.task_name = kwargs["task_name"]
                if "task_description" in kwargs:
                    existing.task_description = kwargs["task_description"]
                if "initial_task_query" in kwargs:
                    existing.initial_task_query = kwargs["initial_task_query"]
                if "subtask_queries" in kwargs:
                    existing.subtask_queries = subtask_queries
                if "agent_actions" in kwargs:
                    existing.agent_actions = agent_actions
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
        tu = kwargs["task_uuid"]
        row = session.query(PGModel).filter_by(
            coordination_uuid=cu, task_uuid=tu,
        ).first()
        if not row:
            return False
        try:
            session.delete(row)
            session.commit()
            self._purge_cache(info, {"coordination_uuid": cu, "task_uuid": tu})
            return True
        except Exception:
            session.rollback()
            raise

    def get_type(self, info, instance: Any) -> Any:
        if isinstance(instance, dict):
            return TaskType(**instance)
        return TaskType(**normalize_row(instance))

    def resolve_single(self, info, **kwargs) -> Any:
        result = self.get(
            coordination_uuid=kwargs["coordination_uuid"],
            task_uuid=kwargs["task_uuid"],
        )
        if result is None:
            return None
        return self.get_type(info, result)

    def _purge_cache(self, info, entity_keys) -> None:
        try:
            from ...dynamodb.cache import purge_entity_cascading_cache
            purge_entity_cascading_cache(
                info.context.get("logger"),
                entity_type="task",
                entity_keys=entity_keys,
                cascade_depth=3,
            )
        except Exception:
            pass