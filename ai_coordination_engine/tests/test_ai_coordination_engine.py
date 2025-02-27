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
    "endpoint_id": os.getenv("endpoint_id"),
    "test_mode": os.getenv("TEST_MODE"),
    "functs_on_local": {
        "ai_coordination_graphql": {
            "module_name": "ai_coordination_engine",
            "class_name": "AICoordinationEngine",
        },
    },
}

sys.path.insert(0, f"{os.getenv('base_dir')}/ai_coordination_engine")
sys.path.insert(1, f"{os.getenv('base_dir')}/silvaengine_dynamodb_base")

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

from ai_coordination_engine import AICoordinationEngine
from silvaengine_utility import Utility


class AICoordinationEngineTest(unittest.TestCase):
    def setUp(self):
        self.ai_coordination_engine = AICoordinationEngine(logger, **setting)
        endpoint_id = setting.get("endpoint_id")
        test_mode = setting.get("test_mode")
        self.schema = Utility.fetch_graphql_schema(
            logger,
            endpoint_id,
            "ai_coordination_graphql",
            setting=setting,
            test_mode=test_mode,
        )

        logger.info("Initiate AICoordinationEngineTest ...")

    def tearDown(self):
        logger.info("Destory AICoordinationEngineTest ...")

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_coordination(self):
        query = Utility.generate_graphql_operation(
            "insertUpdateCoordination", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationType": "operation",
                # "coordinationUuid": "1057228940262445551",
                "coordinationName": "RFQ Op",
                "coordinationDescription": "XXXXXXXXXXXXXXXXXXXX",
                "assistantId": "asst_CRw6YN4ZAZ2w7fz7LqYetrbm",
                "additionalInstructions": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_coordination(self):
        query = Utility.generate_graphql_operation(
            "deleteCoordination", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "15277018802377658863",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_coordination(self):
        query = Utility.generate_graphql_operation(
            "getCoordination", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "15277018802377658863",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_coordination_list(self):
        query = Utility.generate_graphql_operation(
            "getCoordinationList", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {"coordinationName": "RFQ Op"},
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_agent(self):
        query = Utility.generate_graphql_operation(
            "insertUpdateAgent", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "7414700151911289327",
                "agentVersionUuid": "14987473663722983919",
                "agentName": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "agentDescription": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "agentInstructions": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "coordinationType": "operation",
                "responseFormat": "auto",
                # "predecessor": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "successor": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "status": "active",
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_agent(self):
        query = Utility.generate_graphql_operation("deleteAgent", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "agentUuid": "6839313776147829231",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_agent(self):
        query = Utility.generate_graphql_operation("getAgent", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "7414700151911289327",
                "agentName": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_agent_list(self):
        query = Utility.generate_graphql_operation("agentList", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "7414700151911289327",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_session(self):
        query = Utility.generate_graphql_operation(
            "insertUpdateSession", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "7414700151911289327",
                # "sessionUuid": "7172266856517145071",
                "status": "active",
                "notes": "null",
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_session(self):
        query = Utility.generate_graphql_operation(
            "deleteSession", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "sessionUuid": "2194841317416964591",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session(self):
        query = Utility.generate_graphql_operation("getSession", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "7414700151911289327",
                "sessionUuid": "16505656650518893039",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session_list(self):
        query = Utility.generate_graphql_operation(
            "getSessionList", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "1057228940262445551",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_thread(self):
        query = Utility.generate_graphql_operation(
            "insertUpdateThread", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "16505656650518893039",
                "threadId": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "coordinationUuid": "7414700151911289327",
                "agentName": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "lastAssistantMessage": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "log": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_thread(self):
        query = Utility.generate_graphql_operation("deleteThread", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "11763350835914674671",
                "messageId": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_thread(self):
        query = Utility.generate_graphql_operation("thread", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "16505656650518893039",
                "threadId": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_thread_list(self):
        query = Utility.generate_graphql_operation("threadList", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "13393439109748756975",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_task(self):
        query = Utility.generate_graphql_operation(
            "insertUpdateTask", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "taskUuid": "5077563706321605103",
                "taskName": "process_data",
                "taskDescription": "process_datsa",
                "initialTaskQuery": "Please find the data",
                "agentActions": [],
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_task(self):
        query = Utility.generate_graphql_operation(
            "deleteTask", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "taskUuid": "17856133366692516335",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_task(self):
        query = Utility.generate_graphql_operation("task", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "1057228940262445551",
                "taskUuid": "5077563706321605103",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_task_list(self):
        query = Utility.generate_graphql_operation("taskList", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "1057228940262445551",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_task_session(self):
        query = Utility.generate_graphql_operation(
            "insertUpdateTaskSession", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "5077563706321605103",
                "sessionUuid": "16505656650518893039",
                "coordinationUuid": "7414700151911289327",
                "taskQuery": "Please find the data",
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_task_session(self):
        query = Utility.generate_graphql_operation(
            "deleteTaskSession", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "5077563706321605103",
                "sessionUuid": "1067071150838256111",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_task_session(self):
        query = Utility.generate_graphql_operation("taskSession", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "5077563706321605103",
                "sessionUuid": "16505656650518893039",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_task_session_list(self):
        query = Utility.generate_graphql_operation(
            "taskSessionList", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "5077563706321605103",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    # @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_session_agent(self):
        query = Utility.generate_graphql_operation(
            "insertUpdateSessionAgent", "Mutation", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "16505656650518893039",
                "sessionAgentUuid": "14411869504290230767",
                "threadId": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                "taskUuid": "5077563706321605103",
                "agentName": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "userInTheLoop": "",
                # "userAction": "",
                # "agentInput": "",
                # "agentOutput": "",
                # "predecessor": "",
                "inDegree": 1,
                # "state": "",
                # "notes": "",
                "updatedBy": "Bibo W.",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_session_agent(self):
        query = Utility.generate_graphql_operation(
            "deleteSessionAgent", "Mutation", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "16505656650518893039",
                "sessionAgentUuid": "10408353852863615471",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session_agent(self):
        query = Utility.generate_graphql_operation("sessionAgent", "Query", self.schema)
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "16505656650518893039",
                "sessionAgentUuid": "14411869504290230767",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session_agent_list(self):
        query = Utility.generate_graphql_operation(
            "sessionAgentList", "Query", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "16505656650518893039",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_task_schedule(self):
        query = Utility.generate_graphql_operation(
            "insertUpdateTaskSchedule", "Mutation", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "5077563706321605103",
                # "scheduleUuid": "13834605610270527983",
                "coordinationUuid": "7414700151911289327",
                "schedule": "*,*,*,*,*,*",
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_task_schedule(self):
        query = Utility.generate_graphql_operation(
            "deleteTaskSchedule", "Mutation", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "5077563706321605103",
                "scheduleUuid": "13834605610270527983",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_task_schedule(self):
        query = Utility.generate_graphql_operation("taskSchedule", "Query", self.schema)
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "5077563706321605103",
                "scheduleUuid": "18006023039515169263",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_task_schedule_list(self):
        query = Utility.generate_graphql_operation(
            "taskScheduleList", "Query", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "5077563706321605103",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)


if __name__ == "__main__":
    unittest.main()
