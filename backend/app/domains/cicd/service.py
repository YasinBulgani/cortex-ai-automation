"""Public service facade for the cicd domain.

Aggregates Jenkins connection management, quality-gate evaluation, and
test-impact analysis (TIA) into a single importable surface.
"""
from __future__ import annotations

import logging

from app.domains.cicd.jenkins_service import (
    create_connection,
    decrypt_token,
    delete_connection,
    encrypt_token,
    get_connection,
    list_connections,
)
from app.domains.cicd.quality_gate import (
    BaseCheck,
    CheckResult,
    DurationCheck,
    MaxFailuresCheck,
    PassRateCheck,
    QualityGate,
)
from app.domains.cicd.tia import (
    CoverageMap,
    ImpactResult,
    build_import_graph,
    git_diff_names,
    is_test_file,
    map_changes_to_tests,
    parse_coverage_xml,
)

logger = logging.getLogger(__name__)

__all__ = [
    # jenkins_service
    "list_connections",
    "get_connection",
    "create_connection",
    "delete_connection",
    "encrypt_token",
    "decrypt_token",
    # quality_gate
    "QualityGate",
    "BaseCheck",
    "CheckResult",
    "PassRateCheck",
    "MaxFailuresCheck",
    "DurationCheck",
    # tia
    "CoverageMap",
    "ImpactResult",
    "is_test_file",
    "parse_coverage_xml",
    "build_import_graph",
    "git_diff_names",
    "map_changes_to_tests",
    # stubs
    "get_pipeline_status",
    "trigger_build",
]


def get_pipeline_status(connection_id: str, job_name: str, *, tenant_id: str) -> dict:
    """Return the latest build status for a Jenkins job.

    Args:
        connection_id: ID of the stored Jenkins connection.
        job_name: Jenkins job or pipeline name.
        tenant_id: Scoping tenant identifier.

    Returns:
        A dict with ``status``, ``result``, ``url``, and ``timestamp`` keys.

    Raises:
        NotImplementedError: Until Jenkins polling is implemented.
    """
    raise NotImplementedError(
        "TODO: implement get_pipeline_status — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def trigger_build(connection_id: str, job_name: str, *, params: dict | None = None, tenant_id: str) -> dict:
    """Trigger a Jenkins build and return the queue item handle.

    Args:
        connection_id: ID of the stored Jenkins connection.
        job_name: Jenkins job or pipeline name.
        params: Optional build parameters.
        tenant_id: Scoping tenant identifier.

    Returns:
        A dict with ``queue_item_url`` and ``estimated_start`` keys.

    Raises:
        NotImplementedError: Until build triggering is implemented.
    """
    raise NotImplementedError(
        "TODO: implement trigger_build — see docs/planning/END_USER_GAPS_PLAN.md"
    )
