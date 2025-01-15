#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class ThreadType(ObjectType):
    session = JSON()
    thread_id = String()
    agent = JSON()
    last_assistant_message = String()
    status = String()
    log = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class ThreadListType(ListObjectType):
    thread_list = List(ThreadType)
