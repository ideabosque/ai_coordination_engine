#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..handlers import operation_hub
from ..types.operation_hub import AskOperationHubType


def resolve_ask_operation_hub(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AskOperationHubType:
    return operation_hub.ask_operation_hub(info, **kwargs)
