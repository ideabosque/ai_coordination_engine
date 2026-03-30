#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared decorators for AI Coordination Engine models.

This module provides reusable decorators to eliminate code duplication
across model files, particularly for cache purging functionality.
"""
from __future__ import print_function

__author__ = "bibow"

import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def _extract_entity_keys(
    args: tuple,
    kwargs: dict,
    key_fields: List[str],
    entity_param_name: str = "entity"
) -> Dict[str, Any]:
    """Extract entity keys from function arguments.
    
    This helper function extracts entity identification keys from either
    the entity parameter (for updates) or kwargs (for creates/deletes).
    
    Args:
        args: Function positional arguments (args[0] should be info)
        kwargs: Function keyword arguments
        key_fields: List of field names to extract
        entity_param_name: Name of the entity parameter in kwargs
        
    Returns:
        Dictionary of extracted key-value pairs
    """
    entity_keys: Dict[str, Any] = {}
    
    entity = kwargs.get(entity_param_name)
    
    if entity:
        for field in key_fields:
            value = getattr(entity, field, None)
            if value is not None:
                entity_keys[field] = value
    
    for field in key_fields:
        if field not in entity_keys and field in kwargs:
            entity_keys[field] = kwargs[field]
    
    return entity_keys


def create_cache_purger(
    entity_type: str,
    key_fields: List[str],
    cascade_depth: int = 3
) -> Callable[[F], F]:
    """Factory for creating entity-specific cache purger decorators.
    
    This decorator automatically purges cache entries after successful
    database operations (insert/update/delete).
    
    Args:
        entity_type: Type of entity (e.g., 'coordination', 'session')
        key_fields: List of field names that identify the entity
        cascade_depth: Depth for cascading cache purge
        
    Returns:
        Decorator function
        
    Example:
        @create_cache_purger("coordination", ["coordination_uuid", "partition_key"])
        def insert_update_coordination(info, **kwargs):
            ...
    """
    def decorator(original_function: F) -> F:
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                result = original_function(*args, **kwargs)
                
                entity_keys = _extract_entity_keys(args, kwargs, key_fields)
                
                if all(entity_keys.get(field) for field in key_fields):
                    from .cache import purge_entity_cascading_cache
                    
                    logger = None
                    if args and hasattr(args[0], "context"):
                        logger = args[0].context.get("logger")
                    
                    if logger:
                        purge_entity_cascading_cache(
                            logger,
                            entity_type=entity_type,
                            context_keys=None,
                            entity_keys=entity_keys,
                            cascade_depth=cascade_depth,
                        )
                
                return result
            except Exception as exception:
                log = traceback.format_exc()
                if args and hasattr(args[0], "context"):
                    args[0].context.get("logger").error(log)
                raise exception
        
        return wrapper_function
    
    return decorator


def with_retry(
    max_attempts: int = 5,
    max_wait: float = 60.0,
    exponential_base: float = 1.0
) -> Callable[[F], F]:
    """Decorator for automatic retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        max_wait: Maximum wait time between retries
        exponential_base: Base for exponential backoff calculation
        
    Returns:
        Decorator function
        
    Example:
        @with_retry(max_attempts=3)
        def get_entity(key):
            ...
    """
    def decorator(original_function: F) -> F:
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            from tenacity import retry, stop_after_attempt, wait_exponential
            
            retried_function = retry(
                reraise=True,
                wait=wait_exponential(multiplier=exponential_base, max=max_wait),
                stop=stop_after_attempt(max_attempts),
            )(original_function)
            
            return retried_function(*args, **kwargs)
        
        return wrapper_function
    
    return decorator


def with_method_cache(
    ttl: int,
    cache_name: str,
    cache_enabled: bool = True
) -> Callable[[F], F]:
    """Decorator for method-level caching.
    
    Args:
        ttl: Time-to-live in seconds
        cache_name: Name of the cache
        cache_enabled: Whether caching is enabled
        
    Returns:
        Decorator function
        
    Example:
        @with_method_cache(ttl=600, cache_name="models.coordination")
        def get_coordination(partition_key, coordination_uuid):
            ...
    """
    def decorator(original_function: F) -> F:
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            from silvaengine_utility import method_cache
            
            cached_function = method_cache(
                ttl=ttl,
                cache_name=cache_name,
                cache_enabled=cache_enabled,
            )(original_function)
            
            return cached_function(*args, **kwargs)
        
        return wrapper_function
    
    return decorator


def log_errors(logger_name: Optional[str] = None) -> Callable[[F], F]:
    """Decorator to log errors with context.
    
    Args:
        logger_name: Optional logger name (defaults to module name)
        
    Returns:
        Decorator function
        
    Example:
        @log_errors()
        def process_session(info, session_uuid):
            ...
    """
    def decorator(original_function: F) -> F:
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                return original_function(*args, **kwargs)
            except Exception as exception:
                log = traceback.format_exc()
                
                logger = None
                if args and hasattr(args[0], "context"):
                    logger = args[0].context.get("logger")
                
                if logger:
                    logger.error(
                        f"Error in {original_function.__name__}: {exception}\n"
                        f"Traceback: {log}"
                    )
                raise exception
        
        return wrapper_function
    
    return decorator


def validate_required_params(*required_params: str) -> Callable[[F], F]:
    """Decorator to validate required parameters are present.
    
    Args:
        *required_params: Names of required parameters
        
    Returns:
        Decorator function
        
    Example:
        @validate_required_params("coordination_uuid", "session_uuid")
        def get_session(info, **kwargs):
            ...
    """
    def decorator(original_function: F) -> F:
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            missing = [param for param in required_params if param not in kwargs]
            
            if missing:
                from ..exceptions import ValidationError
                raise ValidationError(
                    field=missing[0],
                    value=None,
                    reason=f"Missing required parameters: {', '.join(missing)}"
                )
            
            return original_function(*args, **kwargs)
        
        return wrapper_function
    
    return decorator


# Pre-configured decorators for common entity types
# These can be imported and used directly for convenience

cache_purger_coordination = create_cache_purger(
    entity_type="coordination",
    key_fields=["coordination_uuid", "partition_key"]
)

cache_purger_task = create_cache_purger(
    entity_type="task",
    key_fields=["task_uuid", "coordination_uuid"]
)

cache_purger_session = create_cache_purger(
    entity_type="session",
    key_fields=["session_uuid", "coordination_uuid"]
)

cache_purger_session_agent = create_cache_purger(
    entity_type="session_agent",
    key_fields=["session_agent_uuid", "session_uuid"]
)

cache_purger_session_run = create_cache_purger(
    entity_type="session_run",
    key_fields=["run_uuid", "session_uuid"]
)

cache_purger_task_schedule = create_cache_purger(
    entity_type="task_schedule",
    key_fields=["schedule_uuid", "task_uuid"]
)
