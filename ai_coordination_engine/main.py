#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from graphene import Schema
from silvaengine_dynamodb_base import BaseModel
from silvaengine_utility import Graphql

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


class AICoordinationEngine(Graphql):
    def __init__(self, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        Graphql.__init__(self, logger, **setting)

        if (
            setting.get("region_name")
            and setting.get("aws_access_key_id")
            and setting.get("aws_secret_access_key")
        ):
            BaseModel.Meta.region = setting.get("region_name")
            BaseModel.Meta.aws_access_key_id = setting.get("aws_access_key_id")
            BaseModel.Meta.aws_secret_access_key = setting.get("aws_secret_access_key")

        # Initialize configuration via the Config class
        Config.initialize(logger, **setting)

        self.logger = logger
        self.setting = setting

    def _apply_partition_defaults(self, params: Dict[str, Any]) -> None:
        """
        Apply default partition values if not provided in params.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to build the GraphQL query.
        """
        endpoint_id = params.get("endpoint_id", self.setting.get("endpoint_id"))
        part_id = params.get("custom_headers", {}).get(
            "part_id",
            params.get("part_id", self.setting.get("part_id")),
        )

        if params.get("context") is None:
            params["context"] = {}

        if "partition_key" not in params["context"]:
            params["context"]["partition_key"] = f"{endpoint_id}#{part_id}"

        exclude = ["logger", "setting"]

        for index in exclude:
            if index in params:
                params.pop(index)

    def async_insert_update_session(self, **params: Dict[str, Any]) -> Any:
        self._apply_partition_defaults(params)

        operation_hub_listener.async_insert_update_session(
            self.logger, self.setting, **params
        )
        return

    def async_execute_procedure_task_session(self, **params: Dict[str, Any]) -> Any:
        self._apply_partition_defaults(params)

        procedure_hub_listener.async_execute_procedure_task_session(
            self.logger, self.setting, **params
        )
        return

    def async_update_session_agent(self, **params: Dict[str, Any]) -> Any:
        self._apply_partition_defaults(params)

        procedure_hub_listener.async_update_session_agent(
            self.logger, self.setting, **params
        )
        return

    def async_orchestrate_task_query(self, **params: Dict[str, Any]) -> Any:
        self._apply_partition_defaults(params)

        procedure_hub_listener.async_orchestrate_task_query(
            self.logger, self.setting, **params
        )
        return

    def ai_coordination_graphql(self, **params: Dict[str, Any]) -> Any:
        if params.get("connection_id") is None:
            params["connection_id"] = self.setting.get("connection_id", None)

        self._apply_partition_defaults(params)

        return self.execute(self.__class__.build_graphql_schema(), **params)

    @staticmethod
    def build_graphql_schema() -> Schema:
        return Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )
