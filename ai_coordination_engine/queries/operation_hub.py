#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..handlers.ai_coordination_utility import get_presigned_aws_s3_url
from ..handlers.operation_hub import operation_hub
from ..types.operation_hub import AskOperationHubType, PresignedAWSS3UrlType


def resolve_presigned_aws_s3_url(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> PresignedAWSS3UrlType:
    return get_presigned_aws_s3_url(info, **kwargs)


def resolve_ask_operation_hub(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AskOperationHubType:
    return operation_hub.ask_operation_hub(info, **kwargs)
