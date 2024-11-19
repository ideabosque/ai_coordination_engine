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
sys.path.insert(0, "/var/www/projects/ai_coordination_engine")
sys.path.insert(1, "/var/www/projects/silvaengine_dynamodb_base")

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
                "coordinationUuid": "1057228940262445551",
                "coordinationName": "RFQ Op",
                "coordinationDescription": "XXXXXXXXXXXXXXXXXXXX",
                "assistantId": "asst_CRw6YN4ZAZ2w7fz7LqYetrbm",
                "assistantType": "conversation",
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
                "coordinationUuid": "11097893215860822511",
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
    def test_graphql_get_coordination_list(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationType": "operation",
            },
            "operation_name": "getCoordinationList",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_coordination_agent(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "agentUuid": "14313717474430489071",
                "agentName": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "agentDescription": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "agentInstructions": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "agentAdditionalInstructions": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "coordinationType": "operation",
                "responseFormat": "auto",
                "predecessor": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "successor": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "updatedBy": "XYZ",
            },
            "operation_name": "insertUpdateCoordinationAgent",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_coordination_agent(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "agentUuid": "6839313776147829231",
            },
            "operation_name": "deleteCoordinationAgent",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_coordination_agent(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "agentUuid": "14313717474430489071",
            },
            "operation_name": "getCoordinationAgent",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    # @unittest.skip("demonstrating skipping")
    def test_graphql_get_coordination_agent_list(self):
        payload = {
            "query": document,
            "variables": {
                "coordinationUuid": "1057228940262445551",
            },
            "operation_name": "getCoordinationAgentList",
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)


if __name__ == "__main__":
    unittest.main()
