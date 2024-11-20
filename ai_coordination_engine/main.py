#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from graphene import Schema
from silvaengine_dynamodb_base import SilvaEngineDynamoDBBase

from .handlers import handlers_init
from .schema import Mutations, Query, type_class


# Hook function applied to deployment
def deploy() -> List:
    return [
        {
            "service": "AI Assistant",
            "class": "AICoordinationEngine",
            "functions": {
                "ai_coordination_graphql": {
                    "is_static": False,
                    "label": "AI Coordination GraphQL",
                    "query": [
                        {"action": "ping", "label": "Ping"},
                        {
                            "action": "coordination",
                            "label": "View Coordination",
                        },
                        {
                            "action": "coordinationList",
                            "label": "View Coordination List",
                        },
                        {
                            "action": "coordinationAgent",
                            "label": "View Coordination Agent",
                        },
                        {
                            "action": "coordinationAgentList",
                            "label": "View Coordination Agent List",
                        },
                        {
                            "action": "coordinationSession",
                            "label": "View Coordination Session",
                        },
                        {
                            "action": "coordinationSessionList",
                            "label": "View Coordination Session List",
                        },
                        {
                            "action": "coordinationMessage",
                            "label": "View Coordination Message",
                        },
                        {
                            "action": "coordinationMessageList",
                            "label": "View Coordination Message List",
                        },
                    ],
                    "mutation": [
                        {
                            "action": "insertUpdateCoordination",
                            "label": "Create Update Coordination",
                        },
                        {
                            "action": "deleteCoordination",
                            "label": "Delete Coordination",
                        },
                        {
                            "action": "insertUpdateCoordinationAgent",
                            "label": "Create Update Coordination Agent",
                        },
                        {
                            "action": "deleteCoordinationAgent",
                            "label": "Delete Coordination Agent",
                        },
                        {
                            "action": "insertUpdateCoordinationSession",
                            "label": "Create Update Coordination Session",
                        },
                        {
                            "action": "deleteCoordinationSession",
                            "label": "Delete Coordination Session",
                        },
                        {
                            "action": "insertUpdateCoordinationMessage",
                            "label": "Create Update Coordination Message",
                        },
                        {
                            "action": "deleteCoordinationMessage",
                            "label": "Delete Coordination Message",
                        },
                    ],
                    "type": "RequestResponse",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": True,
                    "settings": "ai_coordination_engine",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
            },
        }
    ]


class AICoordinationEngine(SilvaEngineDynamoDBBase):
    def __init__(self, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        handlers_init(logger, **setting)

        self.logger = logger
        self.setting = setting

        SilvaEngineDynamoDBBase.__init__(self, logger, **setting)

    def ai_coordination_graphql(self, **params: Dict[str, Any]) -> Any:
        schema = Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )
        return self.graphql_execute(schema, **params)
