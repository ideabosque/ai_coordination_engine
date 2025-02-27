#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class SessionAgentType(ObjectType):
    task_session = JSON()
    thread_id = String()
    session_agent_uuid = String()
    agent_name = String()
    agent_action = JSON()
    user_input = String()
    agent_input = String()
    agent_output = String()
    predecessor = String()
    in_degree = Int()
    state = String()
    notes = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionAgentListType(ListObjectType):
    session_agent_list = List(SessionAgentType)
