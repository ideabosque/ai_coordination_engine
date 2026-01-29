#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import os
import sys
import time
import traceback
import zipfile
from typing import Any, Callable, Dict, List, Optional

import humps
from boto3.dynamodb.conditions import Attr, Key
from graphene import ResolveInfo
from promise import Promise
from silvaengine_dynamodb_base.models import GraphqlSchemaModel
from silvaengine_utility import Debugger, Graphql, Invoker, Serializer

from .config import Config


def execute_graphql_query(
    context: Dict[str, Any],
    function_name: str,
    operation_name: str,
    operation_type: str,
    variables: Dict[str, Any],
) -> Dict[str, Any]:
    schema = Config.fetch_graphql_schema(context, function_name)
    result = Graphql.execute_graphql_query(
        context,
        function_name,
        Graphql.generate_graphql_operation(operation_name, operation_type, schema),
        variables,
        aws_lambda=Config.aws_lambda,
    )

    return result


def _module_exists(logger: logging.Logger, module_name: str) -> bool:
    """Check if the module exists in the specified path."""
    module_dir = os.path.join(Config.funct_extract_path, module_name)
    if os.path.exists(module_dir) and os.path.isdir(module_dir):
        logger.info(f"Module {module_name} found in {Config.funct_extract_path}.")
        return True
    logger.info(f"Module {module_name} not found in {Config.funct_extract_path}.")
    return False


def _download_and_extract_module(logger: logging.Logger, module_name: str) -> None:
    """Download and extract the module from S3 if not already extracted."""
    key = f"{module_name}.zip"
    zip_path = f"{Config.funct_zip_path}/{key}"

    logger.info(
        f"Downloading module from S3: bucket={Config.module_bucket_name}, key={key}"
    )
    Config.aws_s3.download_file(Config.module_bucket_name, key, zip_path)
    logger.info(f"Downloaded {key} from S3 to {zip_path}")

    # Extract the ZIP file
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(Config.funct_extract_path)
    logger.info(f"Extracted module to {Config.funct_extract_path}")


def get_action_function(
    info: ResolveInfo, action_function: Dict[str, Any]
) -> Optional[Callable]:
    try:
        module_name = action_function["module_name"]
        function_name = action_function["function_name"]
        if not _module_exists(info.context["logger"], module_name):
            # Download and extract the module if it doesn't exist
            _download_and_extract_module(info.context["logger"], module_name)

        # Add the extracted module to sys.path
        module_path = f"{Config.funct_extract_path}/{module_name}"
        if module_path not in sys.path:
            sys.path.append(module_path)

        return getattr(__import__(module_name), function_name)

    except Exception as e:
        log = traceback.format_exc()
        info.context["logger"].error(log)
        raise e


def invoke_ask_model(
    context: Dict[str, Any],
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Call AI model for assistance via GraphQL query."""
    try:
        query = GraphqlSchemaModel.get_schema(
            endpoint_id=context.get("endpoint_id"),
            operation_type="Query",
            operation_name="askModel",
            module_name="ai_agent_core_engine",
        )

        return humps.decamelize(
            Graphql.request_graphql(
                context=context,
                module_name="ai_agent_core_engine",
                function_name="ai_agent_core_graphql",
                class_name="AIAgentCoreEngine",
                operation_name="askModel",
                variables=variables,
                # operation_type="Query",
                query=query,
            )
        )
    except Exception as e:
        Debugger.info(
            variable=e,
            stage=__name__,
            logger=context.get("logger"),
            setting=context.get("setting"),
        )
        raise


def get_async_task(
    context: Dict[str, Any],
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Call AI model for assistance via GraphQL query."""
    async_task = Graphql.request_graphql(
        context=context,
        module_name="ai_agent_core_engine",
        function_name="ai_agent_core_graphql",
        # operation_type="Query",
        operation_name="asyncTask",
        class_name="AIAgentCoreEngine",
        variables=variables,
    )

    if isinstance(async_task, dict) and "asyncTask" in async_task:
        async_task = async_task.get("asyncTask", {})

    # async_task = execute_graphql_query(
    #     context,
    #     "ai_agent_core_graphql",
    #     "asyncTask",
    #     "Query",
    #     variables,
    # )["asyncTask"]
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


# ============================================================================
# Nested Resolver Helper Functions
# ============================================================================
# These functions provide safe access to nested resolver properties that may
# be either embedded dicts (legacy/listener mode) or GraphQL types with
# lazy-loaded nested resolvers.
#
# Usage Pattern:
# - For FK access: Use direct properties (session.coordination_uuid, session.task_uuid)
# - For nested data: Use ensure_* functions (coordination.agents, task.agent_actions)
# - For batch operations: Use batch_get_* functions to load multiple entities efficiently
# ============================================================================


# ============================================================================
# Batch Loader Helper Functions
# ============================================================================
# These functions use DataLoader for efficient batch loading when processing
# multiple sessions. They eliminate N+1 query problems by loading all needed
# coordinations/tasks in a single query.
# ============================================================================


def batch_get_coordination_data(
    sessions: List, info: ResolveInfo
) -> Dict[str, Dict[str, Any]]:
    """
    Batch load coordination data for multiple sessions using DataLoader.

    This is efficient for processing lists of sessions (e.g., in list queries)
    as it loads all coordinations in a single query instead of N queries.

    Args:
        sessions: List of SessionType objects
        info: GraphQL resolve info containing context with DataLoaders

    Returns:
        Dict mapping coordination_uuid -> coordination data dict

    Example:
        sessions = resolve_session_list(...)
        coord_map = batch_get_coordination_data(sessions, info)
        for session in sessions:
            coord_data = coord_map[session.coordination_uuid]
    """
    from ..models.batch_loaders import get_loaders

    # Collect all unique coordination keys needed using direct property access
    coordination_keys = set()
    for session in sessions:
        coordination_uuid = getattr(session, "coordination_uuid", None)
        partition_key = getattr(session, "partition_key", None)

        if coordination_uuid and partition_key:
            coordination_keys.add((partition_key, coordination_uuid))

    if not coordination_keys:
        return {}

    # Use DataLoader to batch fetch all coordinations
    loaders = get_loaders(info.context)
    coordination_promises = {
        (partition_key, coord_uuid): loaders.coordination_loader.load(
            (partition_key, coord_uuid)
        )
        for partition_key, coord_uuid in coordination_keys
    }

    # Resolve all promises and build result map
    result = {}
    for key, promise in coordination_promises.items():
        coord_dict = promise.get()  # Synchronously wait for DataLoader result
        if coord_dict:
            result[key[1]] = coord_dict  # Key by coordination_uuid only

    return result


def batch_get_task_data(sessions: List, info: ResolveInfo) -> Dict[str, Dict[str, Any]]:
    """
    Batch load task data for multiple sessions using DataLoader.

    This is efficient for processing lists of sessions as it loads all tasks
    in a single query instead of N queries.

    Args:
        sessions: List of SessionType objects
        info: GraphQL resolve info containing context with DataLoaders

    Returns:
        Dict mapping task_uuid -> task data dict (with nested coordination)

    Example:
        sessions = resolve_session_list(...)
        task_map = batch_get_task_data(sessions, info)
        for session in sessions:
            task_data = task_map[session.task_uuid]
            agent_actions = task_data.get("agent_actions", {})
    """
    from ..models.batch_loaders import get_loaders

    # Collect all unique task keys needed using direct property access
    task_keys = set()
    for session in sessions:
        task_uuid = getattr(session, "task_uuid", None)
        partition_key = getattr(session, "partition_key", None)

        if task_uuid and partition_key:
            task_keys.add((partition_key, task_uuid))

    if not task_keys:
        return {}

    # Use DataLoader to batch fetch all tasks
    loaders = get_loaders(info.context)
    task_promises = {
        (partition_key, task_uuid): loaders.task_loader.load((partition_key, task_uuid))
        for partition_key, task_uuid in task_keys
    }

    # Resolve all promises and build result map
    result = {}
    for key, promise in task_promises.items():
        task_dict = promise.get()  # Synchronously wait for DataLoader result
        if task_dict:
            result[key[1]] = task_dict  # Key by task_uuid only

    return result


# ============================================================================
# Smart Ensure Functions
# ============================================================================
# These functions automatically choose the best method to get data based on
# context. They use batch loading when info is available, fall back to simple
# extraction otherwise.
# ============================================================================


def ensure_coordination_data(session, info: ResolveInfo = None) -> Dict[str, Any]:
    """
    Smart function that automatically chooses best method to get coordination data.

    This function has a 4-path fallback strategy:
    1. If coordination is already embedded dict -> return directly
    2. If coordination is GraphQL type -> extract to dict
    3. If info is provided -> use DataLoader for batch efficiency
    4. Otherwise -> use foreign keys only (minimal dict)

    Args:
        session: SessionType object
        info: Optional GraphQL resolve info (enables batch loading)

    Returns:
        Dict containing coordination data

    Example:
        # In GraphQL resolver (has info):
        coord_data = ensure_coordination_data(session, info)

        # In listener/async function (no info):
        coord_data = ensure_coordination_data(session)
    """
    coordination = getattr(session, "coordination", None)

    # Path 1: Already embedded dict
    if isinstance(coordination, dict):
        return coordination

    # Path 2: GraphQL type available
    if coordination is not None and hasattr(coordination, "coordination_uuid"):
        return {
            "coordination_uuid": coordination.coordination_uuid,
            "endpoint_id": coordination.endpoint_id,
            "partition_key": getattr(coordination, "partition_key", None),
            "coordination_name": coordination.coordination_name,
            "coordination_description": getattr(
                coordination, "coordination_description", None
            ),
            "agents": getattr(coordination, "agents", []),
        }

    # Path 3: Use batch loader if info available
    if info is not None:
        from ..models.batch_loaders import get_loaders

        coordination_uuid = getattr(session, "coordination_uuid", None)
        endpoint_id = getattr(session, "endpoint_id", None)
        if coordination_uuid and endpoint_id:
            loaders = get_loaders(info.context)
            coord_dict = loaders.coordination_loader.load(
                (endpoint_id, coordination_uuid)
            ).get()
            if coord_dict:
                return coord_dict

    # Path 4: Fallback to minimal dict with FKs
    return {
        "coordination_uuid": getattr(session, "coordination_uuid", None),
        "endpoint_id": getattr(session, "endpoint_id", None),
        "agents": [],
    }


def _normalize_task_object(task) -> Dict[str, Any]:
    task_dict = {
        "task_uuid": task.task_uuid,
        "task_name": getattr(task, "task_name", None),
        "task_description": getattr(task, "task_description", None),
        "agent_actions": getattr(task, "agent_actions", {}),
        "subtask_queries": getattr(task, "subtask_queries", []),
    }

    # Forward basic properties for coordination resolution
    for attr in ["coordination_uuid", "endpoint_id"]:
        val = getattr(task, attr, None)
        if val is not None:
            task_dict[attr] = val

    # Handle nested coordination within task
    coordination = getattr(task, "coordination", None)
    if isinstance(coordination, Promise):
        coordination = coordination.get()

    if isinstance(coordination, dict):
        task_dict["coordination"] = coordination
    elif coordination is not None and hasattr(coordination, "coordination_uuid"):
        task_dict["coordination"] = {
            "coordination_uuid": coordination.coordination_uuid,
            "endpoint_id": coordination.endpoint_id,
            "agents": getattr(coordination, "agents", []),
        }

    return task_dict


def _load_task_from_loader(session, info) -> Optional[Dict[str, Any]]:
    from ..models.batch_loaders import get_loaders

    task_uuid = getattr(session, "task_uuid", None)
    coordination_uuid = getattr(session, "coordination_uuid", None)
    if task_uuid and coordination_uuid:
        loaders = get_loaders(info.context)
        return loaders.task_loader.load((coordination_uuid, task_uuid)).get()
    return None


def _create_fallback_task(session) -> Dict[str, Any]:
    return {
        "task_uuid": getattr(session, "task_uuid", None),
        "agent_actions": {},
        "subtask_queries": [],
        "coordination": {
            "coordination_uuid": getattr(session, "coordination_uuid", None),
            "agents": [],
        },
    }


def _resolve_coordination(session, task_dict, info) -> Dict[str, Any]:
    coord_uuid = task_dict.get("coordination_uuid") or getattr(
        session, "coordination_uuid", None
    )
    partition_key = task_dict.get("partition_key") or getattr(
        session, "partition_key", None
    )

    if info is not None and coord_uuid and partition_key:
        from ..models.batch_loaders import get_loaders

        loaders = get_loaders(info.context)
        coord_dict = loaders.coordination_loader.load((partition_key, coord_uuid)).get()
        if coord_dict:
            return coord_dict

    return {
        "coordination_uuid": coord_uuid,
        "partition_key": partition_key
        or (info.context.get("partition_key") if info else None),
        "agents": [],
    }


def ensure_task_data(session, info: ResolveInfo = None) -> Dict[str, Any]:
    """
    Smart function that automatically chooses best method to get task data.

    This function has a 4-path fallback strategy:
    1. If task is already embedded dict -> return directly
    2. If task is GraphQL type -> extract to dict (with nested coordination)
    3. If info is provided -> use DataLoader for batch efficiency
    4. Otherwise -> use foreign keys only (minimal dict)

    Args:
        session: SessionType object
        info: Optional GraphQL resolve info (enables batch loading)

    Returns:
        Dict containing task data (with nested coordination dict)

    Example:
        # In GraphQL resolver (has info):
        task_data = ensure_task_data(session, info)

        # In listener/async function (no info):
        task_data = ensure_task_data(session)
        agent_actions = task_data.get("agent_actions", {})
    """
    task = getattr(session, "task", None)

    # Handle Promise objects (from lazy GraphQL resolvers)
    if isinstance(task, Promise):
        task = task.get()  # Synchronously resolve the promise

    task_dict = None

    # Path 1: Already embedded dict
    if isinstance(task, dict):
        task_dict = task

    # Path 2: GraphQL type available
    elif task is not None and hasattr(task, "task_uuid"):
        task_dict = _normalize_task_object(task)

    # Path 3: Use batch loader if info available
    elif info is not None:
        task_dict = _load_task_from_loader(session, info)

    # Path 4: Fallback to minimal dict with FKs
    if task_dict is None:
        task_dict = _create_fallback_task(session)

    # Ensure coordination is nested
    if "coordination" not in task_dict:
        task_dict["coordination"] = _resolve_coordination(session, task_dict, info)

    return task_dict
