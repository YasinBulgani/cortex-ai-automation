"""migration service — thin facade over migration assistant.

HTTP-agnostic. Raises ValueError/KeyError, never HTTPException.

Wraps the core migration functions (migrate_selenium_java, migrate_selenium_py,
migrate_katalon, migrate_source, migrate_directory) and provides a unified
entry-point for callers (routers, CLI, tests).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from app.domains.migration.assistant import (
    MigrationResult,
    SourceFramework,
    migrate_directory,
    migrate_katalon,
    migrate_selenium_java,
    migrate_selenium_py,
    migrate_source,
)

SUPPORTED_FRAMEWORKS: List[SourceFramework] = [
    "selenium-java",
    "selenium-py",
    "katalon",
    "cypress-e2e",
]


def migrate(
    source_code: str,
    framework: str,
    *,
    source_file: Optional[str] = None,
) -> Dict:
    """Migrate source_code from framework to Playwright/DSL.

    Args:
        source_code: Raw source code string to migrate.
        framework: One of 'selenium-java', 'selenium-py', 'katalon', 'cypress-e2e'.
        source_file: Optional file name for attribution in the result.

    Returns:
        MigrationResult serialised as dict (includes success_rate).

    Raises:
        ValueError: if framework is not supported or source_code is empty.
    """
    if not source_code or not source_code.strip():
        raise ValueError("source_code must not be empty")
    if framework not in SUPPORTED_FRAMEWORKS:
        raise ValueError(
            f"Unsupported framework: {framework!r}. "
            f"Supported: {SUPPORTED_FRAMEWORKS}"
        )
    result = migrate_source(source_code, framework=framework, source_file=source_file)  # type: ignore[arg-type]
    return result.to_dict()


def migrate_file(file_path: str, framework: str) -> Dict:
    """Read a file from disk and migrate it.

    Raises:
        KeyError: if file_path does not exist.
        ValueError: if framework is unsupported or file is empty.
    """
    p = Path(file_path)
    if not p.exists():
        raise KeyError(f"File not found: {file_path!r}")
    source_code = p.read_text(encoding="utf-8")
    return migrate(source_code, framework, source_file=file_path)


def migrate_dir(directory: str, framework: str) -> List[Dict]:
    """Migrate all matching files in a directory.

    Raises:
        KeyError: if directory does not exist.
        ValueError: if framework is unsupported.
    """
    d = Path(directory)
    if not d.exists():
        raise KeyError(f"Directory not found: {directory!r}")
    if framework not in SUPPORTED_FRAMEWORKS:
        raise ValueError(f"Unsupported framework: {framework!r}")
    results = migrate_directory(d, framework=framework)  # type: ignore[arg-type]
    return [r.to_dict() for r in results]


def get_supported_frameworks() -> List[str]:
    """Return the list of supported source frameworks."""
    return list(SUPPORTED_FRAMEWORKS)


def migration_summary(result_dict: Dict) -> Dict:
    """Return a concise summary of a migration result dict.

    Useful for logging or API responses where the full result is too verbose.
    """
    return {
        "source_framework": result_dict.get("source_framework"),
        "source_file": result_dict.get("source_file"),
        "steps_total": result_dict.get("steps_total", 0),
        "steps_migrated": result_dict.get("steps_migrated", 0),
        "steps_unhandled": result_dict.get("steps_unhandled", 0),
        "success_rate": result_dict.get("success_rate", 0.0),
        "warnings": result_dict.get("warnings", []),
    }
