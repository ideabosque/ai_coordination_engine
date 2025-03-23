#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, Mutation, String

from silvaengine_utility import JSON

from ..models.session_thread import delete_session_thread, insert_update_session_thread
from ..types.session_thread import SessionThreadType


class InsertUpdateSessionThread(Mutation):
    session_thread = Field(SessionThreadType)

    class Arguments:
        session_uuid = String(required=True)
        thread_uuid = String(required=True)
        agent_uuid = String(required=True)
        coordination_uuid = String(required=True)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateSessionThread":
        try:
            session_thread = insert_update_session_thread(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateSessionThread(session_thread=session_thread)


class DeleteSessionThread(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        session_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteSessionThread":
        try:
            ok = delete_session_thread(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteSessionThread(ok=ok)
