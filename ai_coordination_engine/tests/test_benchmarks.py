# -*- coding: utf-8 -*-
"""Phase 5: Performance benchmarks for PostgreSQL CRUD operations."""
from __future__ import print_function

__author__ = "bibow"

import os
import time
import uuid

import pytest

# Check PG availability
_HAS_PG = bool(os.getenv("DATABASE_URL") or os.getenv("PG_HOST"))
if not _HAS_PG:
    try:
        import psycopg2
        _c = psycopg2.connect(
            host="localhost", port=5432, user="silvaengine",
            password="silvaengine", dbname="silvaengine", connect_timeout=2,
        )
        _c.close()
        _HAS_PG = True
    except Exception:
        pass


@pytest.fixture(autouse=True)
def pg_fixture():
    if not _HAS_PG:
        pytest.skip("No PostgreSQL available")
    from ai_coordination_engine.handlers.config import Config
    Config.DB_BACKEND = "postgresql"
    Config.PG_TABLE_PREFIX = ""
    if not Config.db_session:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import scoped_session, sessionmaker
        url = os.getenv("DATABASE_URL")
        if not url:
            url = "postgresql+psycopg2://silvaengine:silvaengine@localhost:5432/silvaengine"
        engine = create_engine(url, pool_recycle=7200, pool_size=10, pool_pre_ping=True)
        Config.db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        Config._db_engine = engine
    yield
    if Config.db_session:
        Config.db_session.rollback()
        Config.db_session.remove()


@pytest.mark.integration
class TestBenchmarks:
    def test_coordination_insert_benchmark(self):
        from ai_coordination_engine.models.repositories import get_repo, clear_registry
        clear_registry()
        repo = get_repo("coordination")
        info = type("I", (), {"context": {
            "partition_key": "bench_ep#bench_part",
            "endpoint_id": "bench_ep", "part_id": "bench_part", "logger": None}})()

        uuids = []
        start = time.perf_counter()
        for _ in range(50):
            cu = str(uuid.uuid4())
            repo.insert_update(info, coordination_uuid=cu,
                coordination_name=f"Bench {cu[:8]}",
                agents=[{"agent_uuid": "a1"}], updated_by="bench")
            uuids.append(cu)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 50) * 1000
        print(f"\n  Insert 50: {elapsed:.3f}s ({avg_ms:.1f}ms/insert)")

        start = time.perf_counter()
        for cu in uuids:
            repo.get(partition_key="bench_ep#bench_part", coordination_uuid=cu)
        elapsed = time.perf_counter() - start
        avg_get = (elapsed / 50) * 1000
        print(f"  Get 50: {elapsed:.3f}s ({avg_get:.1f}ms/get)")

        start = time.perf_counter()
        result = repo.list(info)
        elapsed = time.perf_counter() - start
        print(f"  List: {elapsed:.3f}s (total={result.total})")

        for cu in uuids:
            repo.delete(info, coordination_uuid=cu)

        assert avg_ms < 50, f"Insert too slow: {avg_ms:.1f}ms"
        assert avg_get < 20, f"Get too slow: {avg_get:.1f}ms"