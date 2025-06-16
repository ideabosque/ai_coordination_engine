#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class SessionType(ObjectType):
    coordination = JSON()
    task = JSON()
    session_uuid = String()
    user_id = String()
    task_query = String()
    input_files = List(JSON)
    iteration_count = Int()
    subtask_queries = List(JSON)
    status = String()
    logs = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionListType(ListObjectType):
    session_list = List(SessionType)
