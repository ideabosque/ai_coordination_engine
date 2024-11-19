#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import (
    Boolean,
    DateTime,
    Decimal,
    Field,
    Float,
    Int,
    List,
    ObjectType,
    String,
)

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class CoordinationType(ObjectType):
    coordination_type = String()
    coordination_uuid = String()
    coordination_name = String()
    coordination_description = String()
    assistant_id = String()
    assistant_type = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationAgentType(ObjectType):
    coordination_uuid = String()
    agent_uuid = String()
    agent_name = String()
    agent_description = String()
    agent_instructions = String()
    agent_additional_instructions = String()
    coordination_type = String()
    response_format = String()
    predecessor = String()
    successor = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationSessionType(ObjectType):
    coordination_uuid = String()
    session_uuid = String()
    coordination_type = String()
    thread_id = String()
    current_agent_uuid = String()
    last_assistant_message = String()
    status = String()
    log = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationMessageType(ObjectType):
    session_uuid = String()
    message_id = String()
    coordination_uuid = String()
    thread_id = String()
    agent_uuid = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationListType(ListObjectType):
    coordination_list = List(CoordinationType)


class CoordinationAgentListType(ListObjectType):
    coordination_agent_list = List(CoordinationAgentType)


class CoordinationSessionListType(ListObjectType):
    coordination_session_list = List(CoordinationSessionType)


class CoordinationMessageListType(ListObjectType):
    coordination_message_list = List(CoordinationMessageType)
