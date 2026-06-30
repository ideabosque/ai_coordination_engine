#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate ai_coordination_engine data from DynamoDB (ideabosque prod) to PostgreSQL.

Migrates all 6 ACE tables in dependency order:
  1. ace-coordinations  -> ace_coordinations
  2. ace-tasks          -> ace_tasks
  3. ace-task_schedules -> ace_task_schedules
  4. ace-sessions       -> ace_sessions
  5. ace-session_agents -> ace_session_agents
  6. ace-session_runs   -> ace_session_runs

Usage:
  python ai_coordination_engine/tests/migrate_dynamodb_to_postgresql.py

Reads AWS credentials from tests/.env (ideabosque prod profile).
Writes to local PostgreSQL via DATABASE_URL from .env.
"""
from __future__ import print_function

__author__ = "bibow"

import os
import sys
import json
import time
import uuid
import logging
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("migrate_ace")

# ── DynamoDB source ──
import boto3

ddb = boto3.client(
    "dynamodb",
    region_name=os.getenv("region_name"),
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key"),
)

# ── PostgreSQL destination ──
import psycopg2
from psycopg2.extras import execute_values

PG_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "dbname": os.getenv("PG_DB", "silvaengine"),
    "user": os.getenv("PG_USER", "silvaengine"),
    "password": os.getenv("PG_PASSWORD", "silvaengine"),
}
# DATABASE_URL takes precedence
db_url = os.getenv("DATABASE_URL")
if db_url:
    # Parse DATABASE_URL to extract password (which may be masked by platform)
    import re
    m = re.match(r"postgresql\+psycopg2://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
    if m:
        PG_CONFIG = {
            "host": m.group(3), "port": int(m.group(4)),
            "dbname": m.group(5), "user": m.group(1), "password": m.group(2),
        }

conn = psycopg2.connect(**PG_CONFIG)
conn.autocommit = False
cur = conn.cursor()

# ── Helpers ──

def ddb_value(v: Any) -> Any:
    """Extract scalar value from DynamoDB typed dict."""
    if v is None:
        return None
    if "S" in v:
        return v["S"]
    if "N" in v:
        return int(v["N"]) if "." not in v["N"] else float(v["N"])
    if "NULL" in v:
        return None
    if "L" in v:
        return [ddb_value(item) for item in v["L"]]
    if "M" in v:
        return {k: ddb_value(val) for k, val in v["M"].items()}
    if "BOOL" in v:
        return v["BOOL"]
    return None


def ddb_to_dict(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a DynamoDB item to a plain dict."""
    return {k: ddb_value(v) for k, v in item.items()}


def to_uuid(val: Any) -> Optional[str]:
    """Convert a string to UUID format for PG insertion. Returns string representation."""
    if val is None:
        return None
    if isinstance(val, str):
        # DynamoDB uses numeric strings like "09047568911300349976" — not valid UUIDs.
        # Store as-is (PG UUID column will reject it, so we use text cast).
        # Actually, PG columns are UUID type. We need to handle non-UUID strings.
        # Option: cast to UUID if it looks like one, otherwise generate a deterministic UUID.
        try:
            # Try parsing as UUID
            u = uuid.UUID(val)
            return str(u)
        except (ValueError, AttributeError):
            # Not a valid UUID — generate a deterministic one from the string
            return str(uuid.uuid5(uuid.NAMESPACE_OID, val))
    return val


def to_jsonb(val: Any) -> Optional[str]:
    """Convert a value to JSON string for JSONB insertion."""
    if val is None:
        return None
    return json.dumps(val, default=str)


def to_timestamp(val: Any) -> Optional[str]:
    """Convert DynamoDB datetime string to PostgreSQL timestamp format."""
    if val is None:
        return None
    if isinstance(val, str):
        # DynamoDB stores like "2026-03-24T01:01:15.259487+0000"
        # PG expects "2026-03-24T01:01:15.259487+00:00"
        # Replace +0000 with +00:00
        if "+0000" in val:
            val = val.replace("+0000", "+00:00")
        elif "+00:00" not in val and len(val) > 6 and val[-5] == "+":
            # Handle +XXXX format
            val = val[:-5] + "+00:00"
        return val
    return val


def scan_all(table_name: str, filter_expr: str = None) -> List[Dict[str, Any]]:
    """Scan all items from a DynamoDB table."""
    items = []
    kwargs = {"TableName": table_name}
    if filter_expr:
        kwargs["FilterExpression"] = filter_expr
    while True:
        resp = ddb.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
        logger.info(f"  {table_name}: scanned {len(items)} so far...")
    return [ddb_to_dict(item) for item in items]


# ── Migration functions ──

def migrate_coordinations():
    """Migrate ace-coordinations -> ace_coordinations."""
    logger.info("Migrating ace-coordinations...")
    items = scan_all("ace-coordinations")
    logger.info(f"  Found {len(items)} coordinations")

    rows = []
    for item in items:
        rows.append((
            item.get("partition_key"),
            to_uuid(item.get("coordination_uuid")),
            item.get("endpoint_id"),
            item.get("part_id"),
            item.get("coordination_name"),
            item.get("coordination_description"),
            to_jsonb(item.get("agents", [])),
            item.get("updated_by"),
            to_timestamp(item.get("created_at")),
            to_timestamp(item.get("updated_at")),
        ))

    if rows:
        execute_values(cur, """
            INSERT INTO ace_coordinations
                (partition_key, coordination_uuid, endpoint_id, part_id,
                 coordination_name, coordination_description, agents,
                 updated_by, created_at, updated_at)
            VALUES %s
            ON CONFLICT (partition_key, coordination_uuid) DO NOTHING
        """, rows)
    conn.commit()
    logger.info(f"  Inserted {len(rows)} coordinations")
    return len(rows)


def migrate_tasks():
    """Migrate ace-tasks -> ace_tasks."""
    logger.info("Migrating ace-tasks...")
    items = scan_all("ace-tasks")
    logger.info(f"  Found {len(items)} tasks")

    rows = []
    for item in items:
        pk = item.get("partition_key")
        if not pk:
            # Derive from coordination's partition_key or use default
            pk = "gpt#nestaging"
        rows.append((
            to_uuid(item.get("coordination_uuid")),
            to_uuid(item.get("task_uuid")),
            pk,
            item.get("task_name"),
            item.get("task_description"),
            item.get("initial_task_query"),
            to_jsonb(item.get("subtask_queries", [])),
            to_jsonb(item.get("agent_actions", {})),
            item.get("updated_by"),
            to_timestamp(item.get("created_at")),
            to_timestamp(item.get("updated_at")),
        ))

    if rows:
        execute_values(cur, """
            INSERT INTO ace_tasks
                (coordination_uuid, task_uuid, partition_key,
                 task_name, task_description, initial_task_query,
                 subtask_queries, agent_actions, updated_by,
                 created_at, updated_at)
            VALUES %s
            ON CONFLICT (coordination_uuid, task_uuid) DO NOTHING
        """, rows)
    conn.commit()
    logger.info(f"  Inserted {len(rows)} tasks")
    return len(rows)


def migrate_task_schedules():
    """Migrate ace-task_schedules -> ace_task_schedules."""
    logger.info("Migrating ace-task_schedules...")
    items = scan_all("ace-task_schedules")
    logger.info(f"  Found {len(items)} task schedules")

    rows = []
    for item in items:
        pk = item.get("partition_key")
        if not pk:
            pk = "gpt#nestaging"
        rows.append((
            to_uuid(item.get("task_uuid")),
            to_uuid(item.get("schedule_uuid")),
            to_uuid(item.get("coordination_uuid")),
            pk,
            item.get("schedule"),
            item.get("status", "initial"),
            item.get("updated_by"),
            to_timestamp(item.get("created_at")),
            to_timestamp(item.get("updated_at")),
        ))

    if rows:
        execute_values(cur, """
            INSERT INTO ace_task_schedules
                (task_uuid, schedule_uuid, coordination_uuid, partition_key,
                 schedule, status, updated_by, created_at, updated_at)
            VALUES %s
            ON CONFLICT (task_uuid, schedule_uuid) DO NOTHING
        """, rows)
    conn.commit()
    logger.info(f"  Inserted {len(rows)} task schedules")
    return len(rows)


def migrate_sessions():
    """Migrate ace-sessions -> ace_sessions."""
    logger.info("Migrating ace-sessions...")
    items = scan_all("ace-sessions")
    logger.info(f"  Found {len(items)} sessions")

    rows = []
    for item in items:
        pk = item.get("partition_key")
        if not pk:
            pk = "gpt#nestaging"
        rows.append((
            to_uuid(item.get("coordination_uuid")),
            to_uuid(item.get("session_uuid")),
            pk,
            to_uuid(item.get("task_uuid")),
            item.get("user_id"),
            item.get("task_query"),
            to_jsonb(item.get("input_files", [])),
            int(item.get("iteration_count", 0) or 0),
            to_jsonb(item.get("subtask_queries", [])),
            item.get("status", "initial"),
            item.get("logs"),
            item.get("updated_by"),
            to_timestamp(item.get("created_at")),
            to_timestamp(item.get("updated_at")),
        ))

    # Batch insert in chunks of 1000
    BATCH = 1000
    total = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        execute_values(cur, """
            INSERT INTO ace_sessions
                (coordination_uuid, session_uuid, partition_key, task_uuid,
                 user_id, task_query, input_files, iteration_count,
                 subtask_queries, status, logs, updated_by,
                 created_at, updated_at)
            VALUES %s
            ON CONFLICT (coordination_uuid, session_uuid) DO NOTHING
        """, batch)
        conn.commit()
        total += len(batch)
        logger.info(f"  Inserted {total}/{len(rows)} sessions...")
    return total


def migrate_session_agents():
    """Migrate ace-session_agents -> ace_session_agents."""
    logger.info("Migrating ace-session_agents...")
    items = scan_all("ace-session_agents")
    logger.info(f"  Found {len(items)} session agents")

    rows = []
    for item in items:
        # SessionAgent has no partition_key in DynamoDB — derive from coordination's partition_key
        # or use the partition_key from a related session if available.
        # For now, use the default "gpt#nestaging" since all data is from that partition.
        pk = item.get("partition_key", "gpt#nestaging")
        if not pk:
            pk = "gpt#nestaging"
        rows.append((
            to_uuid(item.get("session_uuid")),
            to_uuid(item.get("session_agent_uuid")),
            pk,
            to_uuid(item.get("coordination_uuid")),
            item.get("agent_uuid"),
            to_jsonb(item.get("agent_action")),
            item.get("user_input"),
            item.get("agent_input"),
            item.get("agent_output"),
            int(item.get("in_degree", 0) or 0),
            item.get("state", "initial"),
            item.get("notes"),
            item.get("updated_by"),
            to_timestamp(item.get("created_at")),
            to_timestamp(item.get("updated_at")),
        ))

    if rows:
        execute_values(cur, """
            INSERT INTO ace_session_agents
                (session_uuid, session_agent_uuid, partition_key,
                 coordination_uuid, agent_uuid, agent_action,
                 user_input, agent_input, agent_output,
                 in_degree, state, notes, updated_by,
                 created_at, updated_at)
            VALUES %s
            ON CONFLICT (session_uuid, session_agent_uuid) DO NOTHING
        """, rows)
    conn.commit()
    logger.info(f"  Inserted {len(rows)} session agents")
    return len(rows)


def migrate_session_runs():
    """Migrate ace-session_runs -> ace_session_runs."""
    logger.info("Migrating ace-session_runs...")
    items = scan_all("ace-session_runs")
    logger.info(f"  Found {len(items)} session runs")

    rows = []
    for item in items:
        pk = item.get("partition_key")
        if not pk:
            pk = "gpt#nestaging"
        rows.append((
            to_uuid(item.get("session_uuid")),
            to_uuid(item.get("run_uuid")),
            pk,
            to_uuid(item.get("thread_uuid")),
            item.get("agent_uuid"),
            to_uuid(item.get("coordination_uuid")),
            item.get("async_task_uuid"),
            to_uuid(item.get("session_agent_uuid")),
            item.get("updated_by"),
            to_timestamp(item.get("created_at")),
            to_timestamp(item.get("updated_at")),
        ))

    # Batch insert in chunks of 1000
    BATCH = 1000
    total = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        execute_values(cur, """
            INSERT INTO ace_session_runs
                (session_uuid, run_uuid, partition_key, thread_uuid,
                 agent_uuid, coordination_uuid, async_task_uuid,
                 session_agent_uuid, updated_by, created_at, updated_at)
            VALUES %s
            ON CONFLICT (session_uuid, run_uuid) DO NOTHING
        """, batch)
        conn.commit()
        total += len(batch)
        logger.info(f"  Inserted {total}/{len(rows)} session runs...")
    return total


# ── Main ──

def main():
    logger.info("=" * 70)
    logger.info("AI Coordination Engine: DynamoDB → PostgreSQL Migration")
    logger.info("=" * 70)
    logger.info(f"Source: DynamoDB ({os.getenv('region_name')})")
    logger.info(f"Dest:   PostgreSQL ({PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['dbname']})")
    logger.info("")

    # Clean existing ACE data (order matters for FK-like constraints)
    logger.info("Cleaning existing PostgreSQL ACE data...")
    for table in ["ace_session_runs", "ace_session_agents", "ace_sessions",
                   "ace_task_schedules", "ace_tasks", "ace_coordinations"]:
        cur.execute(f"DELETE FROM {table}")
        logger.info(f"  Deleted {cur.rowcount} from {table}")
    conn.commit()
    logger.info("")

    # Migrate in dependency order
    t0 = time.time()
    counts = {}
    counts["coordinations"] = migrate_coordinations()
    counts["tasks"] = migrate_tasks()
    counts["task_schedules"] = migrate_task_schedules()
    counts["sessions"] = migrate_sessions()
    counts["session_agents"] = migrate_session_agents()
    counts["session_runs"] = migrate_session_runs()
    elapsed = time.time() - t0

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"Migration complete in {elapsed:.1f}s")
    logger.info("=" * 70)
    for entity, count in counts.items():
        logger.info(f"  {entity}: {count}")
    logger.info(f"  Total: {sum(counts.values())}")

    # Verify
    logger.info("")
    logger.info("Verification — PostgreSQL row counts:")
    for table in ["ace_coordinations", "ace_tasks", "ace_task_schedules",
                   "ace_sessions", "ace_session_agents", "ace_session_runs"]:
        cur.execute(f"SELECT count(*) FROM {table}")
        cnt = cur.fetchone()[0]
        logger.info(f"  {table}: {cnt}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()