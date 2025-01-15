#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType


class CoordinationType(ObjectType):
    coordination_type = String()
    coordination_uuid = String()
    coordination_name = String()
    coordination_description = String()
    assistant_id = String()
    assistant_type = String()
    additional_instructions = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationListType(ListObjectType):
    coordination_list = List(CoordinationType)
