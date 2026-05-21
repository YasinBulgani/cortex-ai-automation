"""Retention cleanup for AI workflow artifacts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.infra.models import AgentV2Run, AgentV2RunArtifact


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def cleanup_workflow_artifacts(
    db: Session,
    *,
    retention_days: int | None = None,
    dry_run: bool = True,
    now: datetime | None = None,
    terminal_statuses: set[str] | None = None,
    candidates: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Delete old terminal workflow artifact files and their artifact rows.

    The cleanup is deliberately conservative:
    - non-terminal workflow artifacts are never touched;
    - URL artifacts are skipped;
    - paths outside `settings.artifacts_dir` are skipped;
    - dry-run is the default and performs no mutation.
    """
    retention_days = retention_days if retention_days is not None else settings.ai_workflow_artifact_retention_days
    if retention_days <= 0:
        raise ValueError("retention_days must be greater than zero")

    statuses = terminal_statuses or TERMINAL_STATUSES
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "retention_days": retention_days,
        "cutoff": cutoff.isoformat(),
        "matched_artifacts": 0,
        "db_rows_deleted": 0,
        "bytes_reclaimable": 0,
        "bytes_deleted": 0,
        "files_deleted": [],
        "files_missing": [],
        "files_skipped": [],
    }
    if candidates is None:
        try:
            rows = _query_candidates(db, cutoff, statuses)
        except SQLAlchemyError as exc:
            result["skipped_reason"] = "artifact_tables_unavailable"
            result["query_error"] = _compact_error(exc)
            return result
    else:
        rows = list(candidates)

    for artifact in rows:
        if not _artifact_run_is_eligible(artifact, cutoff, statuses):
            continue
        result["matched_artifacts"] += 1
        result["bytes_reclaimable"] += int(getattr(artifact, "size_bytes", 0) or 0)
        raw_path = str(getattr(artifact, "storage_path", "") or "")
        path_status, resolved_path = _resolve_retention_path(raw_path)
        if path_status != "ok" or resolved_path is None:
            result["files_skipped"].append({"path": raw_path, "reason": path_status})
            continue

        if dry_run:
            result["files_skipped"].append({"path": raw_path, "reason": "dry_run"})
            continue

        if resolved_path.exists() and resolved_path.is_file():
            size = resolved_path.stat().st_size
            resolved_path.unlink()
            result["files_deleted"].append(raw_path)
            result["bytes_deleted"] += size
        else:
            result["files_missing"].append(raw_path)

        db.delete(artifact)
        result["db_rows_deleted"] += 1

    if not dry_run:
        db.commit()
    return result


def _query_candidates(
    db: Session,
    cutoff: datetime,
    statuses: set[str],
) -> list[AgentV2RunArtifact]:
    stmt = (
        select(AgentV2RunArtifact)
        .join(AgentV2RunArtifact.run)
        .where(
            AgentV2Run.status.in_(statuses),
            AgentV2Run.completed_at.is_not(None),
            AgentV2Run.completed_at < cutoff,
        )
        .order_by(AgentV2RunArtifact.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def _artifact_run_is_eligible(artifact: Any, cutoff: datetime, statuses: set[str]) -> bool:
    run = getattr(artifact, "run", None)
    if run is None:
        return False
    if getattr(run, "status", None) not in statuses:
        return False
    completed_at = getattr(run, "completed_at", None)
    if completed_at is None:
        return False
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    return completed_at < cutoff


def _resolve_retention_path(raw_path: str) -> tuple[str, Path | None]:
    if not raw_path:
        return "empty_path", None
    lowered = raw_path.strip().lower()
    if lowered.startswith(("http://", "https://")):
        return "url_artifact", None

    root = Path(settings.artifacts_dir).expanduser().resolve()
    path = Path(raw_path).expanduser()
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        return "outside_artifacts_dir", None
    return "ok", resolved


def _compact_error(exc: BaseException) -> str:
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    return f"{exc.__class__.__name__}: {message}"
