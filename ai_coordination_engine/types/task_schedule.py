#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility.serializer import Serializer


class TaskScheduleBaseType(ObjectType):
    """Base TaskSchedule type with flat fields only (no nested resolvers)."""

    schedule_uuid = String()
    task_uuid = String()  # FK to Task
    coordination_uuid = String()  # FK to Coordination
    endpoint_id = String()
    partition_key = String()
    schedule = String()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class TaskScheduleType(TaskScheduleBaseType):
    """
    TaskSchedule type with nested resolvers for related entities.

    This type extends TaskScheduleBaseType to add lazy-loaded nested fields
    for task and coordination, using DataLoader for efficient batching.
    """

    # Nested fields (lazy-loaded via resolvers)
    task = Field(lambda: TaskType)
    coordination = Field(lambda: CoordinationType)

    # ------- Nested resolvers -------

    @staticmethod
    def resolve_task(parent, info):
        """
        Resolve nested Task for this task schedule using DataLoader.

        Args:
            parent: Parent TaskScheduleType object
            info: GraphQL resolve info containing context

        Returns:
            TaskType object or Promise resolving to TaskType or None
        """
        from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded as dict
        existing = getattr(parent, "task", None)
        if isinstance(existing, dict):
            return TaskType(**Serializer.json_normalize(existing))
        if isinstance(existing, TaskType):
            return existing

        # Case 2: Need to fetch using DataLoader
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

    @staticmethod
    def resolve_coordination(parent, info):
        """
        Resolve nested Coordination for this task schedule using DataLoader.

        Args:
            parent: Parent TaskScheduleType object
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


class TaskScheduleListType(ListObjectType):
    task_schedule_list = List(TaskScheduleType)


from .coordination import CoordinationType
from .task import TaskType
