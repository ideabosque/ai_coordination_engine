#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from ..models.session import delete_session, insert_update_session
from ..types.session import SessionType


class InsertUpdateSession(Mutation):
    session = Field(SessionType)

    class Arguments:
        coordination_uuid = String(required=True)
        session_uuid = String(required=False)
        coordination_type = String(required=False)
        status = String(required=False)
        notes = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateSession":
        try:
            session = insert_update_session(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateSession(session=session)


class DeleteSession(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)
        session_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteSession":
        try:
            ok = delete_session(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteSession(ok=ok)
