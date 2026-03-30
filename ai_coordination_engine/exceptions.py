#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exception hierarchy for AI Coordination Engine.

This module provides a unified exception system for consistent error handling
across all modules of the coordination engine.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional


class AICoordinationError(Exception):
    """Base exception for all AI Coordination Engine errors.
    
    All custom exceptions in the coordination engine should inherit from this
    base class to enable unified error handling and logging.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class EntityNotFoundError(AICoordinationError):
    """Raised when a requested entity is not found in the database.
    
    Attributes:
        entity_type: The type of entity that was not found
        entity_id: The identifier used to search for the entity
    """
    
    def __init__(
        self, 
        entity_type: str, 
        entity_id: str,
        message: Optional[str] = None
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        message = message or f"{entity_type} not found: {entity_id}"
        super().__init__(
            message=message,
            details={"entity_type": entity_type, "entity_id": entity_id}
        )


class ValidationError(AICoordinationError):
    """Raised when input validation fails.
    
    Attributes:
        field: The field that failed validation
        value: The invalid value (may be sanitized)
        reason: Human-readable explanation of why validation failed
    """
    
    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        message: Optional[str] = None
    ):
        self.field = field
        self.value = value
        self.reason = reason
        message = message or f"Validation failed for field '{field}': {reason}"
        super().__init__(
            message=message,
            details={"field": field, "reason": reason}
        )


class AgentExecutionError(AICoordinationError):
    """Raised when an agent execution fails.
    
    Attributes:
        agent_uuid: UUID of the agent that failed
        session_uuid: UUID of the session (if applicable)
        original_error: The underlying error that caused the failure
    """
    
    def __init__(
        self,
        agent_uuid: str,
        original_error: Optional[str] = None,
        session_uuid: Optional[str] = None,
        message: Optional[str] = None
    ):
        self.agent_uuid = agent_uuid
        self.session_uuid = session_uuid
        self.original_error = original_error
        message = message or f"Agent execution failed for agent {agent_uuid}"
        if original_error:
            message = f"{message}: {original_error}"
        super().__init__(
            message=message,
            details={
                "agent_uuid": agent_uuid,
                "session_uuid": session_uuid,
                "original_error": original_error
            }
        )


class SessionTimeoutError(AICoordinationError):
    """Raised when a session execution times out.
    
    Attributes:
        session_uuid: UUID of the timed out session
        timeout_seconds: The timeout duration that was exceeded
        elapsed_seconds: Actual elapsed time
    """
    
    def __init__(
        self,
        session_uuid: str,
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None,
        message: Optional[str] = None
    ):
        self.session_uuid = session_uuid
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds
        message = message or f"Session {session_uuid} timed out after {timeout_seconds}s"
        super().__init__(
            message=message,
            details={
                "session_uuid": session_uuid,
                "timeout_seconds": timeout_seconds,
                "elapsed_seconds": elapsed_seconds
            }
        )


class CoordinationNotFoundError(EntityNotFoundError):
    """Raised when a coordination is not found."""
    
    def __init__(self, coordination_uuid: str):
        super().__init__("coordination", coordination_uuid)


class TaskNotFoundError(EntityNotFoundError):
    """Raised when a task is not found."""
    
    def __init__(self, task_uuid: str):
        super().__init__("task", task_uuid)


class SessionNotFoundError(EntityNotFoundError):
    """Raised when a session is not found."""
    
    def __init__(self, session_uuid: str):
        super().__init__("session", session_uuid)


class SessionAgentNotFoundError(EntityNotFoundError):
    """Raised when a session agent is not found."""
    
    def __init__(self, session_agent_uuid: str):
        super().__init__("session_agent", session_agent_uuid)


class AgentNotFoundError(EntityNotFoundError):
    """Raised when an agent is not found in coordination."""
    
    def __init__(self, agent_uuid: str):
        super().__init__("agent", agent_uuid)


class InvalidStateTransitionError(AICoordinationError):
    """Raised when an invalid state transition is attempted.
    
    Attributes:
        entity_type: Type of entity
        current_state: Current state of the entity
        target_state: Attempted target state
    """
    
    def __init__(
        self,
        entity_type: str,
        current_state: str,
        target_state: str,
        message: Optional[str] = None
    ):
        self.entity_type = entity_type
        self.current_state = current_state
        self.target_state = target_state
        message = message or (
            f"Invalid state transition for {entity_type}: "
            f"cannot transition from '{current_state}' to '{target_state}'"
        )
        super().__init__(
            message=message,
            details={
                "entity_type": entity_type,
                "current_state": current_state,
                "target_state": target_state
            }
        )


class DependencyNotMetError(AICoordinationError):
    """Raised when a dependency requirement is not satisfied.
    
    Attributes:
        dependent_uuid: UUID of the entity waiting on dependencies
        missing_dependencies: List of unmet dependency UUIDs
    """
    
    def __init__(
        self,
        dependent_uuid: str,
        missing_dependencies: List[str],
        message: Optional[str] = None
    ):
        self.dependent_uuid = dependent_uuid
        self.missing_dependencies = missing_dependencies
        message = message or (
            f"Dependency not met for {dependent_uuid}: "
            f"missing {len(missing_dependencies)} dependencies"
        )
        super().__init__(
            message=message,
            details={
                "dependent_uuid": dependent_uuid,
                "missing_dependencies": missing_dependencies
            }
        )


class ConfigurationError(AICoordinationError):
    """Raised when there is a configuration error.
    
    Attributes:
        config_key: The configuration key that has an issue
        config_value: The problematic value (may be sanitized)
    """
    
    def __init__(
        self,
        config_key: str,
        reason: str,
        message: Optional[str] = None
    ):
        self.config_key = config_key
        self.reason = reason
        message = message or f"Configuration error for '{config_key}': {reason}"
        super().__init__(
            message=message,
            details={"config_key": config_key, "reason": reason}
        )


class RateLimitExceededError(AICoordinationError):
    """Raised when rate limit is exceeded.
    
    Attributes:
        limit_type: Type of rate limit (e.g., 'requests', 'tokens')
        limit_value: The limit that was exceeded
        retry_after: Suggested wait time in seconds
    """
    
    def __init__(
        self,
        limit_type: str,
        limit_value: int,
        retry_after: Optional[float] = None,
        message: Optional[str] = None
    ):
        self.limit_type = limit_type
        self.limit_value = limit_value
        self.retry_after = retry_after
        message = message or f"Rate limit exceeded: {limit_type} limit of {limit_value}"
        super().__init__(
            message=message,
            details={
                "limit_type": limit_type,
                "limit_value": limit_value,
                "retry_after": retry_after
            }
        )
