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
from ..config_manager import get_performance_config
from ..procedure_hub.smart_polling import poll_async_task_smart


def async_insert_update_session(
    logger: logging.Logger,
    setting: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> None:
    """
    Asynchronously inserts or updates a session based on async task status.
    Monitors the async task execution and updates session logs if task fails.
    Uses smart polling for improved performance.

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

    info = create_listener_info(logger, "insert_update_session", setting, **kwargs)

    session_run = resolve_session_run(
        info,
        **{
            "session_uuid": kwargs["session_uuid"],
            "run_uuid": kwargs["run_uuid"],
        },
    )

    config = get_performance_config()

    def task_fetcher():
        return get_async_task(
            info.context,
            **{
                "functionName": "async_execute_ask_model",
                "asyncTaskUuid": session_run.async_task_uuid,
            },
        )

    poll_result = poll_async_task_smart(
        task_fetcher=task_fetcher,
        logger=logger,
        task_type="ask_model",
        custom_config=config
    )

    session = resolve_session(
        info,
        **{
            "coordination_uuid": kwargs["coordination_uuid"],
            "session_uuid": kwargs["session_uuid"],
        },
    )
    logs = Serializer.json_loads(session.logs if session.logs else "[]")

    if poll_result.status == "completed":
        logs.append(
            {
                "run_uuid": kwargs["run_uuid"],
                "log": "Task completed successfully.",
            }
        )
        insert_update_session(
            info,
            **{
                "coordination_uuid": kwargs["coordination_uuid"],
                "session_uuid": kwargs["session_uuid"],
                "logs": Serializer.json_dumps(logs),
                "updated_by": "operation_hub",
            },
        )
    elif poll_result.status == "failed":
        logs.append(
            {
                "run_uuid": kwargs["run_uuid"],
                "log": poll_result.notes or "Task failed.",
            }
        )
        insert_update_session(
            info,
            **{
                "coordination_uuid": kwargs["coordination_uuid"],
                "session_uuid": kwargs["session_uuid"],
                "status": "failed",
                "logs": Serializer.json_dumps(logs),
                "updated_by": "operation_hub",
            },
        )
    else:
        logs.append(
            {
                "run_uuid": kwargs["run_uuid"],
                "log": f"The task has timed out after {poll_result.total_duration:.1f} seconds.",
            }
        )
        insert_update_session(
            info,
            **{
                "coordination_uuid": kwargs["coordination_uuid"],
                "session_uuid": kwargs["session_uuid"],
                "status": "timeout",
                "logs": Serializer.json_dumps(logs),
                "updated_by": "operation_hub",
            },
        )
