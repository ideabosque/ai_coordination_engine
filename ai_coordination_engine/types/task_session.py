#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class TaskSessionType(ObjectType):
    task = JSON()
    session = JSON()
    endpoint_id = String()
    task_query = String()
    iteration_count = Int()
    status = String()
    notes = List(JSON)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class TaskSessionListType(ListObjectType):
    task_session_list = List(TaskSessionType)
