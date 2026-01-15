# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import os
from typing import Any, Dict, List

import boto3
from silvaengine_utility import Debugger, Graphql

from ..models import utils


class Config:
    """
    Centralized Configuration Class
    Manages shared configuration variables across the application.
    """

    aws_lambda = None
    aws_dynamodb = None
    aws_ses = None
    aws_s3 = None
    source_email = None
    schemas = {}
    module_bucket_name = None
    funct_zip_path = None
    funct_extract_path = None

    # Cache Configuration
    CACHE_TTL = 1800  # 30 minutes default TTL
    CACHE_ENABLED = True

    # Cache name patterns for different modules
    CACHE_NAMES = {
        "models": "ai_coordination_engine.models",
        "queries": "ai_coordination_engine.queries",
    }

    # Cache entity metadata (module paths, getters, cache key templates)
    CACHE_ENTITY_CONFIG = {
        "coordination": {
            "module": "ai_coordination_engine.models.coordination",
            "model_class": "CoordinationModel",
            "getter": "get_coordination",
            "list_resolver": "ai_coordination_engine.queries.coordination.resolve_coordination_list",
            "cache_keys": ["context:partition_key", "key:coordination_uuid"],
        },
        "session": {
            "module": "ai_coordination_engine.models.session",
            "model_class": "SessionModel",
            "getter": "get_session",
            "list_resolver": "ai_coordination_engine.queries.session.resolve_session_list",
            "cache_keys": ["key:coordination_uuid", "key:session_uuid"],
        },
        "session_agent": {
            "module": "ai_coordination_engine.models.session_agent",
            "model_class": "SessionAgentModel",
            "getter": "get_session_agent",
            "list_resolver": "ai_coordination_engine.queries.session_agent.resolve_session_agent_list",
            "cache_keys": ["key:session_uuid", "key:session_agent_uuid"],
        },
        "session_run": {
            "module": "ai_coordination_engine.models.session_run",
            "model_class": "SessionRunModel",
            "getter": "get_session_run",
            "list_resolver": "ai_coordination_engine.queries.session_run.resolve_session_run_list",
            "cache_keys": ["key:session_agent_uuid", "key:session_run_uuid"],
        },
        "task": {
            "module": "ai_coordination_engine.models.task",
            "model_class": "TaskModel",
            "getter": "get_task",
            "list_resolver": "ai_coordination_engine.queries.task.resolve_task_list",
            "cache_keys": ["key:coordination_uuid", "key:task_uuid"],
        },
        "task_schedule": {
            "module": "ai_coordination_engine.models.task_schedule",
            "model_class": "TaskScheduleModel",
            "getter": "get_task_schedule",
            "list_resolver": "ai_coordination_engine.queries.task_schedule.resolve_task_schedule_list",
            "cache_keys": ["key:coordination_uuid", "key:task_schedule_uuid"],
        },
    }

    @classmethod
    def get_cache_entity_config(cls) -> Dict[str, Dict[str, Any]]:
        """Get cache configuration metadata for each entity type."""
        return cls.CACHE_ENTITY_CONFIG

    # Entity cache dependency relationships
    CACHE_RELATIONSHIPS = {
        "coordination": [
            {
                "entity_type": "session",
                "list_resolver": "resolve_session_list",
                "module": "session",
                "dependency_key": "coordination_uuid",
            },
            {
                "entity_type": "task",
                "list_resolver": "resolve_task_list",
                "module": "task",
                "dependency_key": "coordination_uuid",
            },
            {
                "entity_type": "task_schedule",
                "list_resolver": "resolve_task_schedule_list",
                "module": "task_schedule",
                "dependency_key": "coordination_uuid",
            },
        ],
        "session": [
            {
                "entity_type": "session_agent",
                "list_resolver": "resolve_session_agent_list",
                "module": "session_agent",
                "dependency_key": "session_uuid",
            },
        ],
        "session_agent": [
            {
                "entity_type": "session_run",
                "list_resolver": "resolve_session_run_list",
                "module": "session_run",
                "dependency_key": "session_agent_uuid",
            },
        ],
        "task": [
            {
                "entity_type": "session",
                "list_resolver": "resolve_session_list",
                "module": "session",
                "dependency_key": "task_uuid",
            },
        ],
    }

    @classmethod
    def initialize(cls, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initialize configuration setting.
        Args:
            logger (logging.Logger): Logger instance for logging.
            **setting (Dict[str, Any]): Configuration dictionary.
        """
        try:
            cls._set_parameters(setting)
            cls._setup_function_paths(setting)
            cls._initialize_aws_services(setting)
            if setting.get("initialize_tables"):
                cls._initialize_tables(logger)
            logger.info("Configuration initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize configuration.")
            raise e

    @classmethod
    def _set_parameters(cls, setting: Dict[str, Any]) -> None:
        """
        Set application-level parameters.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        cls.source_email = setting.get("source_email")

    @classmethod
    def _setup_function_paths(cls, setting: Dict[str, Any]) -> None:
        cls.module_bucket_name = str(setting.get("module_bucket_name")).strip()
        cls.funct_zip_path = str(
            setting.get("funct_zip_path", "/tmp/funct_zips")
        ).strip()

        if not cls.funct_zip_path:
            cls.funct_zip_path = "/tmp/funct_zips"

        cls.funct_extract_path = str(
            setting.get("funct_extract_path", "/tmp/functs")
        ).strip()

        if not cls.funct_extract_path:
            cls.funct_extract_path = "/tmp/functs"

        os.makedirs(cls.funct_zip_path, exist_ok=True)
        os.makedirs(cls.funct_extract_path, exist_ok=True)

    @classmethod
    def _initialize_tables(cls, logger: logging.Logger) -> None:
        """
        Initialize database tables by calling the utils._initialize_tables() method.
        This is an internal method used during configuration setup.
        """
        utils._initialize_tables(logger)

    @classmethod
    def _initialize_aws_services(cls, setting: Dict[str, Any]) -> None:
        """
        Initialize AWS services, such as the S3 client.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        if all(
            setting.get(k)
            for k in ["region_name", "aws_access_key_id", "aws_secret_access_key"]
        ):
            aws_credentials = {
                "region_name": setting["region_name"],
                "aws_access_key_id": setting["aws_access_key_id"],
                "aws_secret_access_key": setting["aws_secret_access_key"],
            }
        else:
            aws_credentials = {}

        cls.aws_lambda = boto3.client("lambda", **aws_credentials)
        cls.dynamodb = boto3.resource("dynamodb", **aws_credentials)
        cls.aws_ses = boto3.client("ses", **aws_credentials)
        cls.aws_s3 = boto3.client("s3", **aws_credentials)

    @classmethod
    def get_cache_name(cls, module_type: str, model_name: str) -> str:
        """
        Generate standardized cache names.

        Args:
            module_type: 'models' or 'queries'
            model_name: Name of the model (e.g., 'coordination', 'session')

        Returns:
            Standardized cache name string
        """
        base_name = cls.CACHE_NAMES.get(
            module_type, f"ai_coordination_engine.{module_type}"
        )
        return f"{base_name}.{model_name}"

    @classmethod
    def get_cache_ttl(cls) -> int:
        """Get the configured cache TTL."""
        return cls.CACHE_TTL

    @classmethod
    def is_cache_enabled(cls) -> bool:
        """Check if caching is enabled."""
        return cls.CACHE_ENABLED

    @classmethod
    def get_cache_relationships(cls) -> Dict[str, List[Dict[str, str]]]:
        """Get entity cache dependency relationships."""
        return cls.CACHE_RELATIONSHIPS

    @classmethod
    def get_entity_children(cls, entity_type: str) -> List[Dict[str, str]]:
        """Get child entities for a specific entity type."""
        return cls.CACHE_RELATIONSHIPS.get(entity_type, [])

    # Fetches and caches GraphQL schema for a given function
    @classmethod
    def fetch_graphql_schema(
        cls,
        context: Dict[str, Any],
        function_name: str,
    ) -> Dict[str, Any]:
        """
        Fetches and caches a GraphQL schema for a given function.

        Args:
            logger: Logger instance for error reporting
            endpoint_id: ID of the endpoint to fetch schema from
            function_name: Name of function to get schema for
            setting: Optional settings dictionary

        Returns:
            Dict containing the GraphQL schema
        """
        Debugger.info(
            variable=context,
            stage=__name__,
            delimiter="#",
        )

        # Check if schema exists in cache, if not fetch and store it
        if Config.schemas.get(function_name) is None:
            Config.schemas[function_name] = Graphql.get_graphql_schema(
                context,
                function_name,
                aws_lambda=Config.aws_lambda,
            )
        return Config.schemas[function_name]
