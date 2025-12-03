#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON, Utility


class SessionRunTypeBase(ObjectType):
    """Base SessionRun type with flat fields only (no nested resolvers)."""

    run_uuid = String()
    session_uuid = String()  # FK to Session
    coordination_uuid = String()  # FK to Coordination
    session_agent_uuid = String()  # FK to SessionAgent
    thread_uuid = String()
    agent_uuid = String()
    endpoint_id = String()
    async_task_uuid = String()
    async_task = JSON()  # Async task details
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionRunType(SessionRunTypeBase):
    """
    SessionRun type with nested resolvers for related entities.

    This type extends SessionRunTypeBase to add lazy-loaded nested fields
    for session and session_agent, using DataLoader for efficient batching.
    """

    # Nested fields (lazy-loaded via resolvers)
    session = Field(lambda: SessionType)
    session_agent = Field(lambda: SessionAgentType)

    # ------- Nested resolvers -------

    @staticmethod
    def resolve_session(parent, info):
        """
        Resolve nested Session for this session run using DataLoader.

        Args:
            parent: Parent SessionRunType object
            info: GraphQL resolve info containing context

        Returns:
            SessionType object or Promise resolving to SessionType or None
        """
        from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded as dict
        existing = getattr(parent, "session", None)
        if isinstance(existing, dict):
            return SessionType(**Utility.json_normalize(existing))
        if isinstance(existing, SessionType):
            return existing

        # Case 2: Need to fetch using DataLoader
        coordination_uuid = getattr(parent, "coordination_uuid", None)
        session_uuid = getattr(parent, "session_uuid", None)
        if not coordination_uuid or not session_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.session_loader.load((coordination_uuid, session_uuid)).then(
            lambda session_dict: (
                SessionType(**Utility.json_normalize(session_dict))
                if session_dict
                else None
            )
        )

    @staticmethod
    def resolve_session_agent(parent, info):
        """
        Resolve nested SessionAgent for this session run using DataLoader.

        Args:
            parent: Parent SessionRunType object
            info: GraphQL resolve info containing context

        Returns:
            SessionAgentType object or Promise resolving to SessionAgentType or None
        """
        from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded as dict
        existing = getattr(parent, "session_agent", None)
        if isinstance(existing, dict):
            return SessionAgentType(**Utility.json_normalize(existing))
        if isinstance(existing, SessionAgentType):
            return existing

        # Case 2: Need to fetch using DataLoader
        session_uuid = getattr(parent, "session_uuid", None)
        session_agent_uuid = getattr(parent, "session_agent_uuid", None)
        if not session_uuid or not session_agent_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.session_agent_loader.load(
            (session_uuid, session_agent_uuid)
        ).then(
            lambda agent_dict: (
                SessionAgentType(**Utility.json_normalize(agent_dict))
                if agent_dict
                else None
            )
        )


class SessionRunListType(ListObjectType):
    session_run_list = List(SessionRunType)


from .session import SessionType
from .session_agent import SessionAgentType
