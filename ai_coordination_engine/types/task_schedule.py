#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class TaskScheduleType(ObjectType):
    task = JSON()
    coordination = JSON()
    schedule_uuid = String()
    schedule = String()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class TaskScheduleListType(ListObjectType):
    task_schedule_list = List(TaskScheduleType)
