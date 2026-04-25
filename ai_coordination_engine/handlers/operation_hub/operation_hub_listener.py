# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import time
from typing import Any, Dict

from silvaengine_utility import Serializer

from ...models.session import insert_update_session, resolve_session
from ...models.session_run import resolve_session_run
from ...utils.listener import create_listener_info
from ..ai_coordination_utility import get_async_task
from ..config import Config


def async_insert_update_session(
    logger: logging.Logger,
    setting: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> None:
    """
    Asynchronously inserts or updates a session based on async task status.
    Monitors the async task execution and updates session logs if task fails.

    Args:
        logger: Logger instance for logging messages
        setting: Dictionary containing configuration settings
        kwargs: Additional keyword arguments including:
            - coordination_uuid: UUID of the coordination
            - session_uuid: UUID of the session
            - run_uuid: UUID of the run
    """
    if not kwargs.get("session_uuid") or not kwargs.get("run_uuid"):
        raise ValueError("Invalid required parameter(s)")

    # Create listener info with session details
    info = create_listener_info(logger, "insert_update_session", setting, **kwargs)

    # Resolve the session run using session and run UUIDs
    session_run = resolve_session_run(
        info,
        **{
            "session_uuid": kwargs["session_uuid"],
            "run_uuid": kwargs["run_uuid"],
        },
    )
    if session_run is None:
        raise ValueError("Session run not found")

    # Poll async task status with configurable timeout and backoff
    polling_timeout = getattr(Config, "ASYNC_TASK_TIMEOUT", 60)
    initial_sleep = 0.5
    max_sleep = 3.0
    sleep_time = initial_sleep
    start_time = time.time()

    while True:
        async_task = get_async_task(
            info.context,
            **{
                "functionName": "async_execute_ask_model",
                "asyncTaskUuid": session_run.async_task_uuid,
            },
        )

        # Only resolve session and deserialize logs when we need to write
        if (
            async_task["status"] in ("failed", "completed")
            or time.time() - start_time > polling_timeout
        ):
            session = resolve_session(
                info,
                **{
                    "coordination_uuid": kwargs["coordination_uuid"],
                    "session_uuid": kwargs["session_uuid"],
                },
            )
            if session is None:
                raise ValueError("Session not found")
            logs = Serializer.json_loads(session.logs if session.logs else "[]")

            if async_task["status"] == "failed":
                logs.append(
                    {
                        "run_uuid": kwargs["run_uuid"],
                        "log": async_task.get("notes", "Task failed."),
                    }
                )
                status = "failed"
            elif async_task["status"] == "completed":
                logs.append(
                    {
                        "run_uuid": kwargs["run_uuid"],
                        "log": "Task completed successfully.",
                    }
                )
                status = None
            else:
                logs.append(
                    {
                        "run_uuid": kwargs["run_uuid"],
                        "log": f"The task has timed out after {polling_timeout} seconds.",
                    }
                )
                status = "timeout"

            update_kwargs = {
                "coordination_uuid": kwargs["coordination_uuid"],
                "session_uuid": kwargs["session_uuid"],
                "logs": Serializer.json_dumps(logs),
                "updated_by": "operation_hub",
            }
            if status is not None:
                update_kwargs["status"] = status

            insert_update_session(info, **update_kwargs)

            logger.info(
                f"Async task finished",
                extra={
                    "status": async_task["status"],
                    "elapsed_seconds": round(time.time() - start_time, 2),
                    "session_uuid": kwargs.get("session_uuid"),
                },
            )
            break
        else:
            logger.debug(
                f"Async task still running, sleeping {sleep_time}s",
                extra={
                    "status": async_task.get("status"),
                    "elapsed_seconds": round(time.time() - start_time, 2),
                },
            )
            time.sleep(sleep_time)
            sleep_time = min(sleep_time * 1.5, max_sleep)
