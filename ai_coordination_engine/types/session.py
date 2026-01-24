#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase
from silvaengine_utility.serializer import Serializer
from ..utils.normalization import normalize_to_json


class SessionBaseType(ObjectType):
    """Base Session type with flat fields only (no nested resolvers)."""

    session_uuid = String()
    coordination_uuid = String()  # FK to Coordination
    task_uuid = String()  # FK to Task
    user_id = String()
    endpoint_id = String()
    partition_key = String()
    task_query = String()
    input_files = List(JSONCamelCase)
    iteration_count = Int()
    subtask_queries = List(JSONCamelCase)
    status = String()
    logs = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionType(SessionBaseType):
    """
    Session type with nested resolvers for related entities.

    This type extends SessionBaseType to add lazy-loaded nested fields
    for coordination and task, using DataLoader for efficient batching.
    """

    # Nested fields (lazy-loaded via resolvers)
    coordination = Field(lambda: CoordinationType)
    task = Field(lambda: TaskType)
    session_agents = List(JSONCamelCase)  # List of session agents for this session
    session_runs = List(JSONCamelCase)  # List of session runs for this session

    # ------- Nested resolvers -------

    @staticmethod
    def resolve_coordination(parent, info):
        """
        Resolve nested Coordination for this session using DataLoader.

        Args:
            parent: Parent SessionType object
            info: GraphQL resolve info containing context

        Returns:
            CoordinationType object or Promise resolving to CoordinationType
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

    @staticmethod
    def resolve_task(parent, info):
        """
        Resolve nested Task for this session using DataLoader.

        Args:
            parent: Parent SessionType object
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
    def resolve_session_agents(parent, info):
        """
        Resolve all SessionAgents for this session as JSON list.

        Args:
            parent: Parent SessionType object
            info: GraphQL resolve info containing context

        Returns:
            List of session agent dicts or Promise resolving to list
        """
        from ..models.batch_loaders import get_loaders

        # Check if already embedded
        existing = getattr(parent, "session_agents", None)
        if isinstance(existing, list):
            return [normalize_to_json(agent) for agent in existing]

        # Fetch session agents for this session
        session_uuid = getattr(parent, "session_uuid", None)
        if not session_uuid:
            return []

        loaders = get_loaders(info.context)
        return loaders.session_agents_by_session_loader.load(session_uuid).then(
            lambda agents: [normalize_to_json(agent) for agent in agents]
        )

    @staticmethod
    def resolve_session_runs(parent, info):
        """
        Resolve all SessionRuns for this session as JSON list.

        Args:
            parent: Parent SessionType object
            info: GraphQL resolve info containing context

        Returns:
            List of session run dicts or Promise resolving to list
        """
        from ..models.batch_loaders import get_loaders

        # Check if already embedded
        existing = getattr(parent, "session_runs", None)
        if isinstance(existing, list):
            return [normalize_to_json(run) for run in existing]

        # Fetch session runs for this session
        session_uuid = getattr(parent, "session_uuid", None)
        if not session_uuid:
            return []

        loaders = get_loaders(info.context)
        return loaders.session_runs_by_session_loader.load(session_uuid).then(
            lambda runs: [normalize_to_json(run) for run in runs]
        )


class SessionListType(ListObjectType):
    session_list = List(SessionType)


from .coordination import CoordinationType
from .task import TaskType
