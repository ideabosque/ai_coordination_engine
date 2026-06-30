# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import os
from typing import Any, Dict, List
from urllib.parse import quote_plus

import boto3
from silvaengine_dynamodb_base.models import FunctionModel
from silvaengine_utility import Debugger, Graphql


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

    # Dual-backend selection
    DB_BACKEND = "dynamodb"
    db_session = None  # PostgreSQL scoped_session (only set in PG mode)
    _db_engine = None
    PG_TABLE_PREFIX = ""

    # Cache Configuration
    CACHE_TTL = 1800  # 30 minutes default TTL
    CACHE_ENABLED = True

    # Timeout Configuration (in seconds)
    GRAPHQL_TIMEOUT = 30  # Default timeout for GraphQL requests
    ASYNC_TASK_TIMEOUT = 60  # Timeout for async task polling

    # Cache name patterns for different modules
    CACHE_NAMES = {
        "models": "ai_coordination_engine.models",
        "queries": "ai_coordination_engine.queries",
    }

    # Cache entity metadata — DynamoDB variant (module paths point to models.dynamodb.*)
    CACHE_ENTITY_CONFIG_DYNAMODB = {
        "coordination": {
            "module": "ai_coordination_engine.models.dynamodb.coordination",
            "model_class": "CoordinationModel",
            "getter": "get_coordination",
            "list_resolver": "ai_coordination_engine.queries.coordination.resolve_coordination_list",
            "cache_keys": ["context:partition_key", "key:coordination_uuid"],
        },
        "session": {
            "module": "ai_coordination_engine.models.dynamodb.session",
            "model_class": "SessionModel",
            "getter": "get_session",
            "list_resolver": "ai_coordination_engine.queries.session.resolve_session_list",
            "cache_keys": ["key:coordination_uuid", "key:session_uuid"],
        },
        "session_agent": {
            "module": "ai_coordination_engine.models.dynamodb.session_agent",
            "model_class": "SessionAgentModel",
            "getter": "get_session_agent",
            "list_resolver": "ai_coordination_engine.queries.session_agent.resolve_session_agent_list",
            "cache_keys": ["key:session_uuid", "key:session_agent_uuid"],
        },
        "session_run": {
            "module": "ai_coordination_engine.models.dynamodb.session_run",
            "model_class": "SessionRunModel",
            "getter": "get_session_run",
            "list_resolver": "ai_coordination_engine.queries.session_run.resolve_session_run_list",
            "cache_keys": ["key:session_agent_uuid", "key:session_run_uuid"],
        },
        "task": {
            "module": "ai_coordination_engine.models.dynamodb.task",
            "model_class": "TaskModel",
            "getter": "get_task",
            "list_resolver": "ai_coordination_engine.queries.task.resolve_task_list",
            "cache_keys": ["key:coordination_uuid", "key:task_uuid"],
        },
        "task_schedule": {
            "module": "ai_coordination_engine.models.dynamodb.task_schedule",
            "model_class": "TaskScheduleModel",
            "getter": "get_task_schedule",
            "list_resolver": "ai_coordination_engine.queries.task_schedule.resolve_task_schedule_list",
            "cache_keys": ["key:coordination_uuid", "key:task_schedule_uuid"],
        },
    }

    # PostgreSQL cache config — empty because PG repos don't use @method_cache
    CACHE_ENTITY_CONFIG_POSTGRESQL: Dict[str, Dict[str, Any]] = {}

    # Entity cache dependency relationships — DynamoDB variant
    CACHE_RELATIONSHIPS_DYNAMODB = {
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

    # PostgreSQL cache relationships — empty
    CACHE_RELATIONSHIPS_POSTGRESQL: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def get_cache_entity_config(cls) -> Dict[str, Dict[str, Any]]:
        """Get cache configuration metadata for each entity type."""
        if cls.DB_BACKEND == "postgresql":
            return cls.CACHE_ENTITY_CONFIG_POSTGRESQL
        return cls.CACHE_ENTITY_CONFIG_DYNAMODB

    @classmethod
    def get_cache_relationships(cls) -> Dict[str, List[Dict[str, str]]]:
        """Get entity cache dependency relationships."""
        if cls.DB_BACKEND == "postgresql":
            return cls.CACHE_RELATIONSHIPS_POSTGRESQL
        return cls.CACHE_RELATIONSHIPS_DYNAMODB

    @classmethod
    def initialize(cls, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initialize configuration setting.
        Args:
            logger (logging.Logger): Logger instance for logging.
            **setting (Dict[str, Any]): Configuration keyword arguments.
        """
        try:
            cls._set_parameters(setting)
            cls._setup_function_paths(setting)

            # Backend selection
            cls.DB_BACKEND = str(setting.get("db_backend", "dynamodb")).lower()
            if cls.DB_BACKEND not in ("dynamodb", "postgresql"):
                raise ValueError(f"Unknown db_backend: {cls.DB_BACKEND}")

            cls.PG_TABLE_PREFIX = str(setting.get("pg_table_prefix", ""))

            if cls.DB_BACKEND == "dynamodb":
                cls._initialize_aws_services(setting)
                cls._initialize_dynamodb_meta(setting)
            else:
                cls._initialize_optional_aws_services(setting)
                cls._initialize_db_session(setting)

            if setting.get("initialize_tables"):
                cls._initialize_tables(logger)
            logger.info("Configuration initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize configuration.")
            raise e

    @classmethod
    def _set_parameters(cls, setting: Dict[str, Any]) -> None:
        """Set application-level parameters."""
        cls.source_email = setting.get("source_email")

        if "cache_enabled" in setting:
            cls.CACHE_ENABLED = setting.get("cache_enabled", True)

        if "graphql_timeout" in setting:
            cls.GRAPHQL_TIMEOUT = int(setting.get("graphql_timeout", cls.GRAPHQL_TIMEOUT))

        if "async_task_timeout" in setting:
            cls.ASYNC_TASK_TIMEOUT = int(
                setting.get("async_task_timeout", cls.ASYNC_TASK_TIMEOUT)
            )

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
    def _initialize_dynamodb_meta(cls, setting: Dict[str, Any]) -> None:
        """Set PynamoDB BaseModel.Meta credentials from the setting."""
        from silvaengine_dynamodb_base import BaseModel

        if (
            setting.get("region_name")
            and setting.get("aws_access_key_id")
            and setting.get("aws_secret_access_key")
        ):
            BaseModel.Meta.region = setting.get("region_name")
            BaseModel.Meta.aws_access_key_id = setting.get("aws_access_key_id")
            BaseModel.Meta.aws_secret_access_key = setting.get("aws_secret_access_key")

    @classmethod
    def _initialize_aws_services(cls, setting: Dict[str, Any]) -> None:
        """Initialize AWS services (Lambda, DynamoDB, SES, S3) — DynamoDB mode."""
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
    def _initialize_optional_aws_services(cls, setting: Dict[str, Any]) -> None:
        """Initialize AWS services only when credentials are present — PG mode.

        ACE uses Lambda for async dispatch, S3 for module downloads, SES for email,
        and DynamoDB for FunctionModel (shared platform table). These are likely
        mandatory even in PG mode, so we build the clients when creds are available.
        """
        creds_present = all(
            setting.get(k)
            for k in ["region_name", "aws_access_key_id", "aws_secret_access_key"]
        )
        if creds_present:
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
    def _initialize_db_session(cls, setting: Dict[str, Any]) -> None:
        """Initialize PostgreSQL SQLAlchemy scoped_session."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import scoped_session, sessionmaker

        # DATABASE_URL takes precedence over individual PG_* vars
        database_url = setting.get("database_url")
        if database_url:
            connection_string = database_url
        else:
            password = quote_plus(str(setting.get("db_password", "")))
            connection_string = (
                f"postgresql+psycopg2://{setting.get('db_user', 'silvaengine')}:{password}"
                f"@{setting.get('db_host', 'localhost')}:{setting.get('db_port', '5432')}"
                f"/{setting.get('db_schema', 'silvaengine')}"
            )

        engine = create_engine(
            connection_string,
            pool_recycle=7200,
            pool_size=10,
            pool_pre_ping=True,
            echo=False,
        )
        cls.db_session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=engine)
        )
        cls._db_engine = engine

    @classmethod
    def _initialize_tables(cls, logger: logging.Logger) -> None:
        """Initialize database tables — dispatched by backend."""
        if cls.DB_BACKEND == "dynamodb":
            from ..models.dynamodb.utils import initialize_tables
            initialize_tables(logger)
        elif cls.DB_BACKEND == "postgresql":
            from ..models.postgresql.utils import initialize_tables as pg_init
            pg_init(logger, cls.db_session, cls._db_engine)

    @classmethod
    def _set_rls_context(cls, partition_key: str) -> None:
        """Set the RLS tenant context for the current PostgreSQL session."""
        if cls.DB_BACKEND == "postgresql" and cls.db_session:
            from sqlalchemy import text
            cls.db_session.execute(
                text("SET LOCAL app.tenant_id = :tenant"),
                {"tenant": partition_key},
            )

    @classmethod
    def get_cache_name(cls, module_type: str, model_name: str) -> str:
        """Generate standardized cache names."""
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
    def get_entity_children(cls, entity_type: str) -> List[Dict[str, str]]:
        """Get child entities for a specific entity type."""
        return cls.get_cache_relationships().get(entity_type, [])

    # Fetches and caches GraphQL schema for a given function
    @classmethod
    def fetch_graphql_schema(
        cls,
        context: Dict[str, Any],
        function_name: str,
    ) -> Dict[str, Any]:
        """
        Fetches and caches a GraphQL schema for a given function.
        """
        function_name = str(function_name).strip()

        if (
            not isinstance(context, dict)
            or not function_name
            or "aws_lambda_arn" not in context
        ):
            raise Exception("Invalid required parameter(s)")

        if Config.schemas.get(function_name) is None:
            function = FunctionModel.get(
                hash_key=context.get("aws_lambda_arn"),
                range_key=function_name,
            )

            if (
                not hasattr(function.config, "module_name")
                or not hasattr(function.config, "class_name")
                or not hasattr(function, "function")
            ):
                raise ValueError("Missing function config")

            try:
                Config.schemas[function_name] = Graphql.get_graphql_schema(
                    module_name=function.config.module_name,
                    class_name=function.config.class_name,
                )
            except Exception as e:
                Debugger.info(
                    variable=e,
                    stage=f"{__name__}(fetch_graphql_schema)",
                    delimiter="#",
                )
                raise e
        return Config.schemas[function_name]