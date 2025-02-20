#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class TaskSessionType(ObjectType):
    task = JSON()
    session = JSON()
    endpoint_id = String()
    task_query = String()
    status = String()
    notes = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class TaskSessionListType(ListObjectType):
    task_session_list = List(TaskSessionType)
