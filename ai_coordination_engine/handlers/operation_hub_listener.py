# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import time
from typing import Any, Dict

from silvaengine_utility import Utility

from ..models.session import insert_update_session, resolve_session
from ..models.session_run import resolve_session_run
from .ai_coordination_utility import create_listener_info, get_async_task


def async_insert_update_session(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    info = create_listener_info(logger, "insert_update_session", setting, **kwargs)

    session_run = resolve_session_run(
        info,
        **{
            "session_uuid": kwargs["session_uuid"],
            "run_uuid": kwargs["run_uuid"],
        },
    )

    start_time = time.time()
    while True:
        async_task = get_async_task(
            info.context.get("logger"),
            info.context.get("endpoint_id"),
            info.context.get("setting"),
            **{
                "functionName": "async_execute_ask_model",
                "asyncTaskUuid": session_run.async_task_uuid,
            },
        )

        if async_task["status"] in ["completed", "failed"]:
            break
        if time.time() - start_time > 60:
            break
        time.sleep(1)

    if async_task["status"] == "failed":
        session = resolve_session(
            info,
            **{
                "coordination_uuid": kwargs["coordination_uuid"],
                "session_uuid": kwargs["session_uuid"],
            },
        )
        logs = Utility.json_loads(session.logs if session.logs else "{}")
        logs[kwargs["run_uuid"]] = async_task["logs"]

        session = insert_update_session(
            info,
            **{
                "coordination_uuid": kwargs["coordination_uuid"],
                "session_uuid": kwargs["session_uuid"],
                "status": async_task["status"],
                "logs": Utility.json_dumps(logs),
                "updated_by": "operation_hub",
            },
        )

    # Send email if receiver_email is in kwargs
