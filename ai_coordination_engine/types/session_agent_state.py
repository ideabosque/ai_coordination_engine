#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class SessionAgentStateType(ObjectType):
    task_session = JSON()
    thread_id = String()
    session_agent_state_uuid = String()
    agent_name = String()
    user_in_the_loop = String()
    user_action = String()
    agent_input = String()
    agent_output = String()
    predecessors = List(String)
    in_degree = Int()
    state = String()
    notes = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionAgentStateListType(ListObjectType):
    session_agent_state_list = List(SessionAgentStateType)
