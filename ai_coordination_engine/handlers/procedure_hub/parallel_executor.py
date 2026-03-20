#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parallel Agent Executor Module

This module provides parallel execution capabilities for session agents,
allowing multiple ready agents to execute concurrently while maintaining
proper error handling and resource management.
"""

import asyncio
import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from graphene import ResolveInfo

from ...types.session_agent import SessionAgentType
from ...handlers.config_manager import get_performance_config


class AgentExecutionStatus(Enum):
    """Status of agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentExecutionResult:
    """Result of a single agent execution."""
    session_agent_uuid: str
    agent_uuid: str
    status: AgentExecutionStatus
    duration_seconds: float
    error: Optional[str] = None
    result: Optional[Any] = None


class RateLimiter:
    """Token bucket rate limiter for controlling concurrent API calls."""
    
    def __init__(self, max_requests: int = 10, window_seconds: float = 1.0):
        self.max_requests = max_requests
        self.window = window_seconds
        self.tokens = max_requests
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            # Replenish tokens based on elapsed time
            self.tokens = min(
                self.max_requests,
                self.tokens + elapsed * (self.max_requests / self.window)
            )
            self.last_update = now
            
            if self.tokens < 1:
                # Calculate wait time for next token
                wait_time = (1 - self.tokens) * (self.window / self.max_requests)
                await asyncio.sleep(wait_time)
                self.tokens = 1
            
            self.tokens -= 1


class ParallelAgentExecutor:
    """Executor for running session agents in parallel.
    
    This executor manages concurrent execution of multiple session agents
    while providing rate limiting, error handling, and resource management.
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        rate_limit: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the parallel executor.
        
        Args:
            max_workers: Maximum number of concurrent workers (default from config)
            rate_limit: Maximum API calls per second (default: 10)
            timeout_seconds: Maximum execution time per agent (default from config)
            logger: Logger instance
        """
        config = get_performance_config()
        
        self.max_workers = max_workers or config.max_parallel_agents
        self.timeout_seconds = timeout_seconds or config.parallel_execution_timeout
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize thread pool executor for running sync functions
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Initialize rate limiter
        self._rate_limiter = RateLimiter(
            max_requests=rate_limit or 10,
            window_seconds=1.0
        )
        
        self._execution_stats: Dict[str, Any] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_duration": 0.0,
        }
    
    async def execute_agents_parallel(
        self,
        info: ResolveInfo,
        ready_agents: List[SessionAgentType],
        execute_func: Any
    ) -> List[AgentExecutionResult]:
        """Execute multiple session agents in parallel.
        
        Args:
            info: GraphQL resolve info containing context
            ready_agents: List of agents ready for execution
            execute_func: Function to execute each agent (e.g., execute_session_agent)
            
        Returns:
            List of execution results for each agent
        """
        if not ready_agents:
            return []
        
        self.logger.info(
            f"Starting parallel execution of {len(ready_agents)} agents "
            f"with max_workers={self.max_workers}"
        )
        
        start_time = time.time()
        
        # Use semaphore to control concurrency
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def execute_with_semaphore(agent: SessionAgentType) -> AgentExecutionResult:
            async with semaphore:
                return await self._execute_single_agent(info, agent, execute_func)
        
        # Create tasks for all agents with semaphore control
        tasks = [
            execute_with_semaphore(agent)
            for agent in ready_agents
        ]
        
        # Execute all tasks concurrently with gather
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Process results
        execution_results = []
        for agent, result in zip(ready_agents, results):
            if isinstance(result, Exception):
                execution_results.append(AgentExecutionResult(
                    session_agent_uuid=agent.session_agent_uuid,
                    agent_uuid=agent.agent_uuid,
                    status=AgentExecutionStatus.FAILED,
                    duration_seconds=0.0,
                    error=str(result)
                ))
            else:
                execution_results.append(result)
        
        # Update statistics
        self._update_stats(execution_results, total_duration)
        
        self.logger.info(
            f"Parallel execution completed in {total_duration:.2f}s. "
            f"Success: {sum(1 for r in execution_results if r.status == AgentExecutionStatus.COMPLETED)}, "
            f"Failed: {sum(1 for r in execution_results if r.status == AgentExecutionStatus.FAILED)}"
        )
        
        return execution_results
    
    async def _execute_single_agent(
        self,
        info: ResolveInfo,
        agent: SessionAgentType,
        execute_func: Any
    ) -> AgentExecutionResult:
        """Execute a single agent with rate limiting and timeout.
        
        Args:
            info: GraphQL resolve info
            agent: Session agent to execute
            execute_func: Execution function
            
        Returns:
            AgentExecutionResult with execution status
        """
        start_time = time.time()
        
        try:
            # Apply rate limiting
            await self._rate_limiter.acquire()
            
            self.logger.info(f"Executing agent {agent.agent_uuid} (parallel)")
            
            # Run the execution function in thread pool with timeout
            loop = asyncio.get_event_loop()
            
            # Create a future for the execution
            future = loop.run_in_executor(
                self._executor,
                self._wrap_execution,
                info,
                agent,
                execute_func
            )
            
            # Wait for completion with timeout
            await asyncio.wait_for(future, timeout=self.timeout_seconds)
            
            duration = time.time() - start_time
            
            return AgentExecutionResult(
                session_agent_uuid=agent.session_agent_uuid,
                agent_uuid=agent.agent_uuid,
                status=AgentExecutionStatus.COMPLETED,
                duration_seconds=duration
            )
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            error_msg = f"Agent execution timed out after {self.timeout_seconds}s"
            self.logger.error(f"{error_msg} for agent {agent.agent_uuid}")
            
            return AgentExecutionResult(
                session_agent_uuid=agent.session_agent_uuid,
                agent_uuid=agent.agent_uuid,
                status=AgentExecutionStatus.TIMEOUT,
                duration_seconds=duration,
                error=error_msg
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Agent execution failed: {str(e)}"
            self.logger.error(f"{error_msg} for agent {agent.agent_uuid}")
            self.logger.error(traceback.format_exc())
            
            return AgentExecutionResult(
                session_agent_uuid=agent.session_agent_uuid,
                agent_uuid=agent.agent_uuid,
                status=AgentExecutionStatus.FAILED,
                duration_seconds=duration,
                error=error_msg
            )
    
    def _wrap_execution(
        self,
        info: ResolveInfo,
        agent: SessionAgentType,
        execute_func: Any
    ) -> None:
        """Wrapper for executing agent function in thread pool.
        
        Args:
            info: GraphQL resolve info
            agent: Session agent to execute
            execute_func: Execution function
        """
        try:
            execute_func(info, agent)
        except Exception as e:
            self.logger.error(f"Execution failed for agent {agent.agent_uuid}: {e}")
            raise
    
    def _update_stats(
        self,
        results: List[AgentExecutionResult],
        total_duration: float
    ) -> None:
        """Update execution statistics.
        
        Args:
            results: List of execution results
            total_duration: Total execution time
        """
        self._execution_stats["total_executions"] += len(results)
        self._execution_stats["successful_executions"] += sum(
            1 for r in results if r.status == AgentExecutionStatus.COMPLETED
        )
        self._execution_stats["failed_executions"] += sum(
            1 for r in results if r.status == AgentExecutionStatus.FAILED
        )
        self._execution_stats["total_duration"] += total_duration
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Dictionary containing execution statistics
        """
        stats = self._execution_stats.copy()
        if stats["total_executions"] > 0:
            stats["success_rate"] = (
                stats["successful_executions"] / stats["total_executions"]
            )
            stats["average_duration"] = (
                stats["total_duration"] / stats["total_executions"]
            )
        else:
            stats["success_rate"] = 0.0
            stats["average_duration"] = 0.0
        return stats
    
    def shutdown(self) -> None:
        """Shutdown the executor and release resources."""
        self.logger.info("Shutting down ParallelAgentExecutor")
        self._executor.shutdown(wait=True)


# Global executor instance
_parallel_executor: Optional[ParallelAgentExecutor] = None


def get_parallel_executor(
    max_workers: Optional[int] = None,
    logger: Optional[logging.Logger] = None
) -> ParallelAgentExecutor:
    """Get or create the global parallel executor instance.
    
    Args:
        max_workers: Maximum number of concurrent workers
        logger: Logger instance
        
    Returns:
        ParallelAgentExecutor instance
    """
    global _parallel_executor
    if _parallel_executor is None:
        _parallel_executor = ParallelAgentExecutor(
            max_workers=max_workers,
            logger=logger
        )
    return _parallel_executor


def reset_parallel_executor() -> None:
    """Reset the global executor instance.
    
    This should be called when configuration changes or for testing.
    """
    global _parallel_executor
    if _parallel_executor is not None:
        _parallel_executor.shutdown()
        _parallel_executor = None
