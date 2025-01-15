#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import json
import logging
import os
import sys
import time
import unittest
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
setting = {
    "region_name": os.getenv("region_name"),
    "aws_access_key_id": os.getenv("aws_access_key_id"),
    "aws_secret_access_key": os.getenv("aws_secret_access_key"),
}

document = Path(
    os.path.join(os.path.dirname(__file__), "ai_coordination_engine.graphql")
).read_text()
sys.path.insert(0, f"{os.getenv('base_dir')}/ai_coordination_engine")
sys.path.insert(1, f"{os.getenv('base_dir')}/silvaengine_dynamodb_base")

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

from ai_coordination_engine import AICoordinationEngine


class AICoordinationEngineTest(unittest.TestCase):
    def setUp(self):
        self.ai_coordination_engine = AICoordinationEngine(logger, **setting)
        logger.info("Initiate AICoordinationEngineTest ...")

    def tearDown(self):
        logger.info("Destory AICoordinationEngineTest ...")

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_coordination(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationType": "operation",
                # "coordinationUuid": "1057228940262445551",
                "coordinationName": "RFQ Op",
                "coordinationDescription": "XXXXXXXXXXXXXXXXXXXX",
                "assistantId": "asst_CRw6YN4ZAZ2w7fz7LqYetrbm",
                "assistantType": "conversation",
                "additionalInstructions": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "updatedBy": "XYZ",
            },
            "operation_name": "insertUpdateCoordination",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_coordination(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationType": "operation",
                "coordinationUuid": "5795829138505404911",
            },
            "operation_name": "deleteCoordination",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_coordination(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationType": "operation",
                "coordinationUuid": "1057228940262445551",
            },
            "operation_name": "getCoordination",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_coordination_list(self):
        payload = {
            "query": document,
            "variables": {"coordinationType": "operation"},
            "operation_name": "getCoordinationList",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_agent(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "agentUuid": "14313717474430489071",
                # "agentName": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "agentDescription": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "agentInstructions": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "coordinationType": "operation",
                "responseFormat": "auto",
                # "predecessor": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "successor": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "updatedBy": "XYZ",
            },
            "operation_name": "insertUpdateAgent",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_agent(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "agentUuid": "6839313776147829231",
            },
            "operation_name": "deleteAgent",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_agent(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "agentUuid": "14313717474430489071",
            },
            "operation_name": "getAgent",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_agent_list(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
            },
            "operation_name": "getAgentList",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_session(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "sessionUuid": "7172266856517145071",
                "coordinationType": "operation",
                "status": "active",
                "notes": "null",
                "updatedBy": "XYZ",
            },
            "operation_name": "insertUpdateSession",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_session(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "sessionUuid": "2194841317416964591",
            },
            "operation_name": "deleteSession",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "sessionUuid": "11763350835914674671",
            },
            "operation_name": "getSession",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    # @unittest.skip("demonstrating skipping")
    def test_graphql_session_list(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
            },
            "operation_name": "getSessionList",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_thread(self):
        payload = {
            "query": document,
            "variables": {
                "sessionUuid": "7172266856517145071",
                "threadId": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "coordinationUuid": "1057228940262445551",
                "agentUuid": "14313717474430489071",
                "lastAssistantMessage": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "log": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "updatedBy": "XYZ",
            },
            "operation_name": "insertUpdateThread",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_thread(self):
        payload = {
            "query": document,
            "variables": {
                "sessionUuid": "11763350835914674671",
                "messageId": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            },
            "operation_name": "deleteThread",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_thread(self):
        payload = {
            "query": document,
            "variables": {
                "sessionUuid": "13393439109748756975",
                "threadId": "thread_BITniZMWRWXj6kFuVg5vsnPj",
            },
            "operation_name": "getThread",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_thread_list(self):
        payload = {
            "query": document,
            "variables": {
                "sessionUuid": "13393439109748756975",
            },
            "operation_name": "getThreadList",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)


if __name__ == "__main__":
    unittest.main()
