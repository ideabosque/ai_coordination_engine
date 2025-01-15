#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class SessionType(ObjectType):
    coordination = JSON()
    session_uuid = String()
    thread_ids = List(String)
    status = String()
    notes = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class SessionListType(ListObjectType):
    session_list = List(SessionType)
