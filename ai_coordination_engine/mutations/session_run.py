#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, Mutation, String
from silvaengine_utility import JSONCamelCase

from ..models.session_run import delete_session_run, insert_update_session_run
from ..types.session_run import SessionRunType


class InsertUpdateSessionRun(Mutation):
    session_run = Field(SessionRunType)

    class Arguments:
        session_uuid = String(required=True)
        run_uuid = String(required=True)
        thread_uuid = String(required=True)
        agent_uuid = String(required=True)
        coordination_uuid = String(required=True)
        async_task_uuid = String(required=True)
        session_agent_uuid = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateSessionRun":
        try:
            session_run = insert_update_session_run(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateSessionRun(session_run=session_run)


class DeleteSessionRun(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        session_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteSessionRun":
        try:
            ok = delete_session_run(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteSessionRun(ok=ok)
