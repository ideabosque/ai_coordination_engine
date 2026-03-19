#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Polling Module for Async Task Monitoring

This module provides intelligent polling strategies for monitoring async task
completion status, replacing fixed-interval polling with adaptive strategies
to reduce latency and database load.
"""

import time
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ...handlers.config_manager import get_performance_config, PollingStrategy


@dataclass
class PollingResult:
    """Result of a polling operation."""
    status: str
    result: Optional[str]
    notes: Optional[str]
    attempts: int
    total_duration: float


class AdaptivePollingStats:
    """Statistics for adaptive polling optimization."""
    
    def __init__(self):
        self.task_completion_times: Dict[str, list] = {}
        self.max_history_size = 100
    
    def record_completion(self, task_type: str, duration: float) -> None:
        """Record task completion time for adaptive calculations."""
        if task_type not in self.task_completion_times:
            self.task_completion_times[task_type] = []
        
        self.task_completion_times[task_type].append(duration)
        
        # Keep history size limited
        if len(self.task_completion_times[task_type]) > self.max_history_size:
            self.task_completion_times[task_type] = (
                self.task_completion_times[task_type][-self.max_history_size:]
            )
    
    def get_average_completion_time(self, task_type: str) -> float:
        """Get average completion time for a task type."""
        times = self.task_completion_times.get(task_type, [])
        if not times:
            return 5.0  # Default 5 seconds
        return sum(times) / len(times)


# Global stats instance
_polling_stats = AdaptivePollingStats()


def calculate_polling_interval(
    attempt: int,
    strategy: PollingStrategy,
    config: Any,
    task_type: str = "default"
) -> float:
    """Calculate the polling interval based on strategy and attempt number.
    
    Args:
        attempt: Current attempt number (0-indexed)
        strategy: Polling strategy to use
        config: Configuration object with interval settings
        task_type: Type of task for adaptive polling
        
    Returns:
        float: Polling interval in seconds
    """
    initial = config.async_task_poll_initial_interval
    max_interval = config.async_task_poll_max_interval
    
    if strategy == PollingStrategy.FIXED:
        return 1.0  # Original fixed interval
    
    elif strategy == PollingStrategy.LINEAR:
        # Linear increase: initial + attempt * 0.1
        return min(initial + attempt * 0.1, max_interval)
    
    elif strategy == PollingStrategy.EXPONENTIAL:
        # Exponential backoff: initial * 2^attempt
        interval = initial * (2 ** attempt)
        return min(interval, max_interval)
    
    elif strategy == PollingStrategy.ADAPTIVE:
        # Adaptive based on historical data
        avg_time = _polling_stats.get_average_completion_time(task_type)
        
        if attempt == 0:
            # First poll: quick check
            return initial
        elif avg_time < 1.0:
            # Fast tasks: aggressive polling
            return min(0.1 + attempt * 0.05, max_interval)
        elif avg_time < 5.0:
            # Medium tasks: moderate polling
            return min(0.5 + attempt * 0.1, max_interval)
        else:
            # Slow tasks: relaxed polling
            return min(1.0 + attempt * 0.2, max_interval)
    
    return initial


def poll_async_task_smart(
    task_fetcher: Callable[[], Dict[str, Any]],
    logger: Optional[logging.Logger] = None,
    task_type: str = "default",
    custom_config: Optional[Any] = None
) -> PollingResult:
    """Poll async task with smart polling strategy.
    
    Args:
        task_fetcher: Function that fetches the current task status
        logger: Logger instance
        task_type: Type of task for adaptive polling
        custom_config: Optional custom configuration
        
    Returns:
        PollingResult with task status and polling statistics
    """
    config = custom_config or get_performance_config()
    logger = logger or logging.getLogger(__name__)
    
    strategy = config.async_task_poll_strategy
    max_attempts = config.async_task_poll_max_attempts
    timeout = config.async_task_poll_timeout
    
    start_time = time.time()
    attempt = 0
    
    logger.info(
        f"Starting smart polling with strategy={strategy.value}, "
        f"max_attempts={max_attempts}, timeout={timeout}s"
    )
    
    while attempt < max_attempts:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            logger.warning(f"Smart polling timed out after {elapsed:.2f}s")
            return PollingResult(
                status="timeout",
                result=None,
                notes=f"Polling timed out after {elapsed:.2f}s",
                attempts=attempt,
                total_duration=elapsed
            )
        
        # Fetch task status
        task = task_fetcher()
        
        # Check if task is complete
        if task["status"] in ["completed", "failed"]:
            total_duration = time.time() - start_time
            
            # Record completion time for adaptive polling
            if strategy == PollingStrategy.ADAPTIVE:
                _polling_stats.record_completion(task_type, total_duration)
            
            logger.info(
                f"Task completed with status={task['status']} "
                f"after {attempt + 1} attempts, {total_duration:.2f}s"
            )
            
            return PollingResult(
                status=task["status"],
                result=task.get("result"),
                notes=task.get("notes"),
                attempts=attempt + 1,
                total_duration=total_duration
            )
        
        # Calculate next polling interval
        interval = calculate_polling_interval(attempt, strategy, config, task_type)
        
        logger.debug(
            f"Attempt {attempt + 1}: task status={task['status']}, "
            f"next poll in {interval:.2f}s"
        )
        
        time.sleep(interval)
        attempt += 1
    
    # Max attempts reached
    total_duration = time.time() - start_time
    logger.error(f"Smart polling exceeded max attempts: {max_attempts}")
    
    return PollingResult(
        status="timeout",
        result=None,
        notes=f"Exceeded max attempts: {max_attempts}",
        attempts=attempt,
        total_duration=total_duration
    )


class SmartPoller:
    """Smart poller class for reusable polling operations."""
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        config: Optional[Any] = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or get_performance_config()
        self.stats = AdaptivePollingStats()
    
    def poll(
        self,
        task_fetcher: Callable[[], Dict[str, Any]],
        task_type: str = "default"
    ) -> PollingResult:
        """Poll a task to completion.
        
        Args:
            task_fetcher: Function that returns task status dict
            task_type: Type of task for adaptive polling
            
        Returns:
            PollingResult with final status
        """
        return poll_async_task_smart(
            task_fetcher=task_fetcher,
            logger=self.logger,
            task_type=task_type,
            custom_config=self.config
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get polling statistics."""
        return {
            "task_types": list(self.stats.task_completion_times.keys()),
            "average_times": {
                task_type: self.stats.get_average_completion_time(task_type)
                for task_type in self.stats.task_completion_times
            }
        }
