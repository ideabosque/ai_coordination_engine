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
    additional_instructions = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


class AgentModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-agents"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    agent_uuid = UnicodeAttribute(range_key=True)
    agent_name = UnicodeAttribute()
    agent_instructions = UnicodeAttribute(null=True)
    coordination_type = UnicodeAttribute()
    response_format = UnicodeAttribute(null=True)
    json_schema = MapAttribute(null=True)
    tools = ListAttribute(null=True)
    predecessor = UnicodeAttribute(null=True)
    successor = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


class SessionModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-sessions"

    coordination_uuid = UnicodeAttribute(hash_key=True)
    session_uuid = UnicodeAttribute(range_key=True)
    coordination_type = UnicodeAttribute()
    status = UnicodeAttribute(default="initial")
    notes = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


class ThreadModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "ace-threads"

    session_uuid = UnicodeAttribute(hash_key=True)
    thread_id = UnicodeAttribute(range_key=True)
    coordination_uuid = UnicodeAttribute()
    agent_uuid = UnicodeAttribute(null=True)
    last_assistant_message = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="initial")
    log = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
