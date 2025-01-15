#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import thread
from ..types.thread import ThreadListType, ThreadType


def resolve_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType:
    return thread.resolve_thread(info, **kwargs)


def resolve_thread_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadListType:
    return thread.resolve_thread_list(info, **kwargs)
