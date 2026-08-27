# -*- coding: utf-8 -*-
"""Phase 4: Business Flow Parity tests against a live PostgreSQL database.

These tests validate CRUD, list, RLS enforcement, and JSONB filtering
against the running PostgreSQL service. They auto-skip if DATABASE_URL
or PG_HOST is not available.
"""
from __future__ import print_function

__author__ = "bibow"

import os
import sys
import uuid
from typing import Any, Dict

import pendulum
import pytest

# Auto-skip if no PostgreSQL connection available
# Check env vars OR try connecting to the default local PostgreSQL
_DATABASE_URL = os.getenv("DATABASE_URL")
_PG_HOST = os.getenv("PG_HOST")
_HAS_PG = _DATABASE_URL is not None or _PG_HOST is not None

# If no env vars, try default local connection (Docker silvaengine-postgres)
if not _HAS_PG:
    try:
        import psycopg2
        _conn = psycopg2.connect("postgresql://silvaengine:silvaengine@localhost:5432/silvaengine", connect_timeout=2)
        _conn.close()
        _HAS_PG = True
    except Exception:
        pass
pg_skip = pytest.mark.skipif(not _HAS_PG, reason="No PostgreSQL connection available")


def _setup_pg_config():
    """Initialize Config for PostgreSQL backend."""
    from ai_coordination_engine.handlers.config import Config
    Config.DB_BACKEND = "postgresql"
    Config.PG_TABLE_PREFIX = ""
    if not Config.db_session:
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine
        from sqlalchemy.orm import scoped_session, sessionmaker

        # Try DATABASE_URL first, then build from PG_* env vars, then use known local defaults
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            pg_host = os.getenv("PG_HOST", "localhost")
            pg_port = os.getenv("PG_PORT", "5432")
            pg_user = os.getenv("PG_USER", "silvaengine")
            pg_password = os.getenv("PG_PASSWORD", "silvaengine")
            pg_db = os.getenv("PG_DB", "silvaengine")
            database_url = f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

        engine = create_engine(database_url, pool_recycle=7200, pool_size=10, pool_pre_ping=True, echo=False)
        Config.db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        Config._db_engine = engine


def _cleanup_pg_session():
    """Clean up the PG session after each test."""
    from ai_coordination_engine.handlers.config import Config
    if Config.db_session:
        Config.db_session.rollback()
        Config.db_session.remove()


@pytest.fixture(autouse=True)
def pg_fixture():
    if not _HAS_PG:
        pytest.skip("No PostgreSQL available")
    _setup_pg_config()
    yield
    _cleanup_pg_session()


@pytest.mark.integration
class TestCoordinationPGCRUD:
    """Test Coordination CRUD against PostgreSQL."""

    def test_insert_and_get(self):
        from ai_coordination_engine.models.repositories import get_repo, clear_registry
        clear_registry()

        repo = get_repo("coordination")
        cu = str(uuid.uuid4())
        pk = "test_endpoint#test_part"

        # Insert
        info = type("Info", (), {"context": {"partition_key": pk, "endpoint_id": "test_endpoint", "part_id": "test_part", "logger": None}})()
        result = repo.insert_update(info, coordination_uuid=cu, coordination_name="Test Coord", coordination_description="Test desc", agents=[{"agent_uuid": "agent-1", "agent_name": "Agent 1"}], updated_by="test")
        assert result is not None
        assert result.coordination_name == "Test Coord"
        assert str(result.coordination_uuid) == cu

        # Get
        fetched = repo.get(partition_key=pk, coordination_uuid=cu)
        assert fetched is not None
        assert fetched["coordination_name"] == "Test Coord"
        assert len(fetched["agents"]) == 1

        # Update
        result2 = repo.insert_update(info, coordination_uuid=cu, coordination_name="Updated Coord", updated_by="test")
        assert result2.coordination_name == "Updated Coord"

        # Delete
        deleted = repo.delete(info, coordination_uuid=cu)
        assert deleted is True

        # Verify deleted
        assert repo.get(partition_key=pk, coordination_uuid=cu) is None


@pytest.mark.integration
class TestSessionPGCRUD:
    """Test Session CRUD against PostgreSQL."""

    def test_insert_and_get(self):
        from ai_coordination_engine.models.repositories import get_repo, clear_registry
        clear_registry()

        repo = get_repo("session")
        su = str(uuid.uuid4())
        cu = str(uuid.uuid4())
        pk = "test_endpoint#test_part"

        info = type("Info", (), {"context": {"partition_key": pk, "endpoint_id": "test_endpoint", "part_id": "test_part", "logger": None}})()

        # Insert
        result = repo.insert_update(info, coordination_uuid=cu, session_uuid=su, updated_by="test", status="active")
        assert result is not None
        assert result.status == "active"

        # Get
        fetched = repo.get(coordination_uuid=cu, session_uuid=su)
        assert fetched is not None
        assert fetched["status"] == "active"
        assert fetched["partition_key"] == pk

        # List
        list_result = repo.list(info, coordination_uuid=cu)
        assert list_result.total >= 1

        # Delete
        assert repo.delete(info, coordination_uuid=cu, session_uuid=su) is True
        assert repo.get(coordination_uuid=cu, session_uuid=su) is None


@pytest.mark.integration
class TestSessionAgentPGJSONBFilter:
    """Test SessionAgent with JSONB agent_action filtering."""

    def test_jsonb_filter_primary_path(self):
        from ai_coordination_engine.models.repositories import get_repo, clear_registry
        clear_registry()

        repo = get_repo("session_agent")
        sau = str(uuid.uuid4())
        su = str(uuid.uuid4())
        cu = str(uuid.uuid4())
        pk = "test_endpoint#test_part"

        info = type("Info", (), {"context": {"partition_key": pk, "endpoint_id": "test_endpoint", "part_id": "test_part", "logger": None}})()

        # Insert with agent_action containing primary_path
        repo.insert_update(info, session_uuid=su, session_agent_uuid=sau,
            coordination_uuid=cu, agent_uuid="agent-1",
            agent_action={"primary_path": True, "user_in_the_loop": None, "predecessors": [], "action_function": {}},
            updated_by="test")

        # List filtering by primary_path
        list_result = repo.list(info, session_uuid=su, primary_path=True)
        assert list_result.total >= 1

        # Cleanup
        repo.delete(info, session_uuid=su, session_agent_uuid=sau)


@pytest.mark.integration
class TestRLSEnforcement:
    """Test Row-Level Security tenant isolation.

    Note: RLS is bypassed for superusers. We create a non-superuser role
    'aace_app' and test with that role's session.
    """

    def test_rls_blocks_cross_tenant_access(self):
        """A non-superuser session with tenant A's partition_key cannot read tenant B's rows."""
        from ai_coordination_engine.handlers.config import Config
        from ai_coordination_engine.models.repositories import get_repo, clear_registry
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import scoped_session, sessionmaker
        clear_registry()

        # Create a non-superuser role for RLS testing
        admin_engine = Config._db_engine
        with admin_engine.connect() as conn:
            conn.execute(text("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='aace_app') THEN CREATE ROLE aace_app LOGIN PASSWORD 'aace_app' NOSUPERUSER; END IF; END $$"))
            conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ace_coordinations TO aace_app"))
            conn.commit()

        # Use a separate engine/session for the non-superuser role
        pg_url = "postgresql+psycopg2://aace_app:aace_app@localhost:5432/silvaengine"
        app_engine = create_engine(pg_url, pool_recycle=7200, pool_size=5, pool_pre_ping=True, echo=False)
        app_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=app_engine))

        repo = get_repo("coordination")
        cu_a = str(uuid.uuid4())
        cu_b = str(uuid.uuid4())
        pk_a = "endpoint_a#part_a"
        pk_b = "endpoint_b#part_b"

        # Insert as admin (superuser bypasses RLS)
        info_a = type("Info", (), {"context": {"partition_key": pk_a, "endpoint_id": "endpoint_a", "part_id": "part_a", "logger": None}})()
        info_b = type("Info", (), {"context": {"partition_key": pk_b, "endpoint_id": "endpoint_b", "part_id": "part_b", "logger": None}})()
        repo.insert_update(info_a, coordination_uuid=cu_a, coordination_name="Tenant A Coord", updated_by="test")
        repo.insert_update(info_b, coordination_uuid=cu_b, coordination_name="Tenant B Coord", updated_by="test")

        # Switch to the non-superuser session and set RLS context to tenant A
        original_session = Config.db_session
        Config.db_session = app_session
        app_session.execute(text("SET LOCAL app.tenant_id = :tenant"), {"tenant": pk_a})

        # Tenant A (non-superuser) can read its own coordination
        own = repo.get(partition_key=pk_a, coordination_uuid=cu_a)
        assert own is not None
        assert own["coordination_name"] == "Tenant A Coord"

        # Tenant A (non-superuser) CANNOT read tenant B's coordination (RLS blocks it)
        other = repo.get(partition_key=pk_b, coordination_uuid=cu_b)
        assert other is None, "RLS failed — non-superuser tenant A was able to read tenant B's data!"

        # Cleanup: restore admin session and delete test data
        app_session.remove()
        Config.db_session = original_session
        repo.delete(info_a, coordination_uuid=cu_a)
        repo.delete(info_b, coordination_uuid=cu_b)


@pytest.mark.integration
class TestBothBackendsDispatch:
    """Verify both backends register identical entity sets."""

    def test_identical_entity_sets(self):
        from ai_coordination_engine.handlers.config import Config
        from ai_coordination_engine.models.repositories import get_repo, clear_registry
        from ai_coordination_engine.models.repositories.dispatch import _repo_registry

        expected = {"coordination", "session", "session_agent", "session_run", "task", "task_schedule"}

        # DynamoDB
        Config.DB_BACKEND = "dynamodb"
        clear_registry()
        for entity in expected:
            get_repo(entity)
        ddb_set = set(_repo_registry["dynamodb"].keys())

        # PostgreSQL
        Config.DB_BACKEND = "postgresql"
        clear_registry()
        for entity in expected:
            get_repo(entity)
        pg_set = set(_repo_registry["postgresql"].keys())

        assert ddb_set == expected
        assert pg_set == expected