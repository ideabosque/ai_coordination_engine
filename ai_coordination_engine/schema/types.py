#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import List, Type

from ..types.coordination import CoordinationListType, CoordinationType
from ..types.operation_hub import AskOperationHubType
from ..types.session import SessionListType, SessionType
from ..types.session_agent import SessionAgentListType, SessionAgentType
from ..types.session_run import SessionRunListType, SessionRunType
from ..types.task import TaskListType, TaskType
from ..types.task_schedule import TaskScheduleListType, TaskScheduleType


def type_class() -> List[Type]:
    """Return a list of GraphQL types for schema registration."""
    return [
        CoordinationListType,
        SessionListType,
        SessionType,
        CoordinationType,
        TaskType,
        TaskListType,
        TaskScheduleType,
        TaskScheduleListType,
        SessionAgentType,
        SessionAgentListType,
        SessionRunType,
        SessionRunListType,
        AskOperationHubType,
    ]
