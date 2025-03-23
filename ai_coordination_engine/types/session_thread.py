#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class SessionThreadType(ObjectType):
    session = JSON()
    thread_uuid = String()
    agent_uuid = String()
    endpoint_id = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionThreadListType(ListObjectType):
    session_thread_list = List(SessionThreadType)
