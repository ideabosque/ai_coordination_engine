#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Data migration script for CoordinationModel agents field.

This script migrates data from the legacy 'agents' field (ListAttribute of MapAttribute)
to the new 'agent_uuids' field (ListAttribute of UnicodeAttribute).
"""
from __future__ import print_function

import logging
import sys
from typing import Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_coordination_agents(dry_run: bool = True) -> Tuple[int, int]:
    """Migrate CoordinationModel agents data.

    Args:
        dry_run: If True, only log changes without applying them

    Returns:
        Tuple of (processed_count, migrated_count)
    """
    from ai_coordination_engine.models.coordination import CoordinationModel

    processed_count = 0
    migrated_count = 0

    logger.info(f"Starting migration (dry_run={dry_run})")

    for coordination in CoordinationModel.scan():
        processed_count += 1

        if coordination.agent_uuids and len(coordination.agent_uuids) > 0:
            logger.debug(f"Skipping {coordination.coordination_uuid}: already migrated")
            continue

        if not coordination.agents:
            logger.debug(f"Skipping {coordination.coordination_uuid}: no agents data")
            continue

        agent_uuids = []
        for agent in coordination.agents:
            agent_uuid = agent.get("agent_uuid")
            if agent_uuid:
                agent_uuids.append(agent_uuid)

        if not agent_uuids:
            logger.warning(f"No valid agent_uuids found for {coordination.coordination_uuid}")
            continue

        logger.info(
            f"Migrating {coordination.coordination_uuid}: "
            f"{len(coordination.agents)} agents -> {len(agent_uuids)} UUIDs"
        )

        if not dry_run:
            try:
                coordination.update(actions=[
                    CoordinationModel.agent_uuids.set(agent_uuids)
                ])
                migrated_count += 1
                logger.info(f"Successfully migrated {coordination.coordination_uuid}")
            except Exception as e:
                logger.error(f"Failed to migrate {coordination.coordination_uuid}: {e}")
        else:
            migrated_count += 1

    logger.info(
        f"Migration complete: {processed_count} processed, {migrated_count} migrated"
    )
    return processed_count, migrated_count


def verify_migration() -> bool:
    """Verify the migration by checking data consistency.

    Returns:
        True if verification passes, False otherwise
    """
    from ai_coordination_engine.models.coordination import CoordinationModel

    logger.info("Starting migration verification")

    inconsistent_records = []

    for coordination in CoordinationModel.scan():
        has_legacy = bool(coordination.agents)
        has_new = bool(coordination.agent_uuids)

        if has_legacy and has_new:
            legacy_uuids = set(
                a.get("agent_uuid") for a in coordination.agents if a.get("agent_uuid")
            )
            new_uuids = set(coordination.agent_uuids)

            if legacy_uuids != new_uuids:
                inconsistent_records.append({
                    "coordination_uuid": coordination.coordination_uuid,
                    "legacy_uuids": legacy_uuids,
                    "new_uuids": new_uuids
                })

    if inconsistent_records:
        logger.error(f"Found {len(inconsistent_records)} inconsistent records")
        for record in inconsistent_records[:10]:
            logger.error(f"  {record}")
        return False

    logger.info("Verification passed: All records are consistent")
    return True


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    verify = "--verify" in sys.argv

    if verify:
        success = verify_migration()
        sys.exit(0 if success else 1)
    else:
        processed, migrated = migrate_coordination_agents(dry_run=dry_run)
        print(f"Processed: {processed}, Migrated: {migrated}")
