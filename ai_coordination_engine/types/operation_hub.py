#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_utility import JSON


class AskOperationHubType(ObjectType):
    session = JSON()
    run_uuid = String()
    thread_uuid = String()
    agent_uuid = String()
    async_task_uuid = String()
    updated_at = DateTime()
