#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import List, ObjectType, String

from silvaengine_utility import JSON


class ProcedureTaskSessionType(ObjectType):
    session = JSON()
    session_agents = List(JSON)
