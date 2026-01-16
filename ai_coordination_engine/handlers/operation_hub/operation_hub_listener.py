# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import time
from typing import Any, Dict

from silvaengine_utility import Debugger, Serializer

from ...models.session import insert_update_session, resolve_session
from ...models.session_run import resolve_session_run
from ...utils.listener import create_listener_info
from ..ai_coordination_utility import get_async_task


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

    # Poll async task status with 60 second timeout
    start_time = time.time()

    while True:
        async_task = get_async_task(
            info.context,
            **{
                "functionName": "async_execute_ask_model",
                "asyncTaskUuid": session_run.async_task_uuid,
            },
        )
        session = resolve_session(
            info,
            **{
                "coordination_uuid": kwargs["coordination_uuid"],
                "session_uuid": kwargs["session_uuid"],
            },
        )
        logs = Serializer.json_loads(session.logs if session.logs else "[]")

        if async_task["status"] == "failed" or time.time() - start_time > 60:
            # If async task failed, update session with failure details
            status = "failed" if async_task["status"] == "failed" else "timeout"
            logs.append(
                {
                    "run_uuid": kwargs["run_uuid"],
                    "log": (
                        async_task["notes"]
                        if status == "failed"
                        else "The task has timed out."
                    ),
                }
            )
            session = insert_update_session(
                info,
                **{
                    "coordination_uuid": kwargs["coordination_uuid"],
                    "session_uuid": kwargs["session_uuid"],
                    "status": status,
                    "logs": Serializer.json_dumps(logs),
                    "updated_by": "operation_hub",
                },
            )

            break
        elif async_task["status"] == "completed":
            logs.append(
                {
                    "run_uuid": kwargs["run_uuid"],
                    "log": "Task completed successfully.",
                }
            )
            session = insert_update_session(
                info,
                **{
                    "coordination_uuid": kwargs["coordination_uuid"],
                    "session_uuid": kwargs["session_uuid"],
                    "logs": Serializer.json_dumps(logs),
                    "updated_by": "operation_hub",
                },
            )
            # TODO: Send email if receiver_email is in kwargs
            break
        else:
            # Wait for 1 second before checking again
            time.sleep(1)

    Debugger.info(
        variable="",
        stage=f"{__name__}: async_insert_update_session",
        delimiter="#",
        setting=setting,
    )
