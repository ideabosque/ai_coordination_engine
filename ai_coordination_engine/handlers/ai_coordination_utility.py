#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict, Optional

import humps
from boto3.dynamodb.conditions import Attr, Key
from graphene import ResolveInfo

from silvaengine_utility import Utility

from .config import Config


def create_listener_info(
    logger: logging.Logger,
    field_name: str,
    setting: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> ResolveInfo:
    # Minimal example: some parameters can be None if you're only testing
    info = ResolveInfo(
        field_name=field_name,
        field_asts=[],  # or [some_field_node]
        return_type=None,  # e.g., GraphQLString
        parent_type=None,  # e.g., schema.get_type("Query")
        schema=None,  # your GraphQLSchema
        fragments={},
        root_value=None,
        operation=None,
        variable_values={},
        context={
            "setting": setting,
            "endpoint_id": kwargs.get("endpoint_id"),
            "logger": logger,
            "connectionId": kwargs.get("connection_id"),
        },
        path=None,
    )
    return info


def execute_graphql_query(
    logger: logging.Logger,
    endpoint_id: str,
    function_name: str,
    operation_name: str,
    operation_type: str,
    variables: Dict[str, Any],
    setting: Dict[str, Any] = {},
    connection_id: str = None,
) -> Dict[str, Any]:
    schema = Config.fetch_graphql_schema(
        logger, endpoint_id, function_name, setting=setting
    )
    result = Utility.execute_graphql_query(
        logger,
        endpoint_id,
        function_name,
        Utility.generate_graphql_operation(operation_name, operation_type, schema),
        variables,
        setting=setting,
        aws_lambda=Config.aws_lambda,
        connection_id=connection_id,
        test_mode=setting.get("test_mode"),
    )
    return result


def invoke_ask_model(
    logger: logging.Logger,
    endpoint_id: str,
    setting: Dict[str, Any] = None,
    connection_id: str = None,
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Call AI model for assistance via GraphQL query."""
    ask_model = execute_graphql_query(
        logger,
        endpoint_id,
        "ai_agent_core_graphql",
        "askModel",
        "Query",
        variables,
        setting=setting,
        connection_id=connection_id,
    )["askModel"]
    return humps.decamelize(ask_model)


def get_async_task(
    logger: logging.Logger,
    endpoint_id: str,
    setting: Dict[str, Any] = None,
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Call AI model for assistance via GraphQL query."""
    async_task = execute_graphql_query(
        logger,
        endpoint_id,
        "ai_agent_core_graphql",
        "asyncTask",
        "Query",
        variables,
        setting=setting,
    )["asyncTask"]
    return humps.decamelize(async_task)


# Updated function to use Boto3 to get the latest connection by email without an index
def get_connection_by_email(
    logger: logging.Logger, endpoint_id: str, email: str
) -> Optional[Dict]:
    """
    Retrieve the latest connection by email from DynamoDB without relying on an index.

    Args:
        logger: Logging object
        endpoint_id: Endpoint identifier
        email: Email to search for

    Returns:
        Dict containing connection information or None if not found
    """
    try:
        table = Config.aws_dynamodb.Table("se-wss-connections")

        # Query without using an index
        response = table.query(
            KeyConditionExpression=Key("endpoint_id").eq(endpoint_id),
            FilterExpression=Attr("data.email").eq(email) & Attr("status").eq("active"),
        )

        connections = response.get("Items", [])

        # Sort connections manually by 'updated_at' if present
        latest_connection = None
        if connections:
            latest_connection = max(
                connections,
                key=lambda conn: conn.get("updated_at", "1970-01-01T00:00:00Z"),
            )

        if latest_connection:
            return {
                "connection_id": latest_connection["connection_id"],
                "data": latest_connection.get("data", {}),
            }

        logger.info(f"No active connection found for email: {email}")
        return None

    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e


def send_email(
    logger: logging.Logger, receiver_email: str, subject: str, body: str
) -> None:
    """Send an email with the given subject and body to the receiver's email address using AWS SES."""
    try:
        response = Config.aws_ses.send_email(
            Source=Config.source_email,
            Destination={
                "ToAddresses": [receiver_email],
            },
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )
        logger.info(f"Email sent to: {receiver_email}")
    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e
