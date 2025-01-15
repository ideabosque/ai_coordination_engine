#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import coordination
from ..types.coordination import CoordinationListType, CoordinationType


def resolve_coordination(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> CoordinationType:
    return coordination.resolve_coordination(info, **kwargs)


def resolve_coordination_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> CoordinationListType:
    return coordination.resolve_coordination_list(info, **kwargs)
