#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class CoordinationType(ObjectType):
    partition_key = String()
    coordination_uuid = String()
    endpoint_id = String()
    part_id = String()
    coordination_name = String()
    coordination_description = String()
    agents = List(JSON)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class CoordinationListType(ListObjectType):
    coordination_list = List(CoordinationType)
