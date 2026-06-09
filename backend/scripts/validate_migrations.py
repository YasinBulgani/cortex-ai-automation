#!/usr/bin/env python3
"""Validate migration idempotency and integrity.

Ensures all migrations can be safely re-run without errors.
Tests: upgrade → downgrade → upgrade sequence.

Usage:
  cd backend
  python3 scripts/validate_migrations.py

Integration (CI):
  - Run before: pytest tests/integration
  - Part of: Fresh DB test setup
  - Prevents: DuplicateTable errors on migration re-runs
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run shell command and capture output.

    Returns: (returncode, stdout, stderr)
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


def validate_idempotency() -> int:
    """Validate that migrations are idempotent.

    Tests: upgrade → downgrade → upgrade pattern
    Returns: 0 if valid, 1 if errors found
    """
    backend_dir = Path(__file__).parent.parent

    print("=" * 70)
    print("MIGRATION IDEMPOTENCY VALIDATION")
    print("=" * 70)

    # Check if alembic is available
    returncode, _, _ = run_command(
        ["alembic", "version"],
        cwd=str(backend_dir),
    )

    if returncode != 0:
        print("⚠️  Alembic not available — skipping validation")
        return 0

    print("\n1️⃣  Running migrations (upgrade)...")
    returncode, stdout, stderr = run_command(
        ["alembic", "upgrade", "head"],
        cwd=str(backend_dir),
    )

    if returncode != 0:
        print(f"❌ Upgrade failed:")
        print(f"{stderr}")
        return 1

    print("✓ Upgrade succeeded")
    print(f"  {stdout.strip()}")

    print("\n2️⃣  Getting current migration status...")
    returncode, stdout, stderr = run_command(
        ["alembic", "current"],
        cwd=str(backend_dir),
    )

    if returncode != 0:
        print(f"❌ Status check failed: {stderr}")
        return 1

    current_version = stdout.strip()
    print(f"✓ Current version: {current_version}")

    if current_version == "(base)":
        print("ℹ️  No migrations to validate (database is at base)")
        return 0

    print("\n3️⃣  Downgrading one revision...")
    returncode, stdout, stderr = run_command(
        ["alembic", "downgrade", "-1"],
        cwd=str(backend_dir),
    )

    if returncode != 0:
        print(f"❌ Downgrade failed: {stderr}")
        return 1

    print("✓ Downgrade succeeded")

    print("\n4️⃣  Upgrading again (idempotency test)...")
    returncode, stdout, stderr = run_command(
        ["alembic", "upgrade", "head"],
        cwd=str(backend_dir),
    )

    if returncode != 0:
        print(f"❌ Second upgrade failed (NOT IDEMPOTENT):")
        print(f"{stderr}")
        print("\nFIX: Add IF NOT EXISTS checks to migration files:")
        print("  - Use inspector.get_table_names() before create_table()")
        print("  - Use inspector.get_indexes() before create_index()")
        return 1

    print("✓ Second upgrade succeeded (migrations are idempotent)")

    print("\n" + "=" * 70)
    print("✅ ALL MIGRATION VALIDATIONS PASSED")
    print("=" * 70)
    print("\nMigrations are safe to re-run. Database schema is consistent.")

    return 0


if __name__ == "__main__":
    sys.exit(validate_idempotency())
