#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class TaskType(ObjectType):
    coordination = JSON()
    task_uuid = String()
    task_name = String()
    task_description = String()
    initial_task_query = String()
    agent_actions = List(JSON)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class TaskListType(ListObjectType):
    task_list = List(TaskType)
