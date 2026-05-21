"""Canonical AI workflow API.

This router exposes the plan-level `/ai/workflows` contract while the current
execution engine still runs through agents/v2. The narrow adapter gives the UI
and future persistent store a stable surface without breaking existing
`/agents/v2` clients.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.config import settings
from app.deps import _user_permissions, get_current_user
from app.domains.agents.v2.router import _build_payload
from app.domains.agents.v2.run_store import get_run_store
from app.domains.ai.workflow_queue import enqueue_ai_workflow
from app.domains.ai.workflow_schemas import (
    AIWorkflowApprovalRequest,
    AIWorkflowApprovalResponse,
    AIWorkflowArtifactListResponse,
    AIWorkflowCreateRequest,
    AIWorkflowCreateResponse,
    AIWorkflowDeadLetterListResponse,
    AIWorkflowEventListResponse,
    AIWorkflowHealthSummary,
    AIWorkflowStatus,
)
from app.infra.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/workflows", tags=["ai-workflows"])


def _reports_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "reports"


def _latest_signoff_report() -> dict[str, Any] | None:
    files = sorted(
        _reports_dir().glob("ai-workflow-signoff-*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return {"path": str(path), "report": payload}
    return None


def _latest_soak_report() -> dict[str, Any] | None:
    files = sorted(
        _reports_dir().glob("ai-workflow-soak-*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            summary = payload.get("profile_summary") if isinstance(payload.get("profile_summary"), dict) else {}
            return {
                "path": str(path),
                "profile": payload.get("profile"),
                "runs_total": summary.get("runs_total"),
                "dead_letters_total": summary.get("dead_letters_total"),
                "artifact_count": summary.get("artifact_count"),
                "cost_usd": summary.get("cost_usd"),
                "tokens_used": summary.get("tokens_used"),
                "by_status": summary.get("by_status", {}),
            }
    return None


def _latest_dr_manifest() -> dict[str, Any] | None:
    candidates = [
        Path("/tmp/neurex-dr-drill"),
        _reports_dir(),
    ]
    manifests: list[Path] = []
    for base in candidates:
        if base.exists():
            manifests.extend(base.glob("*manifest-*.json"))
            manifests.extend(base.rglob("*manifest-*.json"))
    manifests = sorted({item.resolve() for item in manifests}, key=lambda item: item.stat().st_mtime, reverse=True)
    for path in manifests:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
            return {
                "path": str(path),
                "created_at": payload.get("created_at"),
                "restore_db": payload.get("restore_db"),
                "artifact_files": counts.get("artifact_files"),
                "artifacts": counts.get("artifacts"),
                "events": counts.get("events"),
                "runs": counts.get("runs"),
            }
    return None


def _build_ops_evidence_summary() -> dict[str, Any] | None:
    latest = _latest_signoff_report()
    if latest is None:
        return None

    report = latest["report"]
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    checks_by_name = {
        item.get("name"): item
        for item in checks
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    soak = checks_by_name.get("workflow_soak") or {}
    dr = checks_by_name.get("dr_restore_drill") or {}
    release_decision = str(report.get("release_decision") or "unknown")

    checklist = [
        {
            "id": "local_full_gate",
            "label": "Local full gate",
            "status": "pass" if not report.get("failed_required_checks") else "fail",
            "detail": "Yerel release evidence pack zorunlu kontrollerle üretildi.",
        },
        {
            "id": "external_soak",
            "label": "External soak",
            "status": str(soak.get("status") or "unknown"),
            "detail": str(soak.get("message") or soak.get("skipped_reason") or "Staging/prod-like soak sonucu bekleniyor."),
        },
        {
            "id": "dr_restore_drill",
            "label": "DR restore drill",
            "status": str(dr.get("status") or "unknown"),
            "detail": str(dr.get("message") or dr.get("skipped_reason") or "Restore kanıtı bekleniyor."),
        },
        {
            "id": "operator_signoff",
            "label": "Operator signoff",
            "status": "pass" if release_decision == "ready_for_operator_approval" else "pending",
            "detail": "JSON evidence release ticket ile operator incelemesine sunulmalı.",
        },
    ]

    return {
        "generated_at": report.get("generated_at"),
        "release_decision": release_decision,
        "llm_quality_score": report.get("llm_quality_score"),
        "report_path": latest["path"],
        "operator_next_steps": report.get("operator_next_steps", []),
        "failed_required_checks": report.get("failed_required_checks", []),
        "soak_report": _latest_soak_report(),
        "dr_manifest": _latest_dr_manifest(),
        "checklist": checklist,
    }


@router.post(
    "",
    response_model=AIWorkflowCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_ai_workflow(
    body: AIWorkflowCreateRequest,
    background: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user),
):
    if body.auto_merge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI workflows do not allow auto_merge; use approval + draft PR flow.",
        )

    input_payload = _build_payload(body)
    if not input_payload:
        raise HTTPException(
            status_code=400,
            detail="Kaynak belirtilmemis. url/file_path/text/swagger_url gerekli.",
        )

    input_payload["workflow"] = {
        "type": body.workflow_type,
        "dry_run": body.dry_run,
        "requires_approval": body.requires_approval,
    }

    tenant_id = getattr(request.state, "tenant_id", "default")
    user_id = str(user.id)

    store = get_run_store()
    workflow_id, initial_state = store.create(
        project_id=body.project_id,
        user_id=user_id,
        tenant_id=tenant_id,
        input_source=body.input_source,
        input_payload=input_payload,
    )
    initial_state["workflow_type"] = body.workflow_type
    initial_state["dry_run"] = body.dry_run
    initial_state["requires_approval"] = body.requires_approval

    initial_status = "pending_approval" if body.requires_approval else "queued"
    store.update_status(workflow_id, initial_status)
    store.publish(
        workflow_id,
        {
            "event_type": "workflow_created",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": workflow_id,
            "workflow_id": workflow_id,
            "data": input_payload["workflow"],
        },
    )

    if body.requires_approval:
        store.publish(
            workflow_id,
            {
                "event_type": "approval_required",
                "timestamp": datetime.utcnow().isoformat(),
                "run_id": workflow_id,
                "workflow_id": workflow_id,
                "message": "Workflow approval bekliyor",
            },
        )
    else:
        _enqueue_or_fail(workflow_id, initial_state, background)

    return AIWorkflowCreateResponse(
        workflow_id=workflow_id,
        run_id=workflow_id,
        status=initial_status,
        created_at=datetime.utcnow(),
        stream_url=f"/api/v1/agents/v2/runs/{workflow_id}/stream",
        detail_url=f"/api/v1/ai/workflows/{workflow_id}",
        events_url=f"/api/v1/ai/workflows/{workflow_id}/events",
        artifacts_url=f"/api/v1/ai/workflows/{workflow_id}/artifacts",
    )


@router.get("/dead-letters", response_model=AIWorkflowDeadLetterListResponse)
async def list_ai_workflow_dead_letters(
    user: User = Depends(get_current_user),
    limit: int = 100,
):
    _require_workflow_admin(user)
    return AIWorkflowDeadLetterListResponse(
        dead_letters=get_run_store().list_dead_letters(limit=min(limit, 500)),
    )


@router.get("/health", response_model=AIWorkflowHealthSummary)
async def get_ai_workflow_health(
    user: User = Depends(get_current_user),
    limit: int = 250,
):
    _require_workflow_admin(user)
    return _build_workflow_health(limit=min(max(limit, 1), 1000))


@router.get("/{workflow_id}", response_model=AIWorkflowStatus)
async def get_ai_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user),
):
    rec = _get_workflow_record(workflow_id)
    _require_workflow_access(user, rec)
    payload = rec.to_status_dict()
    payload["workflow_id"] = workflow_id
    return AIWorkflowStatus(**payload)


@router.get("/{workflow_id}/events", response_model=AIWorkflowEventListResponse)
async def list_ai_workflow_events(
    workflow_id: str,
    user: User = Depends(get_current_user),
):
    rec = _get_workflow_record(workflow_id)
    _require_workflow_access(user, rec)
    return AIWorkflowEventListResponse(
        workflow_id=workflow_id,
        events=get_run_store().list_events(workflow_id),
    )


@router.get("/{workflow_id}/artifacts", response_model=AIWorkflowArtifactListResponse)
async def list_ai_workflow_artifacts(
    workflow_id: str,
    user: User = Depends(get_current_user),
):
    rec = _get_workflow_record(workflow_id)
    _require_workflow_access(user, rec)
    return AIWorkflowArtifactListResponse(
        workflow_id=workflow_id,
        artifacts=get_run_store().list_artifacts(workflow_id),
    )


@router.get("/{workflow_id}/artifacts/{artifact_id}/download")
async def download_ai_workflow_artifact(
    workflow_id: str,
    artifact_id: str,
    user: User = Depends(get_current_user),
):
    rec = _get_workflow_record(workflow_id)
    _require_workflow_access(user, rec)
    artifact = _get_workflow_artifact(workflow_id, artifact_id)
    path = _resolve_downloadable_artifact_path(artifact)
    _verify_artifact_integrity(workflow_id, artifact, path)
    get_run_store().publish(
        workflow_id,
        {
            "event_type": "artifact_downloaded",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": workflow_id,
            "workflow_id": workflow_id,
            "artifact_id": artifact_id,
            "data": {
                "name": artifact.get("name"),
                "kind": artifact.get("kind"),
                "actor_id": str(user.id),
            },
        },
    )
    return FileResponse(
        path,
        media_type=str(artifact.get("mime_type") or "application/octet-stream"),
        filename=str(artifact.get("name") or path.name),
    )


@router.post("/{workflow_id}/approve", response_model=AIWorkflowApprovalResponse)
async def approve_ai_workflow(
    workflow_id: str,
    body: AIWorkflowApprovalRequest,
    background: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user),
):
    rec = _get_workflow_record(workflow_id)
    _require_workflow_approver(user, rec)
    actor_id = str(user.id)

    approval = get_run_store().record_approval(
        workflow_id,
        actor_id=actor_id,
        decision=body.decision,
        note=body.note,
    )
    if approval is None:
        raise HTTPException(status_code=404, detail=f"Workflow bulunamadi: {workflow_id}")

    if body.decision == "approved" and rec.status == "pending_approval":
        get_run_store().update_status(workflow_id, "queued")
        _enqueue_or_fail(workflow_id, rec.state, background)
        rec = _get_workflow_record(workflow_id)
    elif body.decision == "rejected" and rec.status in {"pending_approval", "queued", "running"}:
        get_run_store().update_status(
            workflow_id,
            "cancelled",
            "Workflow approval rejected",
        )
        rec = _get_workflow_record(workflow_id)

    get_run_store().publish(
        workflow_id,
        {
            "event_type": "approval_recorded",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": workflow_id,
            "workflow_id": workflow_id,
            "data": approval,
        },
    )
    return AIWorkflowApprovalResponse(
        workflow_id=workflow_id,
        status=rec.status,
        approval=approval,
    )


@router.post("/{workflow_id}/cancel")
async def cancel_ai_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user),
):
    rec = _get_workflow_record(workflow_id)
    _require_workflow_access(user, rec)
    if rec.status in ("completed", "failed", "cancelled"):
        return {"workflow_id": workflow_id, "run_id": workflow_id, "status": rec.status}

    state = dict(rec.state or {})
    state["cancelled"] = True
    get_run_store().update_state(workflow_id, state)
    try:
        from app.domains.agents.v2.budget_guard import request_cancel

        request_cancel(workflow_id)
    except Exception as exc:
        logger.debug("workflow cancel registry update skipped: %s", exc)

    get_run_store().update_status(workflow_id, "cancelled", "Kullanici iptal etti")
    get_run_store().publish(
        workflow_id,
        {
            "event_type": "cancelled",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": workflow_id,
            "workflow_id": workflow_id,
            "message": "Kullanici iptal etti",
        },
    )
    return {"workflow_id": workflow_id, "run_id": workflow_id, "status": "cancelled"}


def register_state_artifacts(workflow_id: str, state: dict[str, Any]) -> None:
    """Expose known report/test output paths through the canonical artifact API."""
    store = get_run_store()
    metadata = _artifact_metadata(state)

    run_result = state.get("run_result") or {}
    if isinstance(run_result, dict):
        _add_path_artifact(
            workflow_id,
            "allure_report",
            run_result.get("allure_report_path"),
            metadata=metadata,
        )
        _add_path_artifact(
            workflow_id,
            "junit_xml",
            run_result.get("junit_xml_path"),
            metadata=metadata,
        )
        for index, trace_url in enumerate(run_result.get("trace_urls") or [], start=1):
            _add_path_artifact(
                workflow_id,
                "trace",
                trace_url,
                name=f"trace-{index}",
                metadata=metadata,
            )

    report = state.get("report") or {}
    if isinstance(report, dict):
        _add_path_artifact(workflow_id, "html_report", report.get("html_path"), metadata=metadata)
        _add_path_artifact(workflow_id, "pdf_report", report.get("pdf_path"), metadata=metadata)

    try:
        from app.domains.ai.workflow_excel import build_workflow_excel_report

        excel_path = build_workflow_excel_report(
            workflow_id,
            state,
            events=store.list_events(workflow_id),
            artifacts=store.list_artifacts(workflow_id),
        )
        _add_path_artifact(
            workflow_id,
            "excel_report",
            excel_path,
            name="run_report.xlsx",
            metadata={**metadata, "generated_by": "workflow_excel"},
        )
    except Exception as exc:
        logger.warning("Workflow %s Excel artifact olusturulamadi: %s", workflow_id, exc)

    logger.debug("Workflow %s artifact count=%d", workflow_id, len(store.list_artifacts(workflow_id)))


def _enqueue_or_fail(workflow_id: str, state: dict[str, Any], background: BackgroundTasks) -> None:
    try:
        enqueue_ai_workflow(run_id=workflow_id, state=state, background=background)
    except Exception as exc:
        get_run_store().update_status(workflow_id, "failed", f"Queue enqueue failed: {exc}")
        get_run_store().publish(
            workflow_id,
            {
                "event_type": "queue_failed",
                "timestamp": datetime.utcnow().isoformat(),
                "run_id": workflow_id,
                "workflow_id": workflow_id,
                "message": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI workflow queue unavailable",
        )


def _get_workflow_record(workflow_id: str):
    rec = get_run_store().get(workflow_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Workflow bulunamadi: {workflow_id}")
    return rec


def _get_workflow_artifact(workflow_id: str, artifact_id: str) -> dict[str, Any]:
    for artifact in get_run_store().list_artifacts(workflow_id):
        if artifact.get("artifact_id") == artifact_id:
            return artifact
    raise HTTPException(status_code=404, detail=f"Artifact bulunamadi: {artifact_id}")


def _resolve_downloadable_artifact_path(artifact: dict[str, Any]) -> Path:
    storage_path = artifact.get("storage_path")
    if not storage_path or not isinstance(storage_path, str):
        raise HTTPException(status_code=404, detail="Artifact dosya yolu bulunamadi")

    lowered = storage_path.strip().lower()
    if lowered.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu artifact yerel dosya olarak indirilemez",
        )

    root = Path(settings.artifacts_dir).expanduser().resolve()
    raw_path = Path(storage_path).expanduser()
    candidate = raw_path if raw_path.is_absolute() else root / raw_path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Artifact izin verilen depolama alaninin disinda",
        ) from None

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Artifact dosyasi bulunamadi")
    return resolved


def _verify_artifact_integrity(workflow_id: str, artifact: dict[str, Any], path: Path) -> None:
    metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
    expected_sha256 = metadata.get("sha256")
    if not expected_sha256:
        get_run_store().publish(
            workflow_id,
            {
                "event_type": "artifact_integrity_missing",
                "timestamp": datetime.utcnow().isoformat(),
                "run_id": workflow_id,
                "workflow_id": workflow_id,
                "artifact_id": artifact.get("artifact_id"),
                "data": {
                    "name": artifact.get("name"),
                    "kind": artifact.get("kind"),
                },
            },
        )
        try:
            from app.domains.ai.metrics import record_workflow_artifact_integrity_failure

            record_workflow_artifact_integrity_failure(kind=str(artifact.get("kind") or "unknown"))
        except Exception as exc:
            logger.debug("artifact integrity metric skipped: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Artifact butunluk metadata eksik",
        )

    actual_sha256 = _sha256_file(path)
    if actual_sha256 == expected_sha256:
        return

    get_run_store().publish(
        workflow_id,
        {
            "event_type": "artifact_integrity_failed",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": workflow_id,
            "workflow_id": workflow_id,
            "artifact_id": artifact.get("artifact_id"),
            "data": {
                "name": artifact.get("name"),
                "kind": artifact.get("kind"),
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
            },
        },
    )
    try:
        from app.domains.ai.metrics import record_workflow_artifact_integrity_failure

        record_workflow_artifact_integrity_failure(kind=str(artifact.get("kind") or "unknown"))
    except Exception as exc:
        logger.debug("artifact integrity metric skipped: %s", exc)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Artifact butunluk kontrolu basarisiz",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_workflow_access(user: User, rec) -> None:
    if str(rec.user_id) == str(user.id) or _is_workflow_admin(user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Bu workflow kaydına erişim yetkiniz yok",
    )


def _require_workflow_admin(user: User) -> None:
    if _is_workflow_admin(user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="AI workflow admin yetkisi gerekli",
    )


def _require_workflow_approver(user: User, rec) -> None:
    perms = _user_permissions(user)
    has_approval_permission = (
        "admin.*" in perms
        or "ai.workflows.admin" in perms
        or "ai.workflows.approve" in perms
    )
    if not has_approval_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI workflow approval yetkisi gerekli",
        )
    if str(rec.user_id) == str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maker-checker kuralı: workflow sahibi kendi onayını veremez",
        )


def _is_workflow_admin(user: User) -> bool:
    perms = _user_permissions(user)
    return "admin.*" in perms or "ai.workflows.admin" in perms


def _add_path_artifact(
    workflow_id: str,
    kind: str,
    value: Any,
    *,
    name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not value or not isinstance(value, str):
        return
    path = Path(value)
    size_bytes = path.stat().st_size if path.exists() and path.is_file() else 0
    get_run_store().add_artifact(
        workflow_id,
        kind=kind,
        name=name or path.name or kind,
        storage_path=value,
        mime_type=_guess_mime(value),
        size_bytes=size_bytes,
        metadata=metadata,
    )


def _artifact_metadata(state: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "workflow_type": state.get("workflow_type"),
        "dry_run": bool(state.get("dry_run", False)),
    }
    approvals = state.get("approvals")
    if isinstance(approvals, list) and approvals:
        latest = approvals[-1]
        if isinstance(latest, dict):
            metadata.update(
                {
                    "approval_id": latest.get("approval_id"),
                    "approval_decision": latest.get("decision"),
                    "approval_actor_id": latest.get("actor_id"),
                }
            )
    return {key: value for key, value in metadata.items() if value is not None}


def _guess_mime(value: str) -> str:
    suffix = Path(value).suffix.lower()
    if suffix in {".html", ".htm"}:
        return "text/html"
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".xml":
        return "application/xml"
    if suffix == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if suffix == ".json":
        return "application/json"
    if suffix in {".zip", ".gz"}:
        return "application/zip"
    return "application/octet-stream"


def _build_workflow_health(limit: int) -> AIWorkflowHealthSummary:
    store = get_run_store()
    records = store.list(limit=limit)
    dead_letters = store.list_dead_letters(limit=500)
    by_status: dict[str, int] = {}
    by_workflow_type: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    active_statuses = {"pending_approval", "queued", "running"}
    active_ages: list[float] = []
    now = datetime.now(timezone.utc)
    totals = {
        "cost_usd": 0.0,
        "tokens_used": 0,
        "llm_calls_count": 0,
        "artifact_count": 0,
        "artifact_bytes": 0,
        "approval_count": 0,
    }

    for record in records:
        by_status[record.status] = by_status.get(record.status, 0) + 1
        workflow_type = record.state.get("workflow_type") if record.state else None
        if workflow_type:
            key = str(workflow_type)
            by_workflow_type[key] = by_workflow_type.get(key, 0) + 1

        if record.status in active_statuses:
            created_at = _as_utc(record.created_at)
            active_ages.append(max((now - created_at).total_seconds(), 0.0))

        totals["artifact_count"] += len(record.artifacts)
        totals["artifact_bytes"] += sum(int(item.size_bytes or 0) for item in record.artifacts)
        totals["approval_count"] += len(record.approvals)
        if record.state:
            totals["cost_usd"] += float(record.state.get("cost_usd", 0.0) or 0.0)
            totals["tokens_used"] += int(record.state.get("tokens_used", 0) or 0)
            totals["llm_calls_count"] += int(record.state.get("llm_calls_count", 0) or 0)

        for event in record.events:
            event_type = str(event.get("event_type") or "message")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

    return AIWorkflowHealthSummary(
        generated_at=now,
        sample_size=limit,
        runs_total=len(records),
        active_runs=sum(by_status.get(status_name, 0) for status_name in active_statuses),
        by_status=by_status,
        by_workflow_type=by_workflow_type,
        event_counts=event_counts,
        artifact_count=int(totals["artifact_count"]),
        artifact_bytes=int(totals["artifact_bytes"]),
        approval_count=int(totals["approval_count"]),
        dead_letters_total=len(dead_letters),
        recent_dead_letters=dead_letters[:10],
        queue_depth=_workflow_queue_depth(),
        oldest_active_seconds=max(active_ages) if active_ages else None,
        cost_usd=round(float(totals["cost_usd"]), 6),
        tokens_used=int(totals["tokens_used"]),
        llm_calls_count=int(totals["llm_calls_count"]),
        ops_evidence=_build_ops_evidence_summary(),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _workflow_queue_depth() -> int | None:
    try:
        from redis import Redis
        from rq import Queue

        queue = Queue(settings.ai_rq_queue_name, connection=Redis.from_url(settings.redis_url))
        return len(queue)
    except Exception as exc:
        logger.debug("AI workflow queue depth unavailable: %s", exc)
        return None
