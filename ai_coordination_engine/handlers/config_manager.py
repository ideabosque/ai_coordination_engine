#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Manager for AI Coordination Engine Performance Optimizations

This module provides centralized configuration management with support for
feature flags, environment-based configuration, and runtime configuration updates.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class PollingStrategy(Enum):
    """Polling strategy options for async task monitoring."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    ADAPTIVE = "adaptive"


@dataclass
class PerformanceConfig:
    """Performance optimization configuration.

    All optimizations are enabled by default.
    Settings can be adjusted via environment variables.
    """

    max_parallel_agents: int = field(
        default_factory=lambda: int(os.getenv("MAX_PARALLEL_AGENTS", "5"))
    )
    parallel_execution_timeout: float = field(
        default_factory=lambda: float(os.getenv("PARALLEL_EXECUTION_TIMEOUT", "180.0"))
    )

    event_bus_type: str = field(
        default_factory=lambda: os.getenv("EVENT_BUS_TYPE", "memory")
    )
    event_bus_queue_url: Optional[str] = field(
        default_factory=lambda: os.getenv("EVENT_BUS_QUEUE_URL")
    )

    mcp_tool_cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("MCP_TOOL_CACHE_TTL_SECONDS", "300"))
    )
    mcp_tool_cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("MCP_TOOL_CACHE_MAX_SIZE", "100"))
    )

    batch_write_size: int = field(
        default_factory=lambda: int(os.getenv("BATCH_WRITE_SIZE", "25"))
    )

    async_task_poll_strategy: PollingStrategy = field(
        default_factory=lambda: PollingStrategy(os.getenv("ASYNC_TASK_POLL_STRATEGY", "adaptive"))
    )
    async_task_poll_initial_interval: float = field(
        default_factory=lambda: float(os.getenv("ASYNC_TASK_POLL_INITIAL_INTERVAL", "0.05"))
    )
    async_task_poll_max_interval: float = field(
        default_factory=lambda: float(os.getenv("ASYNC_TASK_POLL_MAX_INTERVAL", "1.0"))
    )
    async_task_poll_max_attempts: int = field(
        default_factory=lambda: int(os.getenv("ASYNC_TASK_POLL_MAX_ATTEMPTS", "120"))
    )
    async_task_poll_timeout: float = field(
        default_factory=lambda: float(os.getenv("ASYNC_TASK_POLL_TIMEOUT", "120.0"))
    )
    enable_batch_session_agent_create: bool = field(
        default_factory=lambda: os.getenv("ENABLE_BATCH_SESSION_AGENT_CREATE", "true").lower() == "true"
    )
    enable_event_driven_async_tasks: bool = field(
        default_factory=lambda: os.getenv("ENABLE_EVENT_DRIVEN_ASYNC_TASKS", "true").lower() == "true"
    )

    http_max_connections: int = field(
        default_factory=lambda: int(os.getenv("HTTP_MAX_CONNECTIONS", "100"))
    )
    http_max_keepalive_connections: int = field(
        default_factory=lambda: int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "20"))
    )
    http_keepalive_expiry: float = field(
        default_factory=lambda: float(os.getenv("HTTP_KEEPALIVE_EXPIRY", "60.0"))
    )


# Global configuration instance
_performance_config: Optional[PerformanceConfig] = None


def get_performance_config() -> PerformanceConfig:
    """Get the global performance configuration instance.
    
    Returns:
        PerformanceConfig: The global configuration instance
    """
    global _performance_config
    if _performance_config is None:
        _performance_config = PerformanceConfig()
    return _performance_config


def reload_performance_config() -> PerformanceConfig:
    """Reload configuration from environment variables.
    
    Returns:
        PerformanceConfig: The updated configuration instance
    """
    global _performance_config
    _performance_config = PerformanceConfig()
    return _performance_config
