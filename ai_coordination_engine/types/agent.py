#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class AgentType(ObjectType):
    coordination = JSON()
    agent_version_uuid = String()
    agent_name = String()
    agent_instructions = String()
    response_format = String()
    json_schema = JSON()
    tools = List(JSON)
    predecessor = String()
    successor = String()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class AgentListType(ListObjectType):
    agent_list = List(AgentType)
