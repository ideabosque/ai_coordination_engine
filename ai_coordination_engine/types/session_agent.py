#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON, Utility


class SessionAgentTypeBase(ObjectType):
    """Base SessionAgent type with flat fields only (no nested resolvers)."""

    session_agent_uuid = String()
    session_uuid = String()  # FK to Session
    coordination_uuid = String()  # FK to Coordination
    agent_uuid = String()
    agent_action = JSON()
    user_input = String()
    agent_input = String()
    agent_output = String()
    in_degree = Int()
    state = String()
    notes = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionAgentType(SessionAgentTypeBase):
    """
    SessionAgent type with nested resolvers for related entities.

    This type extends SessionAgentTypeBase to add lazy-loaded nested fields
    for session, using DataLoader for efficient batching.
    """

    # Nested fields (lazy-loaded via resolvers)
    session = Field(lambda: SessionType)

    # ------- Nested resolvers -------

    @staticmethod
    def resolve_session(parent, info):
        """
        Resolve nested Session for this session agent using DataLoader.

        Args:
            parent: Parent SessionAgentType object
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


class SessionAgentListType(ListObjectType):
    session_agent_list = List(SessionAgentType)


from .session import SessionType
