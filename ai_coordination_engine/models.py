#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import os

from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import AllProjection, LocalSecondaryIndex

from silvaengine_dynamodb_base import BaseModel


class CoordinationModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-coordinations"

    coordination_type = UnicodeAttribute(hash_key=True)
    coordination_uuid = UnicodeAttribute(range_key=True)
    coordination_name = UnicodeAttribute()
    coordination_description = UnicodeAttribute()
    assistant_id = UnicodeAttribute()
    assistant_type = UnicodeAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


class CoordinationAgentModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-coordination_agents"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    agent_uuid = UnicodeAttribute(range_key=True)
    agent_name = UnicodeAttribute()
    agent_description = UnicodeAttribute()
    agent_instructions = UnicodeAttribute(null=True)
    agent_additional_instructions = UnicodeAttribute(null=True)
    coordination_type = UnicodeAttribute()
    response_format = UnicodeAttribute(null=True)
    predecessor = UnicodeAttribute(null=True)
    successor = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


class CoordinationSessionModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-coordination_sessions"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    session_uuid = UnicodeAttribute(range_key=True)
    coordination_type = UnicodeAttribute()
    thread_id = UnicodeAttribute()
    current_agent_uuid = UnicodeAttribute(null=True)
    last_assistant_message = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="initial")
    log = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


class CoordinationMessageModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-coordination_messages"

    session_uuid = UnicodeAttribute(hash_key=True)
    message_id = UnicodeAttribute(range_key=True)
    coordination_uuid = UnicodeAttribute()
    thread_id = UnicodeAttribute()
    agent_uuid = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
