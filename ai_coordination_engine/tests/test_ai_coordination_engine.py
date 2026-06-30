#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import base64
import logging
import os
import sys
import unittest

from dotenv import load_dotenv

load_dotenv()
setting = {
    "region_name": os.getenv("region_name"),
    "aws_access_key_id": os.getenv("aws_access_key_id"),
    "aws_secret_access_key": os.getenv("aws_secret_access_key"),
    "api_id": os.getenv("api_id"),
    "api_stage": os.getenv("api_stage"),
    "task_queue_name": os.getenv("task_queue_name"),
    "functs_on_local": {
        "ai_coordination_graphql": {
            "module_name": "ai_coordination_engine",
            "class_name": "AICoordinationEngine",
        },
        "async_insert_update_session": {
            "module_name": "ai_coordination_engine",
            "class_name": "AICoordinationEngine",
        },
        "async_execute_procedure_task_session": {
            "module_name": "ai_coordination_engine",
            "class_name": "AICoordinationEngine",
        },
        "async_update_session_agent": {
            "module_name": "ai_coordination_engine",
            "class_name": "AICoordinationEngine",
        },
        "async_orchestrate_task_query": {
            "module_name": "ai_coordination_engine",
            "class_name": "AICoordinationEngine",
        },
        "ai_agent_core_graphql": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
        "async_execute_ask_model": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
        "async_insert_update_tool_call": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
        "send_data_to_websocket": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
    },
    "connection_id": os.getenv("connection_id"),
    "endpoint_id": os.getenv("endpoint_id"),
    "part_id": os.getenv("part_id"),
    "execute_mode": os.getenv("execute_mode"),
    "initialize_tables": int(os.getenv("initialize_tables", "0")),
    # ── Dual-backend selection ─────────────────────────────────────── #
    "db_backend": os.getenv("db_backend", "dynamodb"),
    "db_host": os.getenv("PG_HOST") or os.getenv("db_host"),
    "db_port": os.getenv("PG_PORT") or os.getenv("db_port"),
    "db_user": os.getenv("PG_USER") or os.getenv("db_user"),
    "db_password": os.getenv("PG_PASSWORD") or os.getenv("db_password"),
    "db_schema": os.getenv("PG_DB") or os.getenv("db_schema"),
    "database_url": os.getenv("DATABASE_URL"),
    "pg_table_prefix": os.getenv("ACE_PG_TABLE_PREFIX") or os.getenv("PG_TABLE_PREFIX") or "",
    # ── Internal MCP for AACE ──────────────────────────────────────── #
    "internal_mcp": {
        "base_url": os.getenv("internal_mcp_base_url") or os.getenv("mcp_server_url"),
        "bearer_token": os.getenv("internal_mcp_bearer_token") or os.getenv("bearer_token"),
        "headers": {
            "x-api-key": os.getenv("x-api-key"),
            "Content-Type": "application/json",
        },
    } if (os.getenv("internal_mcp_base_url") or os.getenv("mcp_server_url")) else None,
    "internal_mcp_token_username": os.getenv("internal_mcp_token_username", ""),
    "internal_mcp_token_password": os.getenv("internal_mcp_token_password", ""),
    "cache_enabled": int(os.getenv("cache_enabled", "0")),
}

sys.path.insert(0, f"{os.getenv('base_dir')}/ai_coordination_engine")
sys.path.insert(1, f"{os.getenv('base_dir')}/silvaengine_utility")
sys.path.insert(2, f"{os.getenv('base_dir')}/silvaengine_dynamodb_base")
sys.path.insert(3, f"{os.getenv('base_dir')}/ai_agent_core_engine")
sys.path.insert(4, f"{os.getenv('base_dir')}/ai_agent_handler")
sys.path.insert(5, f"{os.getenv('base_dir')}/openai_agent_handler")
sys.path.insert(6, f"{os.getenv('base_dir')}/ai_agent_funct_base")
sys.path.insert(7, f"{os.getenv('base_dir')}/ai_marketing_engine")
sys.path.insert(8, f"{os.getenv('base_dir')}/anthropic_agent_handler")
sys.path.insert(9, f"{os.getenv('base_dir')}/gemini_agent_handler")
sys.path.insert(10, f"{os.getenv('base_dir')}/travrse_agent_handler")
sys.path.insert(11, f"{os.getenv('base_dir')}/shopify_connector")
sys.path.insert(12, f"{os.getenv('base_dir')}/mcp_http_client")

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

from ai_coordination_engine import AICoordinationEngine
from silvaengine_utility.graphql import Graphql
from silvaengine_utility.serializer import Serializer


class AICoordinationEngineTest(unittest.TestCase):
    def setUp(self):
        self.ai_coordination_engine = AICoordinationEngine(logger, **setting)

        context = {
            "endpoint_id": setting.get("endpoint_id"),
            "part_id": setting.get("part_id"),
            "setting": setting,
            "logger": logger,
        }
        self.schema = Graphql.fetch_graphql_schema(
            context,
            "ai_coordination_graphql",
        )

        logger.info("Initiate AICoordinationEngineTest ...")

    def tearDown(self):
        logger.info("Destory AICoordinationEngineTest ...")

    @unittest.skip("demonstrating skipping")
    def test_graphql_ping(self):
        query = Graphql.generate_graphql_operation("ping", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {},
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_coordination(self):
        query = Graphql.generate_graphql_operation(
            "insertUpdateCoordination", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "02307992733415915648",
                "coordinationName": "RFQ Op",
                "coordinationDescription": "XXXXXXXXXXXXXXXXXXXX",
                "agents": [],
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_coordination(self):
        query = Graphql.generate_graphql_operation(
            "deleteCoordination", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "13054439966881681904",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_coordination(self):
        query = Graphql.generate_graphql_operation("coordination", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "02307992733415915648",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_coordination_list(self):
        query = Graphql.generate_graphql_operation(
            "coordinationList", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {"coordinationName": "RFQ Op"},
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_session(self):
        query = Graphql.generate_graphql_operation(
            "insertUpdateSession", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "02307992733415915648",
                "sessionUuid": "04405618665134768256",
                # "status": "active",
                # "logs": "null",
                "subtaskQueries": [],
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_session(self):
        query = Graphql.generate_graphql_operation(
            "deleteSession", "Mutation", self.schema
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
        query = Graphql.generate_graphql_operation("session", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "02307992733415915648",
                "sessionUuid": "04405618665134768256",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session_list(self):
        query = Graphql.generate_graphql_operation("sessionList", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "02307992733415915648",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_session_run(self):
        query = Graphql.generate_graphql_operation(
            "insertUpdateSessionRun", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "04405618665134768256",
                "runUuid": "26483373014571845633",
                "threadUuid": "29357596428870387713",
                "agentUuid": "agent-1757495508-c9c63059",
                "coordinationUuid": "02307992733415915648",
                "asyncTaskUuid": "07033402805706065921",
                "sessionAgentUuid": "58605131920884908160",
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_session_run(self):
        query = Graphql.generate_graphql_operation(
            "deleteSessionRun", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "4175379880301105648",
                "runUuid": "XXXXXXXXXXXXXXXXXXXX",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session_run(self):
        query = Graphql.generate_graphql_operation("sessionRun", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "10547781798079042032",
                "runUuid": "17109886231683338736",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        response = Serializer.json_loads(response)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session_run_list(self):
        query = Graphql.generate_graphql_operation(
            "sessionRunList", "Query", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "4175379880301105648",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_task(self):
        query = Graphql.generate_graphql_operation(
            "insertUpdateTask", "Mutation", self.schema
        )
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "02307992733415915648",
                "taskUuid": "95179718047602589824",
                "taskName": "process_data",
                "taskDescription": "process_datsa",
                "initialTaskQuery": "Please find the data",
                "subtaskQueries": [
                    {
                        "agent_uuid": "agent-1742100810-b249e03b",
                        "subtask_query": "Retrieve products related to carpet cleaning using `get_results_from_knowledge_rag`. Provide detailed product specifications including cleaning method, material compatibility, and usage instructions.",
                    },
                    {
                        "agent_uuid": "agent-1742509982-34c5835d",
                        "subtask_query": "Translate the product information retrieved about carpet cleaning into Chinese. Ensure the translation is clear and suitable for supplier communication, focusing on key details such as cleaning method, material compatibility, and usage instructions.",
                    },
                ],
                "agentActions": {},
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_task(self):
        query = Graphql.generate_graphql_operation(
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
        query = Graphql.generate_graphql_operation("task", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "7339318953952874992",
                "taskUuid": "6753533827658093040",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_task_list(self):
        query = Graphql.generate_graphql_operation("taskList", "Query", self.schema)
        logger.info(f"Query: {query}")
        payload = {
            "query": query,
            "variables": {
                "coordinationUuid": "7339318953952874992",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_session_agent(self):
        query = Graphql.generate_graphql_operation(
            "insertUpdateSessionAgent", "Mutation", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "04405618665134768256",
                "sessionAgentUuid": "58605131920884908160",
                "coordinationUuid": "7339318953952874992",
                "agentUuid": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                # "agentAction": "",
                # "userInput": "",
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
        query = Graphql.generate_graphql_operation(
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
        query = Graphql.generate_graphql_operation("sessionAgent", "Query", self.schema)
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "4175379880301105648",
                "sessionAgentUuid": "13128846641751003632",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_session_agent_list(self):
        query = Graphql.generate_graphql_operation(
            "sessionAgentList", "Query", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "4175379880301105648",
                # "predecessors": ["B2B AI Communication Assistant"],
                # "predecessor": "B2B AI Communication Assistant",
                # "userInTheLoop": "Bibo W.",
                # "states": ["initial"],
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_insert_update_task_schedule(self):
        query = Graphql.generate_graphql_operation(
            "insertUpdateTaskSchedule", "Mutation", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "95179718047602589824",
                "scheduleUuid": "71070891704682823808",
                "coordinationUuid": "02307992733415915648",
                "schedule": "*,*,*,*,*,*",
                "updatedBy": "XYZ",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_delete_task_schedule(self):
        query = Graphql.generate_graphql_operation(
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
        query = Graphql.generate_graphql_operation("taskSchedule", "Query", self.schema)
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "6753533827658093040",
                "scheduleUuid": "3318581209527161328",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_task_schedule_list(self):
        query = Graphql.generate_graphql_operation(
            "taskScheduleList", "Query", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "taskUuid": "6753533827658093040",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_ask_operaion_hub(self):
        ######################
        ## Add input files. ##
        file_path = f"{os.getenv('base_dir')}/ai_coordination_engine/ai_coordination_engine/tests/INW Phoenix Formulations Amino Bid 11.08 (added manufacturers).xlsx"
        # Extract the filename
        filename = os.path.basename(file_path)
        # Read the file and encode it in Base64
        encoded_content = None
        with open(file_path, "rb") as file:
            file_content = file.read()
            encoded_content = base64.b64encode(file_content).decode("utf-8")
        input_files = [{"filename": filename, "encoded_content": encoded_content}]
        ## Add input files. ##
        ######################

        query = Graphql.generate_graphql_operation(
            "askOperationHub", "Query", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                # "coordinationUuid": "7339318953952874992",
                # "agentUuid": "agent-1742509982-34c5835d",
                # "sessionUuid": "56499375834730992",
                # "threadUuid": "700638002290430448",
                # "userQuery": "Communication! Please ask the provider have the detail of product catalog in Chinese.",
                "coordinationUuid": "2435144671132914160",
                # "agentUuid": "agent-1742422854-45fe2761",
                # "userQuery": "place_uuid: 10961680129630147056",
                "agentUuid": "agent-1749683202-d8abb5a2",
                "userQuery": """Please Process the content of the file according to the detailed instructions and provide the public download link as well.""",
                "inputFiles": input_files,
                "userId": "XXXXXXXXXXXXXXXXXXX",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("Interactive chatbot test — requires stdin, skipped in automated runs")
    def test_run_chatbot_on_local(self):
        logger.info("Starting chatbot on local usage mode...")

        session_uuid = None
        thread_uuid = None
        while True:
            user_input = input("User: ")
            if user_input.strip().lower() in ["exit", "quit"]:
                logger.info("User requested exit. Stopping the chatbot.")
                print("Chatbot: Goodbye!")
                break

            query = Graphql.generate_graphql_operation(
                "askOperationHub", "Query", self.schema
            )
            logger.info(f"Query: {query}")

            payload = {
                "query": query,
                "variables": {
                    "coordinationUuid": "2435144671132914168",
                    # "agentUuid": "agent-1758131053-92b0e475",
                    "agentUuid": "agent-1757495508-c9c63059",
                    # "agentUuid": "agent-1761878365-24e3e9af",
                    # "agentUuid": "agent-1764104706-a4356066",
                    "sessionUuid": session_uuid,
                    "threadUuid": thread_uuid,
                    "userQuery": user_input,
                    # "userId": "XXXXXXXXXXXXXXXXXXX",
                    "stream": True,
                },
            }
            response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
            response = Serializer.json_loads(response["body"])["data"]

            if response["askOperationHub"]["threadUuid"] is not None:
                thread_uuid = response["askOperationHub"]["threadUuid"]
                session_uuid = response["askOperationHub"]["sessionUuid"]

            query = Graphql.generate_graphql_operation(
                "sessionRun", "Query", self.schema
            )
            logger.info(f"Query: {query}")
            payload = {
                "query": query,
                "variables": {
                    "sessionUuid": session_uuid,
                    "runUuid": response["askOperationHub"]["runUuid"],
                },
            }
            response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
            response = Serializer.json_loads(response["body"])["data"]

            # Print response to user
            print(f"Chatbot: {response['sessionRun']['asyncTask']['result']}")

    @unittest.skip("demonstrating skipping")
    def test_graphql_execute_procedure_task_session(self):
        query = Graphql.generate_graphql_operation(
            "executeProcedureTaskSession", "Mutation", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                # "coordinationUuid": "8033443114236711408",
                # "taskUuid": "6753533827658093040",
                # "taskQuery": (
                #     "Please retrieve products related to carpet cleaning and provide detailed specifications.\n"
                #     "Then translate the product information into Chinese for effective communication with the supplier.\n"
                #     "Include key details such as cleaning method, material compatibility, and usage instructions."
                # ),
                #
                # "coordinationUuid": "217434188865016304",
                # "taskUuid": "2145007703059665392",
                # "taskQuery": Serializer.json_dumps(
                #     {
                #         "company_name": "apple.com",
                #         "topics": [
                #             "Overview",
                #             "Products and Services",
                #             "Financial Data",
                #             "Leadership",
                #         ],
                #     }
                # ),
                #
                # "coordinationUuid": "17700117941906182640",
                # "taskUuid": "655993144917430768",
                # "taskQuery": "find the overview and financial information for apple.com",
                #
                "coordinationUuid": "64512187470233406923",
                "taskUuid": "83542177430094155211",
                "taskQuery": Serializer.json_dumps(
                    {
                        "company_name": "apple.com",
                        "user": "Bibo Wang",
                        "email": "bibo72@outlook.com",
                    }
                ),
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)

    @unittest.skip("demonstrating skipping")
    def test_graphql_execute_for_user_input(self):
        query = Graphql.generate_graphql_operation(
            "executeForUserInput", "Mutation", self.schema
        )
        payload = {
            "query": query,
            "variables": {
                "sessionUuid": "89473965385405448320",
                "sessionAgentUuid": "80224377972519354496",
                "userInput": "Please focus on Apple Vision for partnership.",
            },
        }
        response = self.ai_coordination_engine.ai_coordination_graphql(**payload)
        logger.info(response)


if __name__ == "__main__":
    unittest.main()
