"""Public service facade for the catalog domain.

The catalog domain owns the DSL step library — the registry of reusable test
steps that other domains (automation, evals, dsl) can discover and compose.
All reads and writes to the step catalog should go through this module.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = [
    "list_dsl_steps",
    "search_steps",
    "create_step",
    "delete_step",
]


def list_dsl_steps(*, project_id: str | None = None, tag: str | None = None) -> list[dict]:
    """Return all DSL step definitions, optionally filtered by project or tag.

    Raises:
        NotImplementedError: Until the step registry is implemented.
    """
    raise NotImplementedError(
        "TODO: implement list_dsl_steps — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def search_steps(query: str, *, project_id: str | None = None) -> list[dict]:
    """Full-text search over step names, descriptions, and tags.

    Args:
        query: Search string.
        project_id: Scope search to a specific project if provided.

    Returns:
        Ordered list of matching step dicts.

    Raises:
        NotImplementedError: Until search is implemented.
    """
    raise NotImplementedError(
        "TODO: implement search_steps — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def create_step(step: dict, *, created_by: str | None = None) -> dict:
    """Persist a new DSL step definition.

    Args:
        step: Step payload matching the catalog schema.
        created_by: User identifier for audit purposes.

    Returns:
        The persisted step dict with server-assigned ``id``.

    Raises:
        NotImplementedError: Until persistence is implemented.
    """
    raise NotImplementedError(
        "TODO: implement create_step — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def delete_step(step_id: str) -> bool:
    """Delete a DSL step by ID.

    Returns:
        True if deleted, False if not found.

    Raises:
        NotImplementedError: Until persistence is implemented.
    """
    raise NotImplementedError(
        "TODO: implement delete_step — see docs/planning/END_USER_GAPS_PLAN.md"
    )
