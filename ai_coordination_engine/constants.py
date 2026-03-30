#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Constants and enumerations for AI Coordination Engine.

This module defines all status codes, state values, and type enumerations
to eliminate magic strings throughout the codebase and ensure type safety.
"""
from __future__ import print_function

__author__ = "bibow"

from enum import Enum
from typing import List


class SessionStatus(str, Enum):
    """Status values for Session entities.
    
    The session lifecycle follows this state machine:
    initial -> in_transit -> dispatched -> in_progress -> completed/failed/timeout
    
    State transitions:
    - initial: Session just created
    - in_transit: Session being routed to appropriate agent
    - dispatched: Session agents initialized and ready for execution
    - in_progress: Session agents actively executing
    - wait_for_user_input: Session waiting for user interaction
    - completed: All session agents completed successfully
    - failed: One or more session agents failed
    - timeout: Session execution exceeded time limit
    """
    INITIAL = "initial"
    IN_TRANSIT = "in_transit"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    WAIT_FOR_USER_INPUT = "wait_for_user_input"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    
    @classmethod
    def terminal_states(cls) -> List["SessionStatus"]:
        """Return states that indicate session has finished."""
        return [cls.COMPLETED, cls.FAILED, cls.TIMEOUT]
    
    @classmethod
    def active_states(cls) -> List["SessionStatus"]:
        """Return states that indicate session is still active."""
        return [cls.INITIAL, cls.IN_TRANSIT, cls.DISPATCHED, cls.IN_PROGRESS, cls.WAIT_FOR_USER_INPUT]


class SessionAgentState(str, Enum):
    """State values for SessionAgent entities.
    
    The session agent lifecycle follows this state machine:
    initial -> executing -> pending -> completed
                    |              |
                    v              v
                 failed      wait_for_user_input
    
    State transitions:
    - initial: Agent created, waiting for dependencies
    - executing: Agent actively processing task
    - pending: Agent waiting for action function execution
    - wait_for_user_input: Agent waiting for user input
    - completed: Agent finished successfully
    - failed: Agent execution failed
    """
    INITIAL = "initial"
    EXECUTING = "executing"
    PENDING = "pending"
    WAIT_FOR_USER_INPUT = "wait_for_user_input"
    COMPLETED = "completed"
    FAILED = "failed"
    
    @classmethod
    def ready_states(cls) -> List["SessionAgentState"]:
        """Return states where agent is ready for execution (in_degree == 0)."""
        return [cls.INITIAL, cls.PENDING]
    
    @classmethod
    def terminal_states(cls) -> List["SessionAgentState"]:
        """Return states that indicate agent has finished."""
        return [cls.COMPLETED, cls.FAILED]
    
    @classmethod
    def active_states(cls) -> List["SessionAgentState"]:
        """Return states where agent is still processing."""
        return [cls.INITIAL, cls.EXECUTING, cls.PENDING, cls.WAIT_FOR_USER_INPUT]


class AgentType(str, Enum):
    """Type values for Agent entities.
    
    Agent types determine the role and behavior:
    - task: Executes specific tasks
    - triage: Routes queries to appropriate task agents
    - decompose: Breaks down complex tasks into subtasks
    - planning: Plans task execution strategy
    """
    TASK = "task"
    TRIAGE = "triage"
    DECOMPOSE = "decompose"
    PLANNING = "planning"
    
    @classmethod
    def orchestrator_types(cls) -> List["AgentType"]:
        """Return agent types that orchestrate other agents."""
        return [cls.DECOMPOSE, cls.PLANNING]
    
    @classmethod
    def execution_types(cls) -> List["AgentType"]:
        """Return agent types that execute tasks."""
        return [cls.TASK]


class TaskScheduleStatus(str, Enum):
    """Status values for TaskSchedule entities."""
    INITIAL = "initial"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AsyncTaskStatus(str, Enum):
    """Status values for async task execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class EventBusType(str, Enum):
    """Types of event bus implementations."""
    MEMORY = "memory"
    SQS = "sqs"
    SNS = "sns"
    REDIS = "redis"


class PollingStrategy(str, Enum):
    """Polling strategy options for async task monitoring."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    ADAPTIVE = "adaptive"


class AgentExecutionStatus(str, Enum):
    """Status of agent execution in parallel executor."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Default values
DEFAULT_SESSION_STATUS = SessionStatus.INITIAL
DEFAULT_SESSION_AGENT_STATE = SessionAgentState.INITIAL
DEFAULT_TASK_SCHEDULE_STATUS = TaskScheduleStatus.INITIAL

# Configuration defaults
DEFAULT_CACHE_TTL = 600
DEFAULT_MAX_ITERATIONS = 10
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_PARALLEL_AGENTS = 5
DEFAULT_BATCH_WRITE_SIZE = 25

# Cache TTL by entity type (in seconds)
ENTITY_CACHE_TTL = {
    "coordination": 3600,
    "task": 1800,
    "session": 600,
    "session_agent": 300,
    "session_run": 300,
    "task_schedule": 1800,
}

# Valid state transitions for Session
SESSION_STATE_TRANSITIONS = {
    SessionStatus.INITIAL: [SessionStatus.IN_TRANSIT, SessionStatus.FAILED],
    SessionStatus.IN_TRANSIT: [SessionStatus.DISPATCHED, SessionStatus.FAILED],
    SessionStatus.DISPATCHED: [SessionStatus.IN_PROGRESS, SessionStatus.FAILED],
    SessionStatus.IN_PROGRESS: [
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.TIMEOUT,
        SessionStatus.WAIT_FOR_USER_INPUT,
    ],
    SessionStatus.WAIT_FOR_USER_INPUT: [
        SessionStatus.IN_PROGRESS,
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
    ],
}

# Valid state transitions for SessionAgent
SESSION_AGENT_STATE_TRANSITIONS = {
    SessionAgentState.INITIAL: [
        SessionAgentState.EXECUTING,
        SessionAgentState.PENDING,
        SessionAgentState.FAILED,
    ],
    SessionAgentState.EXECUTING: [
        SessionAgentState.COMPLETED,
        SessionAgentState.FAILED,
        SessionAgentState.WAIT_FOR_USER_INPUT,
    ],
    SessionAgentState.PENDING: [
        SessionAgentState.COMPLETED,
        SessionAgentState.FAILED,
    ],
    SessionAgentState.WAIT_FOR_USER_INPUT: [
        SessionAgentState.COMPLETED,
        SessionAgentState.FAILED,
    ],
}
