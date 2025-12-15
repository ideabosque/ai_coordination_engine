#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON
from silvaengine_utility.serializer import Serializer


class TaskBaseType(ObjectType):
    """Base Task type with flat fields only (no nested resolvers)."""

    task_uuid = String()
    coordination_uuid = String()  # FK to Coordination
    endpoint_id = String()
    partition_key = String()
    task_name = String()
    task_description = String()
    initial_task_query = String()
    subtask_queries = List(JSON)
    agent_actions = JSON()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class TaskType(TaskBaseType):
    """
    Task type with nested resolvers for related entities.

    This type extends TaskBaseType to add lazy-loaded nested fields
    for coordination, using DataLoader for efficient batching.
    """

    # Nested fields (lazy-loaded via resolvers)
    coordination = Field(lambda: CoordinationType)

    # ------- Nested resolvers -------

    @staticmethod
    def resolve_coordination(parent, info):
        """
        Resolve nested Coordination for this task using DataLoader.

        Args:
            parent: Parent TaskType object
            info: GraphQL resolve info containing context

        Returns:
            CoordinationType object or Promise resolving to CoordinationType or None
        """
        from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded as dict
        existing = getattr(parent, "coordination", None)
        if isinstance(existing, dict):
            return CoordinationType(**Serializer.json_normalize(existing))
        if isinstance(existing, CoordinationType):
            return existing

        # Case 2: Need to fetch using DataLoader
        partition_key = getattr(parent, "partition_key", None) or getattr(
            parent, "endpoint_id", None
        )
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


class TaskListType(ListObjectType):
    task_list = List(TaskType)


from .coordination import CoordinationType
