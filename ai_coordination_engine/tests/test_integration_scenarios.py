# -*- coding: utf-8 -*-
"""Integration test scenarios for AI Coordination Engine — INTEGRATION_SCENARIOS_SOP.md

Covers INT-003 through INT-012 against PostgreSQL with internal invoke.
Mocks AACE loopback for workflow tests (INT-009, INT-011).
"""
from __future__ import print_function

__author__ = "bibow"

import os, sys, uuid, logging
from typing import Any, Dict
from unittest.mock import patch, MagicMock

import pytest
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("test_integration")

SETTING = {
    "region_name": os.getenv("region_name"),
    "aws_access_key_id": os.getenv("aws_access_key_id"),
    "aws_secret_access_key": os.getenv("aws_secret_access_key"),
    "endpoint_id": os.getenv("endpoint_id", "gpt"),
    "part_id": os.getenv("part_id", "neprodai"),
    "execute_mode": os.getenv("execute_mode", "local_for_all"),
    "initialize_tables": int(os.getenv("initialize_tables", "0")),
    "cache_enabled": int(os.getenv("cache_enabled", "0")),
    "db_backend": os.getenv("db_backend", "postgresql"),
    "database_url": os.getenv("DATABASE_URL"),
    "db_host": os.getenv("PG_HOST", "localhost"),
    "db_port": os.getenv("PG_PORT", "5432"),
    "db_user": os.getenv("PG_USER", "silvaengine"),
    "db_password": os.getenv("PG_PASSWORD", "silvaengine"),
    "db_schema": os.getenv("PG_DB", "silvaengine"),
    "pg_table_prefix": os.getenv("ACE_PG_TABLE_PREFIX", ""),
    "functs_on_local": {
        "ai_coordination_graphql": {"module_name": "ai_coordination_engine", "class_name": "AICoordinationEngine"},
        "async_insert_update_session": {"module_name": "ai_coordination_engine", "class_name": "AICoordinationEngine"},
        "async_execute_procedure_task_session": {"module_name": "ai_coordination_engine", "class_name": "AICoordinationEngine"},
        "async_update_session_agent": {"module_name": "ai_coordination_engine", "class_name": "AICoordinationEngine"},
        "async_orchestrate_task_query": {"module_name": "ai_coordination_engine", "class_name": "AICoordinationEngine"},
        "ai_agent_core_graphql": {"module_name": "ai_agent_core_engine", "class_name": "AIAgentCoreEngine"},
        "async_execute_ask_model": {"module_name": "ai_agent_core_engine", "class_name": "AIAgentCoreEngine"},
        "async_insert_update_tool_call": {"module_name": "ai_agent_core_engine", "class_name": "AIAgentCoreEngine"},
        "send_data_to_websocket": {"module_name": "ai_agent_core_engine", "class_name": "AIAgentCoreEngine"},
    },
}
PK = f"{SETTING['endpoint_id']}#{SETTING['part_id']}"

@pytest.fixture(scope="module")
def engine():
    from ai_coordination_engine import AICoordinationEngine
    return AICoordinationEngine(logger, **SETTING)

def _gql(engine, query, variables=None):
    from ai_coordination_engine import AICoordinationEngine
    import json
    schema = AICoordinationEngine.build_graphql_schema()
    params = {"query": query, "variables": variables or {},
        "context": {"partition_key": PK, "endpoint_id": SETTING["endpoint_id"], "part_id": SETTING["part_id"], "logger": logger, "setting": SETTING},
        "partition_key": PK, "endpoint_id": SETTING["endpoint_id"], "part_id": SETTING["part_id"]}
    result = engine.execute(schema, **params)
    if isinstance(result, dict) and "body" in result:
        body = result["body"]
        if isinstance(body, str):
            return json.loads(body)
        return body
    return result

def _cc(engine, cu, name="Test", agents=None):
    return _gql(engine, """mutation C($cu: String!, $name: String!, $agents: [JSONCamelCase], $by: String!) {
        insertUpdateCoordination(coordinationUuid: $cu, coordinationName: $name, agents: $agents, updatedBy: $by) { coordination { coordinationUuid } } }""",
        {"cu": cu, "name": name, "agents": agents or [{"agentUuid": "a1", "agentName": "A1", "agentType": "task"}], "by": "test"})

def _cs(engine, cu, su):
    return _gql(engine, """mutation S($cu: String!, $su: String!, $by: String!) {
        insertUpdateSession(coordinationUuid: $cu, sessionUuid: $su, updatedBy: $by) { session { sessionUuid } } }""", {"cu": cu, "su": su, "by": "test"})

def _ct(engine, cu, tu, name="Task", query="q", subtasks=None, actions=None):
    return _gql(engine, """mutation T($cu: String!, $tu: String!, $name: String!, $query: String!, $subtasks: [JSONCamelCase], $actions: JSONCamelCase, $by: String!) {
        insertUpdateTask(coordinationUuid: $cu, taskUuid: $tu, taskName: $name, initialTaskQuery: $query, subtaskQueries: $subtasks, agentActions: $actions, updatedBy: $by) { task { taskUuid subtaskQueries } } }""",
        {"cu": cu, "tu": tu, "name": name, "query": query, "subtasks": subtasks, "actions": actions, "by": "test"})

def _dc(engine, cu):
    return _gql(engine, """mutation D($cu: String!) { deleteCoordination(coordinationUuid: $cu) { ok } }""", {"cu": cu})

def _ds(engine, cu, su):
    return _gql(engine, """mutation D($cu: String!, $su: String!) { deleteSession(coordinationUuid: $cu, sessionUuid: $su) { ok } }""", {"cu": cu, "su": su})

def _dt(engine, cu, tu):
    return _gql(engine, """mutation D($cu: String!, $tu: String!) { deleteTask(coordinationUuid: $cu, taskUuid: $tu) { ok } }""", {"cu": cu, "tu": tu})

def _dsr(engine, cu, su, ru):
    return _gql(engine, """mutation D($su: String!, $ru: String!, $cu: String!) { deleteSessionRun(sessionUuid: $su, runUuid: $ru, coordinationUuid: $cu) { ok } }""", {"su": su, "ru": ru, "cu": cu})

def _dsa(engine, su, sau):
    return _gql(engine, """mutation D($su: String!, $sau: String!) { deleteSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau) { ok } }""", {"su": su, "sau": sau})

# ── INT-003: Coordination CRUD ──────────────────────────────────────────────
@pytest.mark.integration
class TestINT003:
    def test_coordination_crud(self, engine):
        cu = str(uuid.uuid4())
        r = _gql(engine, """mutation I($cu: String!, $name: String!, $desc: String, $agents: [JSONCamelCase], $by: String!) {
            insertUpdateCoordination(coordinationUuid: $cu, coordinationName: $name, coordinationDescription: $desc, agents: $agents, updatedBy: $by) {
                coordination { coordinationUuid coordinationName agents } } }""",
            {"cu": cu, "name": "Test Coord", "desc": "desc", "agents": [{"agentUuid": "a1", "agentName": "A1", "agentType": "task"}, {"agentUuid": "a2", "agentName": "A2", "agentType": "triage"}], "by": "test"})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        c = r["data"]["insertUpdateCoordination"]["coordination"]
        assert c["coordinationName"] == "Test Coord" and len(c["agents"]) == 2
        r = _gql(engine, """query Q($cu: String!) { coordination(coordinationUuid: $cu) { coordinationName } }""", {"cu": cu})
        assert r["data"]["coordination"]["coordinationName"] == "Test Coord"
        r = _gql(engine, """mutation U($cu: String!, $name: String!, $by: String!) { insertUpdateCoordination(coordinationUuid: $cu, coordinationName: $name, updatedBy: $by) { coordination { coordinationName } } }""", {"cu": cu, "name": "Updated", "by": "test"})
        assert r["data"]["insertUpdateCoordination"]["coordination"]["coordinationName"] == "Updated"
        r = _gql(engine, """query L($name: String) { coordinationList(coordinationName: $name) { total } }""", {"name": "Updated"})
        assert r["data"]["coordinationList"]["total"] >= 1
        r = _gql(engine, """mutation D($cu: String!) { deleteCoordination(coordinationUuid: $cu) { ok } }""", {"cu": cu})
        assert r["data"]["deleteCoordination"]["ok"] is True

# ── INT-004: Task CRUD with agent validation ────────────────────────────────
@pytest.mark.integration
class TestINT004:
    def test_task_crud_with_validation(self, engine):
        cu = str(uuid.uuid4()); tu = str(uuid.uuid4())
        _cc(engine, cu, "Task Test", [{"agentUuid": "valid-1", "agentName": "V1", "agentType": "task"}])
        r = _ct(engine, cu, tu, "Task", "q", [{"agentUuid": "valid-1", "subtaskQuery": "S1"}, {"agentUuid": "invalid-2", "subtaskQuery": "S2"}], {"valid-1": {"predecessors": [], "primary_path": True}})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        task = r["data"]["insertUpdateTask"]["task"]
        sq_str = str(task.get("subtaskQueries", []))
        assert "valid-1" in sq_str
        assert "invalid-2" not in sq_str
        r = _gql(engine, """query Q($cu: String!, $tu: String!) { task(coordinationUuid: $cu, taskUuid: $tu) { taskName } }""", {"cu": cu, "tu": tu})
        assert r["data"]["task"]["taskName"] == "Task"
        r = _dt(engine, cu, tu); assert r["data"]["deleteTask"]["ok"] is True
        _dc(engine, cu)

# ── INT-005: TaskSchedule CRUD ──────────────────────────────────────────────
@pytest.mark.integration
class TestINT005:
    def test_task_schedule_crud(self, engine):
        cu = str(uuid.uuid4()); tu = str(uuid.uuid4())
        _cc(engine, cu, "Sched Test"); _ct(engine, cu, tu, "Sched Task")
        r = _gql(engine, """mutation I($tu: String!, $cu: String!, $sched: String!, $by: String!) {
            insertUpdateTaskSchedule(taskUuid: $tu, coordinationUuid: $cu, schedule: $sched, updatedBy: $by) { taskSchedule { scheduleUuid status } } }""",
            {"tu": tu, "cu": cu, "sched": "0 9 * * *", "by": "test"})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        assert r["data"]["insertUpdateTaskSchedule"]["taskSchedule"]["status"] == "initial"
        su = r["data"]["insertUpdateTaskSchedule"]["taskSchedule"]["scheduleUuid"]
        r = _gql(engine, """mutation U($tu: String!, $su: String!, $status: String!, $by: String!) { insertUpdateTaskSchedule(taskUuid: $tu, scheduleUuid: $su, status: $status, updatedBy: $by) { taskSchedule { status } } }""", {"tu": tu, "su": su, "status": "active", "by": "test"})
        assert r["data"]["insertUpdateTaskSchedule"]["taskSchedule"]["status"] == "active"
        r = _gql(engine, """query L($tu: String) { taskScheduleList(taskUuid: $tu) { total } }""", {"tu": tu})
        assert r["data"]["taskScheduleList"]["total"] >= 1
        r = _gql(engine, """mutation D($tu: String!, $su: String!) { deleteTaskSchedule(taskUuid: $tu, scheduleUuid: $su) { ok } }""", {"tu": tu, "su": su})
        assert r["data"]["deleteTaskSchedule"]["ok"] is True
        _dt(engine, cu, tu); _dc(engine, cu)

# ── INT-006: Session CRUD ────────────────────────────────────────────────────
@pytest.mark.integration
class TestINT006:
    def test_session_crud(self, engine):
        cu = str(uuid.uuid4()); su = str(uuid.uuid4())
        _cc(engine, cu, "Session Test")
        r = _gql(engine, """mutation I($cu: String!, $su: String!, $uid: String, $query: String, $by: String!) {
            insertUpdateSession(coordinationUuid: $cu, sessionUuid: $su, userId: $uid, taskQuery: $query, updatedBy: $by) { session { sessionUuid status } } }""",
            {"cu": cu, "su": su, "uid": "user@test.com", "query": "test", "by": "test"})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        assert r["data"]["insertUpdateSession"]["session"]["status"] == "initial"
        r = _gql(engine, """query Q($cu: String!, $su: String!) { session(coordinationUuid: $cu, sessionUuid: $su) { status userId } }""", {"cu": cu, "su": su})
        assert r["data"]["session"]["userId"] == "user@test.com"
        r = _gql(engine, """mutation U($cu: String!, $su: String!, $status: String!, $by: String!) { insertUpdateSession(coordinationUuid: $cu, sessionUuid: $su, status: $status, updatedBy: $by) { session { status } } }""", {"cu": cu, "su": su, "status": "active", "by": "test"})
        assert r["data"]["insertUpdateSession"]["session"]["status"] == "active"
        r = _gql(engine, """query L($cu: String) { sessionList(coordinationUuid: $cu) { total } }""", {"cu": cu})
        assert r["data"]["sessionList"]["total"] >= 1
        r = _ds(engine, cu, su); assert r["data"]["deleteSession"]["ok"] is True
        _dc(engine, cu)

# ── INT-007: SessionAgent CRUD ──────────────────────────────────────────────
@pytest.mark.integration
class TestINT007:
    def test_session_agent_crud(self, engine):
        cu = str(uuid.uuid4()); su = str(uuid.uuid4()); sau = str(uuid.uuid4())
        _cc(engine, cu, "SA Test"); _cs(engine, cu, su)
        r = _gql(engine, """mutation I($su: String!, $sau: String!, $cu: String!, $au: String!, $action: JSONCamelCase, $by: String!) {
            insertUpdateSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau, coordinationUuid: $cu, agentUuid: $au, agentAction: $action, updatedBy: $by) { sessionAgent { sessionAgentUuid state } } }""",
            {"su": su, "sau": sau, "cu": cu, "au": "a1", "action": {"primary_path": True, "user_in_the_loop": None, "predecessors": [], "action_function": {}}, "by": "test"})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        assert r["data"]["insertUpdateSessionAgent"]["sessionAgent"]["state"] == "initial"
        r = _gql(engine, """mutation U($su: String!, $sau: String!, $state: String!, $deg: Int, $by: String!) {
            insertUpdateSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau, state: $state, inDegree: $deg, updatedBy: $by) { sessionAgent { state inDegree } } }""", {"su": su, "sau": sau, "state": "executing", "deg": 2, "by": "test"})
        assert r["data"]["insertUpdateSessionAgent"]["sessionAgent"]["state"] == "executing"
        r = _gql(engine, """query L($su: String) { sessionAgentList(sessionUuid: $su) { total } }""", {"su": su})
        assert r["data"]["sessionAgentList"]["total"] >= 1
        r = _dsa(engine, su, sau)
        assert r["data"]["deleteSessionAgent"]["ok"] is True
        _ds(engine, cu, su); _dc(engine, cu)

# ── INT-008: SessionRun CRUD ────────────────────────────────────────────────
@pytest.mark.integration
class TestINT008:
    def test_session_run_crud(self, engine):
        cu = str(uuid.uuid4()); su = str(uuid.uuid4()); ru = str(uuid.uuid4())
        _cc(engine, cu, "SR Test"); _cs(engine, cu, su)
        r = _gql(engine, """mutation I($su: String!, $ru: String!, $tu: String!, $au: String!, $cu: String!, $atu: String!, $by: String!) {
            insertUpdateSessionRun(sessionUuid: $su, runUuid: $ru, threadUuid: $tu, agentUuid: $au, coordinationUuid: $cu, asyncTaskUuid: $atu, updatedBy: $by) { sessionRun { runUuid agentUuid } } }""",
            {"su": su, "ru": ru, "tu": str(uuid.uuid4()), "au": "a1", "cu": cu, "atu": "async-123", "by": "test"})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        assert r["data"]["insertUpdateSessionRun"]["sessionRun"]["agentUuid"] == "a1"
        r = _gql(engine, """query Q($su: String!, $ru: String!) { sessionRun(sessionUuid: $su, runUuid: $ru) { asyncTaskUuid } }""", {"su": su, "ru": ru})
        assert r["data"]["sessionRun"]["asyncTaskUuid"] == "async-123"
        r = _gql(engine, """query L($su: String) { sessionRunList(sessionUuid: $su) { total } }""", {"su": su})
        assert r["data"]["sessionRunList"]["total"] >= 1
        r = _dsr(engine, cu, su, ru)
        assert r["data"]["deleteSessionRun"]["ok"] is True
        _ds(engine, cu, su); _dc(engine, cu)

# ── INT-010: JSONB filter ───────────────────────────────────────────────────
@pytest.mark.integration
class TestINT010:
    def test_jsonb_filter_primary_path(self, engine):
        cu = str(uuid.uuid4()); su = str(uuid.uuid4())
        sau1 = str(uuid.uuid4()); sau2 = str(uuid.uuid4())
        _cc(engine, cu, "Filter", [{"agentUuid": "a1", "agentName": "A1", "agentType": "task"}, {"agentUuid": "a2", "agentName": "A2", "agentType": "task"}])
        _cs(engine, cu, su)
        _gql(engine, """mutation SA($su: String!, $sau: String!, $cu: String!, $action: JSONCamelCase, $by: String!) {
            insertUpdateSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau, coordinationUuid: $cu, agentUuid: "a1", agentAction: $action, updatedBy: $by) { sessionAgent { sessionAgentUuid } } }""",
            {"su": su, "sau": sau1, "cu": cu, "action": {"primary_path": True, "user_in_the_loop": None, "predecessors": [], "action_function": {}}, "by": "test"})
        _gql(engine, """mutation SA($su: String!, $sau: String!, $cu: String!, $action: JSONCamelCase, $by: String!) {
            insertUpdateSessionAgent(sessionUuid: $su, sessionAgentUuid: $sau, coordinationUuid: $cu, agentUuid: "a2", agentAction: $action, updatedBy: $by) { sessionAgent { sessionAgentUuid } } }""",
            {"su": su, "sau": sau2, "cu": cu, "action": {"primary_path": False, "user_in_the_loop": None, "predecessors": [], "action_function": {}}, "by": "test"})
        r = _gql(engine, """query F($su: String, $pp: Boolean) { sessionAgentList(sessionUuid: $su, primaryPath: $pp) { total sessionAgentList { agentUuid } } }""", {"su": su, "pp": True})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        agents = r["data"]["sessionAgentList"]["sessionAgentList"]
        assert all(a["agentUuid"] == "a1" for a in agents), f"Expected only a1, got {[a['agentUuid'] for a in agents]}"
        r = _gql(engine, """query S($su: String, $st: [String]) { sessionAgentList(sessionUuid: $su, states: $st) { total } }""", {"su": su, "st": ["initial"]})
        assert r["data"]["sessionAgentList"]["total"] >= 2
        _dsa(engine, su, sau1); _dsa(engine, su, sau2)
        _ds(engine, cu, su); _dc(engine, cu)

# ── INT-009: Operation Hub (mocked) ─────────────────────────────────────────
@pytest.mark.integration
class TestINT009:
    def test_ask_operation_hub_mocked(self, engine):
        cu = str(uuid.uuid4())
        _cc(engine, cu, "OpHub", [{"agentUuid": "triage-1", "agentName": "Triage", "agentType": "triage"}, {"agentUuid": "task-1", "agentName": "Task", "agentType": "task"}])
        mock_run = str(uuid.uuid4()); mock_thread = str(uuid.uuid4()); mock_async = str(uuid.uuid4())
        with patch("ai_coordination_engine.handlers.operation_hub.operation_hub.invoke_ask_model") as mock_i:
            mock_i.return_value = {"current_run_uuid": mock_run, "thread_uuid": mock_thread, "async_task_uuid": mock_async}
            with patch("ai_coordination_engine.handlers.operation_hub.operation_hub.Invoker") as mock_inv:
                mock_inv.invoke_funct_on_aws_lambda = MagicMock(return_value=None)
                with patch("ai_coordination_engine.handlers.ai_coordination_utility.get_async_task") as mock_gat:
                    mock_gat.return_value = {"status": "completed", "result": "{}", "notes": ""}
                    with patch.dict(sys.modules, {"google": MagicMock(), "google.genai": MagicMock()}):
                        r = _gql(engine, """query Q($cu: String!, $query: String!, $uid: String) {
                            askOperationHub(coordinationUuid: $cu, userQuery: $query, userId: $uid) { coordinationUuid sessionUuid runUuid threadUuid agentUuid asyncTaskUuid } }""",
                            {"cu": cu, "query": "test query", "uid": "test-user"})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        hub = r["data"]["askOperationHub"]
        assert hub["coordinationUuid"] == cu and hub["runUuid"] == mock_run
        _dc(engine, cu)

# ── INT-011: Procedure Hub (mocked) ─────────────────────────────────────────
@pytest.mark.integration
class TestINT011:
    def test_procedure_hub_mocked(self, engine):
        cu = str(uuid.uuid4()); tu = str(uuid.uuid4())
        _cc(engine, cu, "ProcHub", [{"agentUuid": "a1", "agentName": "A1", "agentType": "task"}, {"agentUuid": "a2", "agentName": "A2", "agentType": "task"}])
        _ct(engine, cu, tu, "Proc Task", "test query", [{"agentUuid": "a1", "subtaskQuery": "S1"}, {"agentUuid": "a2", "subtaskQuery": "S2"}], {"a1": {"predecessors": [], "primary_path": True}, "a2": {"predecessors": ["a1"], "primary_path": False}})
        with patch("ai_coordination_engine.handlers.procedure_hub.procedure_hub.Invoker") as mock_inv:
            mock_inv.invoke_funct_on_aws_lambda = MagicMock(return_value=None)
            r = _gql(engine, """mutation E($cu: String!, $tu: String!, $query: String) {
                executeProcedureTaskSession(coordinationUuid: $cu, taskUuid: $tu, taskQuery: $query) { procedureTaskSession { coordinationUuid sessionUuid taskUuid taskQuery } } }""",
                {"cu": cu, "tu": tu, "query": "test procedure"})
        assert r.get("errors") is None, f"Errors: {r.get('errors')}"
        proc = r["data"]["executeProcedureTaskSession"]["procedureTaskSession"]
        assert proc["coordinationUuid"] == cu and proc["taskUuid"] == tu and proc["sessionUuid"] is not None
        _dt(engine, cu, tu); _dc(engine, cu)