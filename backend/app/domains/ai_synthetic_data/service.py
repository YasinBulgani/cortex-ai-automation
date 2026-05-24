"""Public service facade for the ai_synthetic_data domain.

Provides the canonical API surface for generating and managing synthetic
datasets. Differential-privacy and advanced-generator internals should be
accessed only through this module.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = [
    "generate_data",
    "list_datasets",
    "delete_dataset",
]


def generate_data(schema: dict, *, project_id: str, rows: int = 100) -> dict:
    """Generate synthetic data rows conforming to *schema*.

    Args:
        schema: JSON-schema-compatible field definitions.
        project_id: The owning project's identifier.
        rows: Number of rows to generate.

    Returns:
        A dict with ``dataset_id`` and ``rows`` keys.

    Raises:
        NotImplementedError: Until the generation pipeline is wired up.
    """
    raise NotImplementedError(
        "TODO: implement generate_data — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def list_datasets(project_id: str) -> list[dict]:
    """Return all synthetic datasets for a project.

    Raises:
        NotImplementedError: Until storage layer is implemented.
    """
    raise NotImplementedError(
        "TODO: implement list_datasets — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def delete_dataset(dataset_id: str, project_id: str) -> bool:
    """Delete a synthetic dataset by ID.

    Returns:
        True if the dataset was deleted, False if it was not found.

    Raises:
        NotImplementedError: Until storage layer is implemented.
    """
    raise NotImplementedError(
        "TODO: implement delete_dataset — see docs/planning/END_USER_GAPS_PLAN.md"
    )
