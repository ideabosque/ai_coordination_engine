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
    additional_instructions = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationAgentType(ObjectType):
    coordination = JSON()
    agent_uuid = String()
    agent_name = String()
    agent_instructions = String()
    response_format = String()
    json_schema = JSON()
    tools = List(JSON)
    predecessor = String()
    successor = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationSessionType(ObjectType):
    coordination = JSON()
    session_uuid = String()
    thread_id = String()
    current_agent = JSON()
    last_assistant_message = String()
    status = String()
    log = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationMessageType(ObjectType):
    coordination_session = JSON()
    message_id = String()
    thread_id = String()
    coordination_agent = JSON()
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
