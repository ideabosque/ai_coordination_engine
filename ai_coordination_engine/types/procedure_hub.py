#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import Field, ObjectType, String
from silvaengine_utility.serializer import Serializer


class ProcedureTaskSessionBaseType(ObjectType):
    """Base ProcedureTaskSession type with flat fields only (no nested resolvers)."""

    coordination_uuid = String()
    session_uuid = String()
    task_uuid = String()
    user_id = String()
    task_query = String()
    partition_key = String()


class ProcedureTaskSessionType(ProcedureTaskSessionBaseType):
    """
    ProcedureTaskSession type with nested resolvers for related entities.

    This type extends ProcedureTaskSessionBaseType to add lazy-loaded nested fields
    for coordination, session, and task, using DataLoader for efficient batching.
    """

    # Nested fields (lazy-loaded via resolvers)
    coordination = Field(lambda: CoordinationType)
    session = Field(lambda: SessionType)
    task = Field(lambda: TaskType)

    # ------- Nested resolvers -------

    @staticmethod
    def resolve_coordination(parent, info):
        """
        Resolve nested Coordination for this procedure task session using DataLoader.
        """
        from ..models.batch_loaders import get_loaders

        existing = getattr(parent, "coordination", None)
        if isinstance(existing, dict):
            return CoordinationType(**Serializer.json_normalize(existing))
        if isinstance(existing, CoordinationType):
            return existing

        partition_key = getattr(parent, "partition_key", None)
        coordination_uuid = getattr(parent, "coordination_uuid", None)
        if not partition_key or not coordination_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.coordination_loader.load(
            (partition_key, coordination_uuid)
        ).then(
            lambda coord_dict: (
                CoordinationType(**Serializer.json_normalize(coord_dict))
                if coord_dict
                else None
            )
        )

    @staticmethod
    def resolve_session(parent, info):
        """
        Resolve nested Session for this procedure task session using DataLoader.
        """
        from ..models.batch_loaders import get_loaders

        existing = getattr(parent, "session", None)
        if isinstance(existing, dict):
            return SessionType(**Serializer.json_normalize(existing))
        if isinstance(existing, SessionType):
            return existing

        coordination_uuid = getattr(parent, "coordination_uuid", None)
        session_uuid = getattr(parent, "session_uuid", None)
        if not coordination_uuid or not session_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.session_loader.load((coordination_uuid, session_uuid)).then(
            lambda session_dict: (
                SessionType(**Serializer.json_normalize(session_dict))
                if session_dict
                else None
            )
        )

    @staticmethod
    def resolve_task(parent, info):
        """
        Resolve nested Task for this procedure task session using DataLoader.
        """
        from ..models.batch_loaders import get_loaders

        existing = getattr(parent, "task", None)
        if isinstance(existing, dict):
            return TaskType(**Serializer.json_normalize(existing))
        if isinstance(existing, TaskType):
            return existing

        coordination_uuid = getattr(parent, "coordination_uuid", None)
        task_uuid = getattr(parent, "task_uuid", None)
        if not coordination_uuid or not task_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.task_loader.load((coordination_uuid, task_uuid)).then(
            lambda task_dict: (
                TaskType(**Serializer.json_normalize(task_dict)) if task_dict else None
            )
        )


from .coordination import CoordinationType
from .session import SessionType
from .task import TaskType
