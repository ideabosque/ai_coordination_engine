#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Live integration test runner — captures all GraphQL inputs/outputs for the certification report."""
from __future__ import print_function
import os, sys, json, uuid, logging, time
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
logger = logging.getLogger("live_runner")

SETTING = {
    "region_name": os.getenv("region_name"),
    "aws_access_key_id": os.getenv("aws_access_key_id"),
    "aws_secret_access_key": os.getenv("aws_secret_access_key"),
    "endpoint_id": os.getenv("endpoint_id", "gpt"),
    "part_id": os.getenv("part_id", "neprodai"),
    "execute_mode": "local_for_all",
    "initialize_tables": 0,
    "cache_enabled": 0,
    "db_backend": "postgresql",
    "database_url": os.getenv("DATABASE_URL"),
    "db_host": os.getenv("PG_HOST", "localhost"),
    "db_port": os.getenv("PG_PORT", "5432"),
    "db_user": os.getenv("PG_USER", "silvaengine"),
    "db_password": os.getenv("PG_PASSWORD", "silvaengine"),
    "db_schema": os.getenv("PG_DB", "silvaengine"),
    "pg_table_prefix": os.getenv("ACE_PG_TABLE_PREFIX", ""),
    "functs_on_local": {
        "ai_coordination_graphql": {"module_name": "ai_coordination_engine", "class_name": "AICoordinationEngine"},
        "ai_agent_core_graphql": {"module_name": "ai_agent_core_engine", "class_name": "AIAgentCoreEngine"},
    },
}
PK = "gpt#neprodai"

from ai_coordination_engine import AICoordinationEngine
eng = AICoordinationEngine(logger, **SETTING)
schema = AICoordinationEngine.build_graphql_schema()

call_log = []
call_num = [0]

def gql(query, variables=None, scenario_id=""):
    call_num[0] += 1
    n = call_num[0]
    t0 = time.time()
    params = {
        "query": query, "variables": variables or {},
        "context": {"partition_key": PK, "endpoint_id": "gpt", "part_id": "neprodai", "logger": logger, "setting": SETTING},
        "partition_key": PK, "endpoint_id": "gpt", "part_id": "neprodai",
    }
    r = eng.execute(schema, **params)
    elapsed = round((time.time() - t0) * 1000, 1)
    if isinstance(r, dict) and "body" in r:
        body = r["body"]
        result = json.loads(body) if isinstance(body, str) else body
    else:
        result = r
    status = "pass" if (result.get("errors") is None or result.get("data")) else "fail"
    # Truncate output for readability
    output_str = json.dumps(result, default=str)
    if len(output_str) > 2000:
        output_str = output_str[:2000] + "... (truncated)"
    call_log.append({
        "num": n, "scenario_id": scenario_id, "status": status, "elapsed_ms": elapsed,
        "query": query.strip()[:300], "variables": variables or {}, "output": json.loads(output_str) if not output_str.endswith("... (truncated)") else output_str[:2000] + "... (truncated)",
    })
    return result

def cc(cu, name, agents, sid):
    return gql("mutation C($cu: String!, $name: String!, $agents: [JSONCamelCase], $by: String!) { insertUpdateCoordination(coordinationUuid: $cu, coordinationName: $name, agents: $agents, updatedBy: $by) { coordination { coordinationUuid } } }", {"cu": cu, "name": name, "agents": agents, "by": "pytest"}, sid)

def cs(cu, su, sid):
    return gql("mutation S($cu: String!, $su: String!, $by: String!) { insertUpdateSession(coordinationUuid: $cu, sessionUuid: $su, updatedBy: $by) { session { sessionUuid } } }", {"cu": cu, "su": su, "by": "pytest"}, sid)

def ct(cu, tu, name, query, subtasks, actions, sid):
    return gql("mutation T($cu: String!, $tu: String!, $name: String!, $query: String!, $subtasks: [JSONCamelCase], $actions: JSONCamelCase, $by: String!) { insertUpdateTask(coordinationUuid: $cu, taskUuid: $tu, taskName: $name, initialTaskQuery: $query, subtaskQueries: $subtasks, agentActions: $actions, updatedBy: $by) { task { taskUuid subtaskQueries } } }", {"cu": cu, "tu": tu, "name": name, "query": query, "subtasks": subtasks, "actions": actions, "by": "pytest"}, sid)

def dc(cu, sid):
    return gql("mutation D($cu: String!) { deleteCoordination(coordinationUuid: $cu) { ok } }", {"cu": cu}, sid)

def ds(cu, su, sid):
    return gql("mutation D($cu: String!, $su: String!) { deleteSession(coordinationUuid: $cu, sessionUuid: $su) { ok } }", {"cu": cu, "su": su}, sid)

def dt(cu, tu, sid):
    return gql("mutation D($cu: String!, $tu: String!) { deleteTask(coordinationUuid: $cu, taskUuid: $tu) { ok } }", {"cu": cu, "tu": tu}, sid)

A1 = [{"agentUuid": "a1", "agentName": "A1", "agentType": "task"}]
A2 = [{"agentUuid": "a1", "agentName": "A1", "agentType": "task"}, {"agentUuid": "a2", "agentName": "A2", "agentType": "task"}]

# ── INT-003: Coordination CRUD ──
cu = str(uuid.uuid4())
r = gql("mutation I($cu: String!, $name: String!, $desc: String, $agents: [JSONCamelCase], $by: String!) { insertUpdateCoordination(coordinationUuid: $cu, coordinationName: $name, coordinationDescription: $desc, agents: $agents, updatedBy: $by) { coordination { coordinationUuid coordinationName agents } } }", {"cu": cu, "name": "INT-003 Test Coord", "desc": "Integration test coordination", "agents": [{"agentUuid": "agent-1", "agentName": "Task Agent", "agentType": "task"}, {"agentUuid": "agent-2", "agentName": "Triage Agent", "agentType": "triage"}], "by": "pytest"}, "INT-003")
r = gql("query Q($cu: String!) { coordination(coordinationUuid: $cu) { coordinationUuid coordinationName coordinationDescription } }", {"cu": cu}, "INT-003")
r = gql("mutation U($cu: String!, $name: String!, $by: String!) { insertUpdateCoordination(coordinationUuid: $cu, coordinationName: $name, updatedBy: $by) { coordination { coordinationName } } }", {"cu": cu, "name": "INT-003 Updated", "by": "pytest"}, "INT-003")
r = gql("query L($name: String) { coordinationList(coordinationName: $name) { total coordinationList { coordinationUuid } } }", {"name": "INT-003"}, "INT-003")
r = gql("mutation D($cu: String!) { deleteCoordination(coordinationUuid: $cu) { ok } }", {"cu": cu}, "INT-003")

# ── INT-004: Task CRUD with agent validation ──
cu4, tu4 = str(uuid.uuid4()), str(uuid.uuid4())
cc(cu4, "INT-004 Coord", [{"agentUuid": "valid-1", "agentName": "Valid Agent", "agentType": "task"}], "INT-004")
r = gql("mutation T($cu: String!, $tu: String!, $name: String!, $query: String!, $subtasks: [JSONCamelCase], $actions: JSONCamelCase, $by: String!) { insertUpdateTask(coordinationUuid: $cu, taskUuid: $tu, taskName: $name, initialTaskQuery: $query, subtaskQueries: $subtasks, agentActions: $actions, updatedBy: $by) { task { taskUuid taskName subtaskQueries } } }", {"cu": cu4, "tu": tu4, "name": "INT-004 Task", "query": "Initial query", "subtasks": [{"agentUuid": "valid-1", "subtaskQuery": "Subtask 1"}, {"agentUuid": "invalid-2", "subtaskQuery": "Should be filtered"}], "actions": {"valid-1": {"predecessors": [], "primary_path": True}}, "by": "pytest"}, "INT-004")
r = gql("query Q($cu: String!, $tu: String!) { task(coordinationUuid: $cu, taskUuid: $tu) { taskName } }", {"cu": cu4, "tu": tu4}, "INT-004")
r = dt(cu4, tu4, "INT-004")
r = dc(cu4, "INT-004")

# ── INT-005: TaskSchedule CRUD ──
cu5, tu5 = str(uuid.uuid4()), str(uuid.uuid4())
cc(cu5, "INT-005 Coord", A1, "INT-005")
gql("mutation T($cu: String!, $tu: String!, $name: String!, $query: String!, $by: String!) { insertUpdateTask(coordinationUuid: $cu, taskUuid: $tu, taskName: $name, initialTaskQuery: $query, updatedBy: $by) { task { taskUuid } } }", {"cu": cu5, "tu": tu5, "name": "INT-005 Task", "query": "q", "by": "pytest"}, "INT-005")
r = gql("mutation I($tu: String!, $cu: String!, $sched: String!, $by: String!) { insertUpdateTaskSchedule(taskUuid: $tu, coordinationUuid: $cu, schedule: $sched, updatedBy: $by) { taskSchedule { scheduleUuid status } } }", {"tu": tu5, "cu": cu5, "sched": "0 9 * * *", "by": "pytest"}, "INT-005")
su5 = r["data"]["insertUpdateTaskSchedule"]["taskSchedule"]["scheduleUuid"]
r = gql("mutation U($tu: String!, $su: String!, $status: String!, $by: String!) { insertUpdateTaskSchedule(taskUuid: $tu, scheduleUuid: $su, status: $status, updatedBy: $by) { taskSchedule { status } } }", {"tu": tu5, "su": su5, "status": "active", "by": "pytest"}, "INT-005")
r = gql("query L($tu: String) { taskScheduleList(taskUuid: $tu) { total } }", {"tu": tu5}, "INT-005")
r = gql("mutation D($tu: String!, $su: String!) { deleteTaskSchedule(taskUuid: $tu, scheduleUuid: $su) { ok } }", {"tu": tu5, "su": su5}, "INT-005")
dt(cu5, tu5, "INT-005"); dc(cu5, "INT-005")

# ── INT-006: Session CRUD ──
cu6, su6 = str(uuid.uuid4()), str(uuid.uuid4())
cc(cu6, "INT-006 Coord", A1, "INT-006")
r = gql("mutation I($cu: String!, $su: String!, $uid: String, $query: String, $by: String!) { insertUpdateSession(coordinationUuid: $cu, sessionUuid: $su, userId: $uid, taskQuery: $query, updatedBy: $by) { session { sessionUuid status } } }", {"cu": cu6, "su": su6, "uid": "user@test.com", "query": "test session", "by": "pytest"}, "INT-006")
r = gql("query Q($cu: String!, $su: String!) { session(coordinationUuid: $cu, sessionUuid: $su) { status userId } }", {"cu": cu6, "su": su6}, "INT-006")
r = gql("mutation U($cu: String!, $su: String!, $status: String!, $by: String!) { insertUpdateSession(coordinationUuid: $cu, sessionUuid: $su, status: $status, updatedBy: $by) { session { status } } }", {"cu": cu6, "su": su6, "status": "active", "by": "pytest"}, "INT-006")
r = gql("query L($cu: String) { sessionList(coordinationUuid: $cu) { total } }", {"cu": cu6}, "INT-006")
r = ds(cu6, su6, "INT-006"); dc(cu6, "INT-006")

# ── INT-007: SessionAgent CRUD ──
cu7, su7, sau7 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
cc(cu7, "INT-007 Coord", A1, "INT-007"); cs(cu7, su7, "INT-007")
r = gql("mutation I($su: String!, $sau: String!, $cu: String!, $au: String!, $action: JSONCamelCase, $by: String!) { insertUpdateSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau, coordinationUuid: $cu, agentUuid: $au, agentAction: $action, updatedBy: $by) { sessionAgent { sessionAgentUuid state } } }", {"su": su7, "sau": sau7, "cu": cu7, "au": "a1", "action": {"primary_path": True, "user_in_the_loop": None, "predecessors": [], "action_function": {}}, "by": "pytest"}, "INT-007")
r = gql("mutation U($su: String!, $sau: String!, $state: String!, $deg: Int, $by: String!) { insertUpdateSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau, state: $state, inDegree: $deg, updatedBy: $by) { sessionAgent { state inDegree } } }", {"su": su7, "sau": sau7, "state": "executing", "deg": 2, "by": "pytest"}, "INT-007")
r = gql("query L($su: String) { sessionAgentList(sessionUuid: $su) { total } }", {"su": su7}, "INT-007")
r = gql("mutation D($su: String!, $sau: String!) { deleteSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau) { ok } }", {"su": su7, "sau": sau7}, "INT-007")
ds(cu7, su7, "INT-007"); dc(cu7, "INT-007")

# ── INT-008: SessionRun CRUD ──
cu8, su8, ru8 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
cc(cu8, "INT-008 Coord", A1, "INT-008"); cs(cu8, su8, "INT-008")
r = gql("mutation I($su: String!, $ru: String!, $tu: String!, $au: String!, $cu: String!, $atu: String!, $by: String!) { insertUpdateSessionRun(sessionUuid: $su, runUuid: $ru, threadUuid: $tu, agentUuid: $au, coordinationUuid: $cu, asyncTaskUuid: $atu, updatedBy: $by) { sessionRun { runUuid agentUuid } } }", {"su": su8, "ru": ru8, "tu": str(uuid.uuid4()), "au": "a1", "cu": cu8, "atu": "async-task-008", "by": "pytest"}, "INT-008")
r = gql("query Q($su: String!, $ru: String!) { sessionRun(sessionUuid: $su, runUuid: $ru) { asyncTaskUuid } }", {"su": su8, "ru": ru8}, "INT-008")
r = gql("query L($su: String) { sessionRunList(sessionUuid: $su) { total } }", {"su": su8}, "INT-008")
r = gql("mutation D($su: String!, $ru: String!, $cu: String!) { deleteSessionRun(sessionUuid: $su, runUuid: $ru, coordinationUuid: $cu) { ok } }", {"su": su8, "ru": ru8, "cu": cu8}, "INT-008")
ds(cu8, su8, "INT-008"); dc(cu8, "INT-008")

# ── INT-010: JSONB Filter ──
cu10, su10 = str(uuid.uuid4()), str(uuid.uuid4())
sau10a, sau10b = str(uuid.uuid4()), str(uuid.uuid4())
cc(cu10, "INT-010 Coord", A2, "INT-010"); cs(cu10, su10, "INT-010")
gql("mutation SA($su: String!, $sau: String!, $cu: String!, $action: JSONCamelCase, $by: String!) { insertUpdateSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau, coordinationUuid: $cu, agentUuid: \"a1\", agentAction: $action, updatedBy: $by) { sessionAgent { sessionAgentUuid } } }", {"su": su10, "sau": sau10a, "cu": cu10, "action": {"primary_path": True, "user_in_the_loop": None, "predecessors": [], "action_function": {}}, "by": "pytest"}, "INT-010")
gql("mutation SA($su: String!, $sau: String!, $cu: String!, $action: JSONCamelCase, $by: String!) { insertUpdateSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau, coordinationUuid: $cu, agentUuid: \"a2\", agentAction: $action, updatedBy: $by) { sessionAgent { sessionAgentUuid } } }", {"su": su10, "sau": sau10b, "cu": cu10, "action": {"primary_path": False, "user_in_the_loop": None, "predecessors": [], "action_function": {}}, "by": "pytest"}, "INT-010")
r = gql("query F($su: String, $pp: Boolean) { sessionAgentList(sessionUuid: $su, primaryPath: $pp) { total sessionAgentList { agentUuid } } }", {"su": su10, "pp": True}, "INT-010")
r = gql("query S($su: String, $st: [String]) { sessionAgentList(sessionUuid: $su, states: $st) { total } }", {"su": su10, "st": ["initial"]}, "INT-010")
gql("mutation D($su: String!, $sau: String!) { deleteSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau) { ok } }", {"su": su10, "sau": sau10a}, "INT-010")
gql("mutation D($su: String!, $sau: String!) { deleteSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau) { ok } }", {"su": su10, "sau": sau10b}, "INT-010")
ds(cu10, su10, "INT-010"); dc(cu10, "INT-010")

# ── INT-009: Operation Hub (mocked) ──
cu9 = str(uuid.uuid4())
cc(cu9, "INT-009 OpHub", [{"agentUuid": "triage-1", "agentName": "Triage", "agentType": "triage"}, {"agentUuid": "task-1", "agentName": "Task", "agentType": "task"}], "INT-009")
mock_run, mock_thread, mock_async = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
with patch("ai_coordination_engine.handlers.operation_hub.operation_hub.invoke_ask_model") as mock_i:
    mock_i.return_value = {"current_run_uuid": mock_run, "thread_uuid": mock_thread, "async_task_uuid": mock_async}
    with patch("ai_coordination_engine.handlers.operation_hub.operation_hub.Invoker") as mock_inv:
        mock_inv.invoke_funct_on_aws_lambda = MagicMock(return_value=None)
        with patch("ai_coordination_engine.handlers.ai_coordination_utility.get_async_task") as mock_gat:
            mock_gat.return_value = {"status": "completed", "result": "{}", "notes": ""}
            with patch.dict(sys.modules, {"google": MagicMock(), "google.genai": MagicMock()}):
                r = gql("query Q($cu: String!, $query: String!, $uid: String) { askOperationHub(coordinationUuid: $cu, userQuery: $query, userId: $uid) { coordinationUuid sessionUuid runUuid threadUuid agentUuid asyncTaskUuid } }", {"cu": cu9, "query": "test query for triage", "uid": "test-user"}, "INT-009")
dc(cu9, "INT-009")

# ── INT-011: Procedure Hub (mocked) ──
cu11, tu11 = str(uuid.uuid4()), str(uuid.uuid4())
cc(cu11, "INT-011 ProcHub", A2, "INT-011")
ct(cu11, tu11, "INT-011 Task", "test query", [{"agentUuid": "a1", "subtaskQuery": "S1"}, {"agentUuid": "a2", "subtaskQuery": "S2"}], {"a1": {"predecessors": [], "primary_path": True}, "a2": {"predecessors": ["a1"], "primary_path": False}}, "INT-011")
with patch("ai_coordination_engine.handlers.procedure_hub.procedure_hub.Invoker") as mock_inv:
    mock_inv.invoke_funct_on_aws_lambda = MagicMock(return_value=None)
    r = gql("mutation E($cu: String!, $tu: String!, $query: String) { executeProcedureTaskSession(coordinationUuid: $cu, taskUuid: $tu, taskQuery: $query) { procedureTaskSession { coordinationUuid sessionUuid taskUuid taskQuery } } }", {"cu": cu11, "tu": tu11, "query": "test procedure"}, "INT-011")
dt(cu11, tu11, "INT-011"); dc(cu11, "INT-011")

# Write call log
out_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "test_results", "live_call_log.json")
with open(out_path, "w") as f:
    json.dump(call_log, f, indent=2, default=str)

passed = sum(1 for c in call_log if c["status"] == "pass")
failed = sum(1 for c in call_log if c["status"] == "fail")
print(f"Total calls: {len(call_log)}, Passed: {passed}, Failed: {failed}")
print(f"Call log written to: {out_path}")