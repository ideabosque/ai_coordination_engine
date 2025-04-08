#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import ObjectType, String


class ProcedureTaskSessionType(ObjectType):
    coordination_uuid = String()
    session_uuid = String()
    task_uuid = String()
    user_id = String()
    task_query = String()
