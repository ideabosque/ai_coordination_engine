#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Schema module for AI Coordination Engine.

This module re-exports the schema components from the schema package
for backward compatibility.
"""
from __future__ import print_function

__author__ = "bibow"

from .schema.query import Query
from .schema.mutation import Mutations
from .schema.types import type_class

__all__ = ["Query", "Mutations", "type_class"]
