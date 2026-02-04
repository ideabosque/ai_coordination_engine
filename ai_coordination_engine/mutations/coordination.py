#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String
from silvaengine_utility import JSONCamelCase

from ..models.coordination import delete_coordination, insert_update_coordination
from ..types.coordination import CoordinationType


class InsertUpdateCoordination(Mutation):
    coordination = Field(CoordinationType)

    class Arguments:
        coordination_uuid = String(required=False)
        coordination_name = String(required=False)
        coordination_description = String(required=False)
        agents = List(JSONCamelCase, required=False)
        theme_uuid = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateCoordination":
        try:
            coordination = insert_update_coordination(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateCoordination(coordination=coordination)


class DeleteCoordination(Mutation):
    ok = Boolean()

    class Arguments:
        coordination_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteCoordination":
        try:
            ok = delete_coordination(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteCoordination(ok=ok)
