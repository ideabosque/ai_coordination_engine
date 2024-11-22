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


class AgentType(ObjectType):
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


class SessionType(ObjectType):
    coordination = JSON()
    session_uuid = String()
    thread_ids = List(String)
    status = String()
    notes = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class ThreadType(ObjectType):
    session = JSON()
    thread_id = String()
    agent = JSON()
    last_assistant_message = String()
    status = String()
    log = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationListType(ListObjectType):
    coordination_list = List(CoordinationType)


class AgentListType(ListObjectType):
    agent_list = List(AgentType)


class SessionListType(ListObjectType):
    session_list = List(SessionType)


class ThreadListType(ListObjectType):
    thread_list = List(ThreadType)
