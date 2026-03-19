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
    
    All feature flags default to False for backward compatibility.
    Enable features gradually through environment variables or runtime configuration.
    """
    
    # Feature Flags for Parallel Execution
    enable_parallel_agent_execution: bool = field(
        default_factory=lambda: os.getenv("ENABLE_PARALLEL_AGENT_EXECUTION", "false").lower() == "true"
    )
    max_parallel_agents: int = field(
        default_factory=lambda: int(os.getenv("MAX_PARALLEL_AGENTS", "3"))
    )
    parallel_execution_timeout: float = field(
        default_factory=lambda: float(os.getenv("PARALLEL_EXECUTION_TIMEOUT", "300.0"))
    )
    
    # Feature Flags for Event-Driven Architecture
    enable_event_driven_async_tasks: bool = field(
        default_factory=lambda: os.getenv("ENABLE_EVENT_DRIVEN_ASYNC_TASKS", "false").lower() == "true"
    )
    event_bus_type: str = field(
        default_factory=lambda: os.getenv("EVENT_BUS_TYPE", "memory")  # memory, sqs, sns
    )
    event_bus_queue_url: Optional[str] = field(
        default_factory=lambda: os.getenv("EVENT_BUS_QUEUE_URL")
    )
    
    # Feature Flags for MCP Tool Caching
    enable_mcp_tool_cache: bool = field(
        default_factory=lambda: os.getenv("ENABLE_MCP_TOOL_CACHE", "false").lower() == "true"
    )
    mcp_tool_cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("MCP_TOOL_CACHE_TTL_SECONDS", "300"))
    )
    mcp_tool_cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("MCP_TOOL_CACHE_MAX_SIZE", "100"))
    )
    
    # Feature Flags for Batch Operations
    enable_batch_session_agent_create: bool = field(
        default_factory=lambda: os.getenv("ENABLE_BATCH_SESSION_AGENT_CREATE", "false").lower() == "true"
    )
    batch_write_size: int = field(
        default_factory=lambda: int(os.getenv("BATCH_WRITE_SIZE", "25"))
    )
    
    # Polling Configuration
    async_task_poll_strategy: PollingStrategy = field(
        default_factory=lambda: PollingStrategy(os.getenv("ASYNC_TASK_POLL_STRATEGY", "adaptive"))
    )
    async_task_poll_initial_interval: float = field(
        default_factory=lambda: float(os.getenv("ASYNC_TASK_POLL_INITIAL_INTERVAL", "0.1"))
    )
    async_task_poll_max_interval: float = field(
        default_factory=lambda: float(os.getenv("ASYNC_TASK_POLL_MAX_INTERVAL", "2.0"))
    )
    async_task_poll_max_attempts: int = field(
        default_factory=lambda: int(os.getenv("ASYNC_TASK_POLL_MAX_ATTEMPTS", "60"))
    )
    async_task_poll_timeout: float = field(
        default_factory=lambda: float(os.getenv("ASYNC_TASK_POLL_TIMEOUT", "60.0"))
    )
    
    # HTTP Client Configuration
    http_max_connections: int = field(
        default_factory=lambda: int(os.getenv("HTTP_MAX_CONNECTIONS", "100"))
    )
    http_max_keepalive_connections: int = field(
        default_factory=lambda: int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "20"))
    )
    http_keepalive_expiry: float = field(
        default_factory=lambda: float(os.getenv("HTTP_KEEPALIVE_EXPIRY", "60.0"))
    )
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled.
        
        Args:
            feature_name: Name of the feature flag
            
        Returns:
            bool: True if feature is enabled
            
        Supported feature names:
        - PARALLEL_EXECUTION
        - EVENT_DRIVEN_ASYNC_TASKS
        - MCP_TOOL_CACHE
        - BATCH_SESSION_AGENT_CREATE
        """
        feature_map = {
            "PARALLEL_EXECUTION": self.enable_parallel_agent_execution,
            "EVENT_DRIVEN_ASYNC_TASKS": self.enable_event_driven_async_tasks,
            "MCP_TOOL_CACHE": self.enable_mcp_tool_cache,
            "BATCH_SESSION_AGENT_CREATE": self.enable_batch_session_agent_create,
        }
        return feature_map.get(feature_name, False)
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "enable_parallel_agent_execution": self.enable_parallel_agent_execution,
            "max_parallel_agents": self.max_parallel_agents,
            "parallel_execution_timeout": self.parallel_execution_timeout,
            "enable_event_driven_async_tasks": self.enable_event_driven_async_tasks,
            "event_bus_type": self.event_bus_type,
            "enable_mcp_tool_cache": self.enable_mcp_tool_cache,
            "mcp_tool_cache_ttl_seconds": self.mcp_tool_cache_ttl_seconds,
            "enable_batch_session_agent_create": self.enable_batch_session_agent_create,
            "batch_write_size": self.batch_write_size,
            "async_task_poll_strategy": self.async_task_poll_strategy.value,
            "async_task_poll_initial_interval": self.async_task_poll_initial_interval,
            "async_task_poll_max_interval": self.async_task_poll_max_interval,
            "http_max_connections": self.http_max_connections,
        }


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
