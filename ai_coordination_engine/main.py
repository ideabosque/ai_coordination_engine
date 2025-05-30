#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from graphene import Schema

from silvaengine_dynamodb_base import SilvaEngineDynamoDBBase

from .handlers.config import Config
from .handlers.operation_hub import operation_hub_listener
from .handlers.procedure_hub import procedure_hub_listener
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
                            "action": "agent",
                            "label": "View Coordination Agent",
                        },
                        {
                            "action": "agentList",
                            "label": "View Coordination Agent List",
                        },
                        {
                            "action": "session",
                            "label": "View Coordination Session",
                        },
                        {
                            "action": "sessionList",
                            "label": "View Coordination Session List",
                        },
                        {
                            "action": "thread",
                            "label": "View Coordination Message",
                        },
                        {
                            "action": "threadList",
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
                            "action": "insertUpdateAgent",
                            "label": "Create Update Coordination Agent",
                        },
                        {
                            "action": "deleteAgent",
                            "label": "Delete Coordination Agent",
                        },
                        {
                            "action": "insertUpdateSession",
                            "label": "Create Update Coordination Session",
                        },
                        {
                            "action": "deleteSession",
                            "label": "Delete Coordination Session",
                        },
                        {
                            "action": "insertUpdateThread",
                            "label": "Create Update Coordination Message",
                        },
                        {
                            "action": "deleteThread",
                            "label": "Delete Coordination Message",
                        },
                    ],
                    "type": "RequestResponse",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": True,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "async_insert_update_session": {
                    "is_static": False,
                    "label": "Async Insert Update Session",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "async_execute_procedure_task_session": {
                    "is_static": False,
                    "label": "Async Execute Procedure Task Session",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "async_update_session_agent": {
                    "is_static": False,
                    "label": "Async Update Session Agent",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "async_orchestrate_task_query": {
                    "is_static": False,
                    "label": "Async Orchestrate Task Query",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
            },
        }
    ]


class AICoordinationEngine(SilvaEngineDynamoDBBase):
    def __init__(self, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        SilvaEngineDynamoDBBase.__init__(self, logger, **setting)

        # Initialize configuration via the Config class
        Config.initialize(logger, **setting)

        self.logger = logger
        self.setting = setting

    def async_insert_update_session(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##

        operation_hub_listener.async_insert_update_session(
            self.logger, self.setting, **params
        )
        return

    def async_execute_procedure_task_session(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##

        procedure_hub_listener.async_execute_procedure_task_session(
            self.logger, self.setting, **params
        )
        return

    def async_update_session_agent(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##

        procedure_hub_listener.async_update_session_agent(
            self.logger, self.setting, **params
        )
        return

    def async_orchestrate_task_query(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##

        procedure_hub_listener.async_orchestrate_task_query(
            self.logger, self.setting, **params
        )
        return

    def ai_coordination_graphql(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("connection_id") is None:
            params["connection_id"] = self.setting.pop("connection_id", None)
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##
        schema = Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )
        return self.graphql_execute(schema, **params)
