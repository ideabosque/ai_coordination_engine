#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from silvaengine_definitions import (
    AgentLoader,
    AgentModel,
    ThemeSettingLoader,
    ThemeSettingModel,
)
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase, Serializer

ThemeSettingType = ThemeSettingModel.generate_graphql_type()
AgentType = AgentModel.generate_graphql_type()


class CoordinationType(ObjectType):
    partition_key = String()
    coordination_uuid = String()
    endpoint_id = String()
    part_id = String()
    theme_uuid = String()
    theme = Field(lambda: ThemeSettingType)
    coordination_name = String()
    coordination_description = String()
    agents = List(AgentType)
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

        partition_key = getattr(parent, "partition_key", None)
        theme_uuid = getattr(parent, "theme_uuid", None)

        if not partition_key or not theme_uuid:
            return None

        return (
            ThemeSettingLoader(info=info)
            .load((partition_key, theme_uuid))
            .then(
                lambda theme_setting: (
                    ThemeSettingType(**Serializer.json_normalize(theme_setting))
                    if theme_setting
                    else None
                )
            )
        )

    @staticmethod
    def resolve_agents(parent, info):
        partition_key = getattr(parent, "partition_key", None)
        agent_uuids = getattr(parent, "agents", None) or []

        if not agent_uuids:
            return []

        if not partition_key:
            return []

        keys = [(partition_key, uuid) for uuid in agent_uuids]
        return AgentLoader(info=info).load_many(keys)


class CoordinationListType(ListObjectType):
    coordination_list = List(CoordinationType)
