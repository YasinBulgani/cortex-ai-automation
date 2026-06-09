"""DSAR export/delete service for AI workflow data."""
from __future__ import annotations

from datetime import datetime, timezone as _tz
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.infra.models import AgentV2Run


def build_user_dsar_export(
    db: Session, *, user_id: str, tenant_id: str | None = None
) -> dict[str, Any]:
    user_uuid = _uuid_or_none(user_id)
    workflows = []
    if user_uuid:
        conditions = [AgentV2Run.user_id == user_uuid]
        if tenant_id is not None:
            conditions.append(AgentV2Run.tenant_id == tenant_id)
        runs = list(
            db.scalars(
                select(AgentV2Run)
                .where(*conditions)
                .order_by(AgentV2Run.created_at.desc())
            ).all()
        )
        workflows = [_workflow_export(run) for run in runs]

    traces = _select_llm_traces(db, user_id=user_id, tenant_id=tenant_id, limit=1000)
    artifact_count = sum(len(item.get("artifacts", [])) for item in workflows)
    return {
        "user_id": user_id,
        "generated_at": datetime.now(_tz.utc),
        "counts": {
            "workflows": len(workflows),
            "workflow_artifacts": artifact_count,
            "llm_traces": len(traces),
        },
        "workflows": workflows,
        "llm_traces": traces,
    }


def delete_user_ai_data(
    db: Session,
    *,
    user_id: str,
    dry_run: bool,
    purge_artifact_files: bool,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    user_uuid = _uuid_or_none(user_id)
    runs: list[AgentV2Run] = []
    if user_uuid:
        conditions = [AgentV2Run.user_id == user_uuid]
        if tenant_id is not None:
            conditions.append(AgentV2Run.tenant_id == tenant_id)
        runs = list(
            db.scalars(
                select(AgentV2Run).where(*conditions)
            ).all()
        )

    artifact_paths = [
        artifact.storage_path
        for run in runs
        for artifact in run.artifacts
        if artifact.storage_path
    ]
    llm_trace_count = _count_llm_traces(db, user_id=user_id, tenant_id=tenant_id)

    response = {
        "user_id": user_id,
        "dry_run": dry_run,
        "deleted": {
            "workflows": len(runs),
            "workflow_events": sum(len(run.events) for run in runs),
            "workflow_artifacts": sum(len(run.artifacts) for run in runs),
            "workflow_approvals": sum(len(run.approvals) for run in runs),
            "llm_traces": llm_trace_count,
        },
        "artifact_files_deleted": [],
        "artifact_files_skipped": [],
    }
    if dry_run:
        response["artifact_files_skipped"] = list(artifact_paths)
        return response

    if purge_artifact_files:
        deleted, skipped = _purge_artifact_files(artifact_paths)
        response["artifact_files_deleted"] = deleted
        response["artifact_files_skipped"] = skipped
    else:
        response["artifact_files_skipped"] = list(artifact_paths)

    _delete_llm_traces(db, user_id=user_id, tenant_id=tenant_id)
    if user_uuid:
        delete_conditions = [AgentV2Run.user_id == user_uuid]
        if tenant_id is not None:
            delete_conditions.append(AgentV2Run.tenant_id == tenant_id)
        db.execute(delete(AgentV2Run).where(*delete_conditions))
    db.commit()
    return response


def _workflow_export(run: AgentV2Run) -> dict[str, Any]:
    return {
        "run_id": str(run.id),
        "project_id": str(run.project_id),
        "workflow_type": run.workflow_type,
        "status": run.status,
        "input_source": run.input_source,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "cost_usd": float(run.cost_usd or 0.0),
        "tokens_used": int(run.tokens_used or 0),
        "events": [
            {
                "event_type": event.event_type,
                "agent_name": event.agent_name,
                "message": event.message,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in sorted(run.events, key=lambda item: item.created_at)
        ],
        "artifacts": [
            {
                "artifact_id": str(artifact.id),
                "kind": artifact.kind,
                "name": artifact.name,
                "storage_path": artifact.storage_path,
                "mime_type": artifact.mime_type,
                "size_bytes": artifact.size_bytes,
                "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
            }
            for artifact in sorted(run.artifacts, key=lambda item: item.created_at)
        ],
        "approvals": [
            {
                "approval_id": str(approval.id),
                "decision": approval.decision,
                "created_at": approval.created_at.isoformat() if approval.created_at else None,
            }
            for approval in sorted(run.approvals, key=lambda item: item.created_at)
        ],
    }


def _select_llm_traces(
    db: Session, *, user_id: str, limit: int, tenant_id: str | None = None
) -> list[dict[str, Any]]:
    if not _table_exists(db, "llm_traces"):
        return []
    where = "WHERE user_id = :user_id"
    params: dict[str, Any] = {"user_id": user_id, "limit": limit}
    if tenant_id is not None:
        where += " AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id
    rows = db.execute(
        text(
            f"""
            SELECT id, run_id, agent_name, model, provider, task_type, status,
                   prompt_id, prompt_version, created_at
            FROM llm_traces
            {where}
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def _count_llm_traces(db: Session, *, user_id: str, tenant_id: str | None = None) -> int:
    """S-HIGH-8: SQL audit note.

    Query uses f-string, but WHERE clause is safe:
    - Literal table name (hardcoded "llm_traces")
    - WHERE conditions constructed from literals only ("user_id", "tenant_id" keys)
    - All values passed as bound parameters (:user_id, :tenant_id) — not interpolated
    - No user input in column names or table name

    This is SAFE from SQL injection. Parameterized approach is correct.
    """
    if not _table_exists(db, "llm_traces"):
        return 0
    where = "WHERE user_id = :user_id"
    params: dict[str, Any] = {"user_id": user_id}
    if tenant_id is not None:
        where += " AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id
    return int(
        db.execute(
            text(f"SELECT count(*) FROM llm_traces {where}"),
            params,
        ).scalar()
        or 0
    )


def _delete_llm_traces(db: Session, *, user_id: str, tenant_id: str | None = None) -> None:
    """S-HIGH-8: SQL audit note.

    DELETE query structure is safe (same as _count_llm_traces):
    - Table name hardcoded, no user input
    - WHERE conditions from literal strings only
    - All values parameterized (no interpolation)

    This is SAFE from SQL injection.
    """
    if not _table_exists(db, "llm_traces"):
        return
    where = "WHERE user_id = :user_id"
    params: dict[str, Any] = {"user_id": user_id}
    if tenant_id is not None:
        where += " AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id
    db.execute(text(f"DELETE FROM llm_traces {where}"), params)


def _table_exists(db: Session, table_name: str) -> bool:
    try:
        return bool(
            db.execute(
                text("SELECT to_regclass(:table_name) IS NOT NULL"),
                {"table_name": f"public.{table_name}"},
            ).scalar()
        )
    except Exception:
        return False


def _purge_artifact_files(paths: list[str]) -> tuple[list[str], list[str]]:
    deleted: list[str] = []
    skipped: list[str] = []
    root = Path(settings.artifacts_dir).resolve()
    for raw_path in paths:
        path = Path(raw_path).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            skipped.append(raw_path)
            continue
        if path.exists() and path.is_file():
            path.unlink()
            deleted.append(raw_path)
        else:
            skipped.append(raw_path)
    return deleted, skipped


def _uuid_or_none(value: str) -> str | None:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None
