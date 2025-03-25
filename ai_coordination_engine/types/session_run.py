#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class SessionRunType(ObjectType):
    session = JSON()
    run_uuid = String()
    thread_uuid = String()
    agent_uuid = String()
    endpoint_id = String()
    async_task_uuid = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionRunListType(ListObjectType):
    session_run_list = List(SessionRunType)
