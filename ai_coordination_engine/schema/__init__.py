#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import List, Type

from .query import Query
from .mutation import Mutations
from .types import type_class

__all__ = ["Query", "Mutations", "type_class"]
