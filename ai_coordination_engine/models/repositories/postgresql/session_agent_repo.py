# -*- coding: utf-8 -*-
"""PostgreSQL repository for SessionAgent entity."""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, Optional

import pendulum
from graphene import ResolveInfo

from ....handlers.config import Config
from ....types.session_agent import SessionAgentListType, SessionAgentType
from ...postgresql.base import normalize_row
from ...postgresql.session_agent import SessionAgentModel as PGModel
from ..base import EntityRepository

logger = logging.getLogger(__name__)

_DEFAULT_AGENT_ACTION = {
    "primary_path": True,
    "user_in_the_loop": None,
    "predecessors": [],
    "action_function": {},
}


class SessionAgentPGRepository(EntityRepository):
    """PostgreSQL repository for SessionAgent entities."""

    @property
    def entity_type(self) -> str:
        return "session_agent"

    def get(self, **keys) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        row = session.query(PGModel).filter_by(
            session_uuid=keys["session_uuid"],
            session_agent_uuid=keys["session_agent_uuid"],
        ).first()
        return normalize_row(row) if row else None

    def count(self, **keys) -> int:
        session = Config.db_session
        q = session.query(PGModel)
        if "partition_key" in keys:
            q = q.filter_by(partition_key=keys["partition_key"])
        if "session_uuid" in keys:
            q = q.filter_by(session_uuid=keys["session_uuid"])
        if "coordination_uuid" in keys:
            q = q.filter_by(coordination_uuid=keys["coordination_uuid"])
        if "agent_uuid" in keys:
            q = q.filter_by(agent_uuid=keys["agent_uuid"])
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

        coordination_uuid = filters.get("coordination_uuid")
        if coordination_uuid:
            q = q.filter(PGModel.coordination_uuid == coordination_uuid)

        agent_uuid = filters.get("agent_uuid")
        if agent_uuid:
            q = q.filter(PGModel.agent_uuid == agent_uuid)

        primary_path = filters.get("primary_path")
        if primary_path is not None:
            q = q.filter(PGModel.agent_action["primary_path"].astext == str(primary_path).lower())

        user_in_the_loop = filters.get("user_in_the_loop")
        if user_in_the_loop is not None:
            q = q.filter(PGModel.agent_action["user_in_the_loop"].astext == str(user_in_the_loop).lower())

        predecessor = filters.get("predecessor")
        if predecessor:
            q = q.filter(PGModel.agent_action["predecessors"].contains(predecessor))

        predecessors = filters.get("predecessors")
        if predecessors:
            q = q.filter(PGModel.agent_uuid.in_(predecessors))

        in_degree = filters.get("in_degree")
        if in_degree is not None:
            q = q.filter(PGModel.in_degree == in_degree)

        states = filters.get("states")
        if states:
            q = q.filter(PGModel.state.in_(states))

        total = q.count()
        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        offset = (page_number - 1) * limit if page_number > 0 else 0

        rows = q.order_by(PGModel.updated_at.desc()).offset(offset).limit(limit).all()
        items = [self.get_type(info, normalize_row(r)) for r in rows]

        return SessionAgentListType(
            session_agent_list=items,
            total=total,
            page_size=limit,
            page_number=page_number,
        )

    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]:
        session = Config.db_session
        pk = kwargs.get("partition_key") or info.context.get("partition_key")
        su = kwargs.get("session_uuid")
        sau = kwargs.get("session_agent_uuid")

        existing = None
        if su and sau:
            existing = session.query(PGModel).filter_by(
                session_uuid=su, session_agent_uuid=sau,
            ).first()

        # Merge agent_action defaults with kwargs.
        agent_action = dict(_DEFAULT_AGENT_ACTION)
        if kwargs.get("agent_action"):
            agent_action.update(kwargs["agent_action"])

        try:
            if existing is None:
                row = PGModel(
                    partition_key=pk,
                    session_uuid=su,
                    session_agent_uuid=sau,
                    coordination_uuid=kwargs["coordination_uuid"],
                    agent_uuid=kwargs["agent_uuid"],
                    agent_action=agent_action,
                    user_input=kwargs.get("user_input"),
                    agent_input=kwargs.get("agent_input"),
                    agent_output=kwargs.get("agent_output"),
                    in_degree=kwargs.get("in_degree", 0),
                    state=kwargs.get("state", "initial"),
                    notes=kwargs.get("notes"),
                    updated_by=kwargs["updated_by"],
                )
                session.add(row)
                session.commit()
                session.refresh(row)
            else:
                if "coordination_uuid" in kwargs:
                    existing.coordination_uuid = kwargs["coordination_uuid"]
                if "agent_uuid" in kwargs:
                    existing.agent_uuid = kwargs["agent_uuid"]
                if "agent_action" in kwargs:
                    existing.agent_action = agent_action
                if "user_input" in kwargs:
                    existing.user_input = kwargs["user_input"]
                if "agent_input" in kwargs:
                    existing.agent_input = kwargs["agent_input"]
                if "agent_output" in kwargs:
                    existing.agent_output = kwargs["agent_output"]
                if "in_degree" in kwargs:
                    existing.in_degree = kwargs["in_degree"]
                if "state" in kwargs:
                    existing.state = kwargs["state"]
                if "notes" in kwargs:
                    existing.notes = kwargs["notes"]
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
        sau = kwargs["session_agent_uuid"]
        row = session.query(PGModel).filter_by(
            session_uuid=su, session_agent_uuid=sau,
        ).first()
        if not row:
            return False
        try:
            session.delete(row)
            session.commit()
            self._purge_cache(info, {"session_uuid": su, "session_agent_uuid": sau})
            return True
        except Exception:
            session.rollback()
            raise

    def get_type(self, info, instance: Any) -> Any:
        if isinstance(instance, dict):
            data = {k: v for k, v in instance.items() if k != "partition_key"}
            return SessionAgentType(**data)
        data = normalize_row(instance)
        data.pop("partition_key", None)
        return SessionAgentType(**data)

    def resolve_single(self, info, **kwargs) -> Any:
        result = self.get(
            session_uuid=kwargs["session_uuid"],
            session_agent_uuid=kwargs["session_agent_uuid"],
        )
        if result is None:
            return None
        return self.get_type(info, result)

    def _purge_cache(self, info, entity_keys) -> None:
        try:
            from ...dynamodb.cache import purge_entity_cascading_cache
            purge_entity_cascading_cache(
                info.context.get("logger"),
                entity_type="session_agent",
                entity_keys=entity_keys,
                cascade_depth=3,
            )
        except Exception:
            pass