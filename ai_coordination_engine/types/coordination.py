#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

from sys import modules
from xml.parsers.expat import model

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from silvaengine_definitions import ThemeSettingLoader, ThemeSettingModel
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase, Serializer

ThemeSettingType = ThemeSettingModel.generate_graphql_type()


class CoordinationType(ObjectType):
    partition_key = String()
    coordination_uuid = String()
    endpoint_id = String()
    part_id = String()
    theme_uuid = String()
    theme = Field(lambda: ThemeSettingType)
    coordination_name = String()
    coordination_description = String()
    agents = List(JSONCamelCase)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    @staticmethod
    def resolve_theme(parent, info):
        existing = getattr(parent, "task", None)

        if isinstance(existing, dict):
            return ThemeSettingType(**Serializer.json_normalize(existing))
        elif isinstance(existing, ThemeSettingType):
            return existing

        # Case 2: Need to fetch using DataLoader
        partition_key = getattr(parent, "partition_key", None)
        theme_uuid = getattr(parent, "theme_uuid", None)

        if not partition_key or not theme_uuid:
            return None

        def cb(theme_setting):
            print(theme_setting)
            return (
                ThemeSettingType(**Serializer.json_normalize(theme_setting))
                if theme_setting
                else None
            )

        return ThemeSettingLoader(info=info).load((partition_key, theme_uuid)).then(cb)


class CoordinationListType(ListObjectType):
    coordination_list = List(CoordinationType)
