"""CI/CD domain service facade.

Thin facade that re-exports the two most commonly needed operations
from the cicd sub-modules so that callers (tests, other domains,
background tasks) can import a single, stable entry-point instead of
reaching directly into ``quality_gate`` or ``jenkins_service``.

Exposed API
-----------
run_quality_gate(config, summary) -> GateResult
    Build a QualityGate from *config* overrides and evaluate it
    against *summary*.  Returns a ``GateResult`` dataclass.

get_jenkins_last_build(db, conn_id, tenant_id, job_name) -> dict
    Fetch the last Jenkins build status for *job_name* via the stored
    connection identified by *conn_id* / *tenant_id*.

list_jenkins_connections(db, tenant_id) -> list[dict]
    Return all Jenkins connections registered for *tenant_id*.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domains.cicd.quality_gate import GateResult, QualityGate, build_gate_from_config
from app.domains.cicd import jenkins_service as _jenkins_svc


def run_quality_gate(config: dict, summary: dict) -> GateResult:
    """Evaluate a quality gate against an execution summary.

    Args:
        config:  Threshold overrides (``min_pass_rate``, ``max_failures``,
                 ``max_duration_s``, ``max_new_flakies``, ``min_coverage_pct``).
                 Any key omitted falls back to the application default from
                 ``settings``.
        summary: Execution summary dict as produced by the test runner
                 (``passed``, ``failed``, ``total``, ``duration_s``, …).

    Returns:
        ``GateResult`` with ``.result`` in ``{"passed", "failed"}`` and a
        list of ``CheckResult`` objects for each threshold evaluated.
    """
    gate: QualityGate = build_gate_from_config(config)
    return gate.evaluate(summary)


async def get_jenkins_last_build(
    db: Session,
    conn_id: str,
    tenant_id: str,
    job_name: str,
) -> dict[str, Any]:
    """Fetch the last build status for *job_name* from a Jenkins connection.

    Args:
        db:        SQLAlchemy session.
        conn_id:   UUID of the stored Jenkins connection.
        tenant_id: Tenant identifier used to scope the connection lookup.
        job_name:  Jenkins job name (URL path segment).

    Returns:
        Dict with ``number``, ``result``, ``url``, ``duration``, and
        ``timestamp`` keys (structure mirrors the Jenkins REST API).
    """
    return await _jenkins_svc.last_build(db, conn_id, tenant_id, job_name)


def list_jenkins_connections(db: Session, tenant_id: str) -> list[dict[str, Any]]:
    """Return all Jenkins connections registered for *tenant_id*.

    Token fields are redacted; use ``jenkins_service`` directly if you
    need the raw (decrypted) credential for outbound calls.
    """
    return _jenkins_svc.list_connections(db, tenant_id)
