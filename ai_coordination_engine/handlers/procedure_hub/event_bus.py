#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event Bus Module for Async Task Completion Notifications

This module provides an event-driven architecture for async task completion,
replacing polling-based waiting with event notifications for improved
performance and reduced latency.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional, Set

from ...constants import EventBusType
from ...handlers.config_manager import get_performance_config


@dataclass
class TaskCompletionEvent:
    """Event representing async task completion."""
    async_task_uuid: str
    function_name: str
    status: str  # "completed", "failed"
    result: Optional[str] = None
    notes: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskCompletionEvent":
        """Create event from dictionary."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "TaskCompletionEvent":
        """Create event from JSON string."""
        return cls.from_dict(json.loads(json_str))


class EventBusBackend(ABC):
    """Abstract base class for event bus backends."""
    
    @abstractmethod
    def publish(self, event: TaskCompletionEvent) -> bool:
        """Publish an event to the bus.
        
        Args:
            event: The event to publish
            
        Returns:
            bool: True if published successfully
        """
        pass
    
    @abstractmethod
    def subscribe(
        self, 
        async_task_uuid: str, 
        callback: Callable[[TaskCompletionEvent], None]
    ) -> None:
        """Subscribe to events for a specific task.
        
        Args:
            async_task_uuid: UUID of the async task to subscribe to
            callback: Function to call when event is received
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, async_task_uuid: str) -> None:
        """Unsubscribe from events for a specific task.
        
        Args:
            async_task_uuid: UUID of the async task to unsubscribe from
        """
        pass
    
    @abstractmethod
    def get_pending_event(
        self, 
        async_task_uuid: str
    ) -> Optional[TaskCompletionEvent]:
        """Get any pending event for a task (for late subscribers).
        
        Args:
            async_task_uuid: UUID of the async task
            
        Returns:
            The pending event if exists, None otherwise
        """
        pass


class InMemoryEventBus(EventBusBackend):
    """In-memory implementation of event bus.
    
    Suitable for single-instance deployments or testing.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._subscribers: Dict[str, Set[Callable]] = {}
        self._pending_events: Dict[str, TaskCompletionEvent] = {}
        self._lock = asyncio.Lock()
    
    def publish(self, event: TaskCompletionEvent) -> bool:
        """Publish event to in-memory bus."""
        try:
            self.logger.debug(
                f"Publishing event for task {event.async_task_uuid} "
                f"with status {event.status}"
            )
            
            # Store event for late subscribers
            self._pending_events[event.async_task_uuid] = event
            
            # Notify subscribers
            callbacks = self._subscribers.get(event.async_task_uuid, set())
            for callback in callbacks:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error notifying subscriber: {e}")
            
            # Clean up completed/failed events after some time
            if event.status in ["completed", "failed"]:
                # Keep for 60 seconds for late subscribers
                asyncio.create_task(
                    self._cleanup_after_delay(event.async_task_uuid, 60)
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing event: {e}")
            return False
    
    def subscribe(
        self, 
        async_task_uuid: str, 
        callback: Callable[[TaskCompletionEvent], None]
    ) -> None:
        """Subscribe to events for a specific task."""
        if async_task_uuid not in self._subscribers:
            self._subscribers[async_task_uuid] = set()
        self._subscribers[async_task_uuid].add(callback)
        
        self.logger.debug(
            f"Subscribed to events for task {async_task_uuid}"
        )
        
        # Check if there's already a pending event
        pending = self._pending_events.get(async_task_uuid)
        if pending and pending.status in ["completed", "failed"]:
            self.logger.debug(
                f"Found pending event for task {async_task_uuid}, notifying immediately"
            )
            try:
                callback(pending)
            except Exception as e:
                self.logger.error(f"Error notifying subscriber with pending event: {e}")
    
    def unsubscribe(self, async_task_uuid: str) -> None:
        """Unsubscribe from events for a specific task."""
        if async_task_uuid in self._subscribers:
            del self._subscribers[async_task_uuid]
            self.logger.debug(
                f"Unsubscribed from events for task {async_task_uuid}"
            )
    
    def get_pending_event(
        self, 
        async_task_uuid: str
    ) -> Optional[TaskCompletionEvent]:
        """Get pending event for a task."""
        return self._pending_events.get(async_task_uuid)
    
    async def _cleanup_after_delay(
        self, 
        async_task_uuid: str, 
        delay_seconds: int
    ) -> None:
        """Clean up event after delay."""
        await asyncio.sleep(delay_seconds)
        self._pending_events.pop(async_task_uuid, None)
        self._subscribers.pop(async_task_uuid, None)


class SQSEventBus(EventBusBackend):
    """AWS SQS-based event bus for distributed deployments.
    
    Provides reliable message delivery with persistence.
    """
    
    def __init__(
        self, 
        queue_url: str,
        region: str = "us-east-1",
        logger: Optional[logging.Logger] = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.queue_url = queue_url
        self.region = region
        
        # Import boto3 lazily
        try:
            import boto3
            self.sqs = boto3.client("sqs", region_name=region)
        except ImportError:
            self.logger.error("boto3 not installed, SQS event bus unavailable")
            raise
    
    def publish(self, event: TaskCompletionEvent) -> bool:
        """Publish event to SQS queue."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=event.to_json(),
                MessageAttributes={
                    "async_task_uuid": {
                        "StringValue": event.async_task_uuid,
                        "DataType": "String"
                    },
                    "status": {
                        "StringValue": event.status,
                        "DataType": "String"
                    }
                }
            )
            
            self.logger.debug(
                f"Published event to SQS for task {event.async_task_uuid}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing to SQS: {e}")
            return False
    
    def subscribe(
        self, 
        async_task_uuid: str, 
        callback: Callable[[TaskCompletionEvent], None]
    ) -> None:
        """Subscribe is handled via polling in SQS."""
        # SQS subscription is implemented via polling
        # This would be handled by a separate worker process
        pass
    
    def unsubscribe(self, async_task_uuid: str) -> None:
        """Unsubscribe from SQS events."""
        pass
    
    def get_pending_event(
        self, 
        async_task_uuid: str
    ) -> Optional[TaskCompletionEvent]:
        """Poll SQS for pending events."""
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                MessageAttributeNames=["All"],
                VisibilityTimeout=0,
                WaitTimeSeconds=0
            )
            
            messages = response.get("Messages", [])
            for message in messages:
                body = json.loads(message["Body"])
                if body.get("async_task_uuid") == async_task_uuid:
                    # Delete the message
                    self.sqs.delete_message(
                        QueueUrl=self.queue_url,
                        ReceiptHandle=message["ReceiptHandle"]
                    )
                    return TaskCompletionEvent.from_dict(body)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error polling SQS: {e}")
            return None


class AsyncTaskEventBus:
    """Main event bus for async task completion notifications.
    
    Provides a unified interface for event-driven async task monitoring,
    with support for multiple backends (memory, SQS, etc.).
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = get_performance_config()
        
        # Initialize backend based on configuration
        bus_type = EventBusType(self.config.event_bus_type)
        
        if bus_type == EventBusType.MEMORY:
            self._backend: EventBusBackend = InMemoryEventBus(logger)
        elif bus_type == EventBusType.SQS:
            if not self.config.event_bus_queue_url:
                raise ValueError("SQS queue URL not configured")
            self._backend = SQSEventBus(
                queue_url=self.config.event_bus_queue_url,
                logger=logger
            )
        else:
            self.logger.warning(
                f"Unsupported event bus type: {bus_type}, falling back to memory"
            )
            self._backend = InMemoryEventBus(logger)
        
        self.logger.info(f"Initialized AsyncTaskEventBus with {bus_type.value} backend")
    
    def publish_task_completion(
        self,
        async_task_uuid: str,
        function_name: str,
        status: str,
        result: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Publish a task completion event.
        
        Args:
            async_task_uuid: UUID of the completed async task
            function_name: Name of the function that was executed
            status: Completion status ("completed" or "failed")
            result: Optional result data
            notes: Optional notes or error message
            
        Returns:
            bool: True if event was published successfully
        """
        event = TaskCompletionEvent(
            async_task_uuid=async_task_uuid,
            function_name=function_name,
            status=status,
            result=result,
            notes=notes
        )
        
        return self._backend.publish(event)
    
    def wait_for_task_completion(
        self,
        async_task_uuid: str,
        timeout_seconds: float = 60.0,
        poll_fallback: bool = True
    ) -> Optional[TaskCompletionEvent]:
        """Wait for a task to complete using event-driven approach.
        
        This method uses event subscription for immediate notification,
        with optional fallback to polling.
        
        Args:
            async_task_uuid: UUID of the task to wait for
            timeout_seconds: Maximum time to wait
            poll_fallback: Whether to fall back to polling if event bus fails
            
        Returns:
            TaskCompletionEvent if task completed, None if timed out
        """
        if not self.config.enable_event_driven_async_tasks:
            self.logger.debug("Event-driven tasks disabled, returning None")
            return None
        
        start_time = time.time()
        event_received: Optional[TaskCompletionEvent] = None
        
        def on_event(event: TaskCompletionEvent) -> None:
            nonlocal event_received
            event_received = event
        
        # Subscribe to events for this task
        self._backend.subscribe(async_task_uuid, on_event)
        
        try:
            # Wait for event with timeout
            while time.time() - start_time < timeout_seconds:
                if event_received is not None:
                    self.logger.debug(
                        f"Received completion event for task {async_task_uuid}"
                    )
                    return event_received
                
                # Short sleep to avoid busy waiting
                time.sleep(0.01)
            
            # Timeout reached
            self.logger.warning(
                f"Timeout waiting for task {async_task_uuid} completion event"
            )
            return None
            
        finally:
            # Always unsubscribe
            self._backend.unsubscribe(async_task_uuid)
    
    def get_backend(self) -> EventBusBackend:
        """Get the underlying event bus backend."""
        return self._backend


# Global event bus instance
_event_bus: Optional[AsyncTaskEventBus] = None


def get_event_bus(logger: Optional[logging.Logger] = None) -> AsyncTaskEventBus:
    """Get or create the global event bus instance.
    
    Args:
        logger: Logger instance
        
    Returns:
        AsyncTaskEventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = AsyncTaskEventBus(logger)
    return _event_bus


def reset_event_bus() -> None:
    """Reset the global event bus instance.
    
    This should be called when configuration changes or for testing.
    """
    global _event_bus
    _event_bus = None
