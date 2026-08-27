# -*- coding: utf-8 -*-
"""Static adoption guard — ensures no direct models.dynamodb imports in the GraphQL layer.

This test fails the build if any module in queries/, mutations/, types/, or handlers/
imports from models.dynamodb directly or calls DynamoDB insert_update_* / delete_*
free functions — which would bypass the repository dispatch boundary.
"""
from __future__ import print_function

__author__ = "bibow"

import ast
import os
import re
import sys
from pathlib import Path

import pytest


# Directories that must NOT import from models.dynamodb or models.batch_loaders
_GUARDED_DIRS = ["queries", "mutations", "types", "handlers"]

# The base package directory
_PKG_DIR = Path(__file__).resolve().parent.parent / "ai_coordination_engine"


def _find_python_files(directory: Path) -> list:
    """Find all .py files in a directory (recursive)."""
    if not directory.exists():
        return []
    return list(directory.rglob("*.py"))


def _check_file_for_violations(filepath: Path) -> list:
    """Check a single file for forbidden imports/calls. Returns list of violations."""
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return []

    # Parse AST to check imports
    try:
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        # Check import statements
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # Forbidden: from ..models.dynamodb, from ..models.batch_loaders, from ...models.dynamodb
            if "models.dynamodb" in module or "models.batch_loaders" in module:
                # Allow: from ..models.repositories (that's the dispatch boundary)
                if "models.repositories" not in module:
                    violations.append(
                        f"Line {node.lineno}: forbidden import '{module}' "
                        f"— use models.repositories.get_repo() instead"
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "models.dynamodb" in alias.name or "models.batch_loaders" in alias.name:
                    violations.append(
                        f"Line {node.lineno}: forbidden import '{alias.name}'"
                    )

    # Also check for direct insert_update_*/delete_* free function calls
    # (these should go through get_repo().insert_update() / .delete())
    for match in re.finditer(r"\b(insert_update_|delete_)(coordination|session|session_agent|session_run|task|task_schedule)\s*\(", content):
        line_num = content[:match.start()].count("\n") + 1
        # Allow if it's inside a string/comment — rough check
        line = content.split("\n")[line_num - 1]
        if line.strip().startswith("#") or '"""' in line[:match.start()]:
            continue
        violations.append(
            f"Line {line_num}: direct free function call '{match.group()}' "
            f"— use get_repo().insert_update() / .delete() instead"
        )

    return violations


class TestAdoptionGuard:
    """Ensure the GraphQL layer routes persistence through the repository boundary."""

    @pytest.mark.parametrize("dirname", _GUARDED_DIRS)
    def test_no_direct_dynamodb_imports(self, dirname: str):
        """No module in queries/, mutations/, types/, handlers/ may import from models.dynamodb."""
        directory = _PKG_DIR / dirname
        all_violations = []

        for filepath in _find_python_files(directory):
            if "__pycache__" in str(filepath):
                continue
            violations = _check_file_for_violations(filepath)
            if violations:
                rel_path = filepath.relative_to(_PKG_DIR)
                for v in violations:
                    all_violations.append(f"{rel_path}: {v}")

        assert not all_violations, (
            f"Found {len(all_violations)} forbidden import(s)/call(s) in {dirname}/:\n"
            + "\n".join(f"  - {v}" for v in all_violations)
        )


class TestDynamoDBDispatch:
    """Verify that DynamoDB repositories register and resolve correctly."""

    def test_all_entities_resolve_under_dynamodb(self):
        """All 6 entities should resolve through get_repo() under DynamoDB backend."""
        from ai_coordination_engine.handlers.config import Config
        Config.DB_BACKEND = "dynamodb"

        from ai_coordination_engine.models.repositories import get_repo, clear_registry
        clear_registry()

        expected_entities = [
            "coordination", "session", "session_agent",
            "session_run", "task", "task_schedule",
        ]

        for entity in expected_entities:
            repo = get_repo(entity)
            assert repo is not None, f"get_repo('{entity}') returned None"
            assert repo.entity_type == entity, (
                f"get_repo('{entity}').entity_type = '{repo.entity_type}', expected '{entity}'"
            )

    def test_get_loaders_returns_request_loaders(self):
        """get_loaders() should return RequestLoaders under DynamoDB backend."""
        from ai_coordination_engine.handlers.config import Config
        Config.DB_BACKEND = "dynamodb"

        from ai_coordination_engine.models.repositories import get_loaders, clear_registry
        clear_registry()

        context = {"logger": None}
        loaders = get_loaders(context)
        assert loaders is not None, "get_loaders() returned None"
        # Verify it has the expected loader properties
        assert hasattr(loaders, "coordination_loader")
        assert hasattr(loaders, "session_loader")
        assert hasattr(loaders, "task_loader")


class TestPostgreSQLDispatch:
    """Verify that PostgreSQL repositories register and resolve correctly."""

    def test_all_entities_resolve_under_postgresql(self):
        """All 6 entities should resolve through get_repo() under PostgreSQL backend."""
        from ai_coordination_engine.handlers.config import Config
        Config.DB_BACKEND = "postgresql"

        from ai_coordination_engine.models.repositories import get_repo, clear_registry
        clear_registry()

        expected_entities = [
            "coordination", "session", "session_agent",
            "session_run", "task", "task_schedule",
        ]

        for entity in expected_entities:
            repo = get_repo(entity)
            assert repo is not None, f"get_repo('{entity}') returned None under postgresql"
            assert repo.entity_type == entity, (
                f"get_repo('{entity}').entity_type = '{repo.entity_type}', expected '{entity}'"
            )

    def test_both_backends_register_identical_entity_sets(self):
        """Both backends should register the same set of entity types."""
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

        assert ddb_set == expected, f"DynamoDB entities mismatch: {ddb_set} != {expected}"
        assert pg_set == expected, f"PostgreSQL entities mismatch: {pg_set} != {expected}"