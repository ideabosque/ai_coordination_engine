#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from ..models.thread import delete_thread, insert_update_thread
from ..types.thread import ThreadType


class InsertUpdateThread(Mutation):
    thread = Field(ThreadType)

    class Arguments:
        session_uuid = String(required=True)
        thread_id = String(required=True)
        coordination_uuid = String(required=True)
        agent_uuid = String(required=False)
        last_assistant_message = String(required=False)
        status = String(required=False)
        log = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateThread":
        try:
            thread = insert_update_thread(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateThread(thread=thread)


class DeleteThread(Mutation):
    ok = Boolean()

    class Arguments:
        session_uuid = String(required=True)
        thread_id = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteThread":
        try:
            ok = delete_thread(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteThread(ok=ok)
