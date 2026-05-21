"""CI/CD Integration Router — GitHub Actions, GitLab CI, Jenkins webhook receivers.

Endpoints:
  POST /cicd/webhook/github               - GitHub Actions webhook
  POST /cicd/webhook/gitlab               - GitLab CI webhook
  POST /cicd/webhook/jenkins              - Jenkins build webhook
  GET  /cicd/events                       - List recent CI/CD events
  POST /cicd/trigger/{project_id}         - Trigger test run from CI/CD context
  POST /cicd/quality-gate/evaluate        - Evaluate quality gate for a test run
  POST /cicd/impact-analysis/{project_id} - Git diff → prioritized test selection
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user, get_optional_user
from app.domains.tspm.models import TspmProject, TspmProjectMember
from app.infra.database import get_db
from app.config import settings
from fastapi import Depends

router = APIRouter(prefix="/cicd", tags=["cicd"])
logger = logging.getLogger(__name__)

GITHUB_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
GITLAB_TOKEN = os.environ.get("GITLAB_WEBHOOK_TOKEN", "")
JENKINS_TOKEN = os.environ.get("JENKINS_WEBHOOK_TOKEN", "")
ENGINE_BASE = (os.environ.get("ENGINE_BASE_URL") or settings.engine_base_url).rstrip("/")
ENGINE_KEY = os.environ.get("ENGINE_INTERNAL_KEY") or settings.engine_internal_key

# CI Token: trigger endpoint'ini dis pipeline cagrilarindan korur.
CI_TOKEN = os.environ.get("CI_TRIGGER_TOKEN", "")


def _webhook_secret_required() -> bool:
    forced = os.environ.get("CICD_REQUIRE_WEBHOOK_SECRETS", "").lower() in {"1", "true", "yes"}
    return forced or settings.is_production_like


def _ci_trigger_token_required() -> bool:
    forced = os.environ.get("CICD_REQUIRE_TRIGGER_TOKEN", "").lower() in {"1", "true", "yes"}
    return forced or settings.is_production_like


def _verify_header_token(
    *,
    token_name: str,
    configured_token: str,
    provided_token: str,
) -> None:
    if _webhook_secret_required() and not configured_token:
        raise HTTPException(503, f"{token_name} ayari zorunlu ama eksik")
    if configured_token and not hmac.compare_digest(provided_token, configured_token):
        raise HTTPException(401, f"Invalid {token_name}")

def _summarize(payload: dict) -> dict:
    """Extract key info without storing full payload."""
    keys = ["ref", "repository", "action", "status", "conclusion", "pipeline", "build_url",
            "commit", "branch", "tag", "object_kind", "state"]
    return {k: payload.get(k) for k in keys if k in payload}


def _normalize_ref(ref: str) -> str:
    if ref.startswith("refs/heads/"):
        return ref.split("refs/heads/", 1)[1]
    if ref.startswith("refs/tags/"):
        return ref.split("refs/tags/", 1)[1]
    return ref


def _is_admin_user(user: User) -> bool:
    for role in user.roles:
        for role_permission in role.permissions:
            if role_permission.permission == "admin.*":
                return True
    return False


def _project_exists(db: Session, project_id: str) -> None:
    if db.get(TspmProject, project_id) is None:
        raise HTTPException(404, "Proje bulunamadi")


def _require_project_access(db: Session, user: User, project_id: str) -> None:
    _project_exists(db, project_id)
    if _is_admin_user(user):
        return
    is_member = db.scalar(
        select(func.count()).where(
            TspmProjectMember.project_id == project_id,
            TspmProjectMember.user_id == user.id,
        )
    )
    if not is_member:
        raise HTTPException(403, "Bu projeye erisim yetkiniz yok")


def _extract_commit_sha(payload: dict) -> str:
    candidates = [
        payload.get("after"),
        payload.get("checkout_sha"),
        payload.get("sha"),
        payload.get("commit"),
        payload.get("workflow_run", {}).get("head_sha"),
        payload.get("object_attributes", {}).get("sha"),
        payload.get("build", {}).get("scm", {}).get("commit"),
    ]
    for value in candidates:
        if isinstance(value, str) and value:
            return value[:64]
    return ""


def _extract_branch(payload: dict) -> str:
    candidates = [
        payload.get("branch"),
        payload.get("ref"),
        payload.get("object_attributes", {}).get("ref"),
        payload.get("workflow_run", {}).get("head_branch"),
        payload.get("build", {}).get("branch"),
    ]
    for value in candidates:
        if isinstance(value, str) and value:
            return _normalize_ref(value)[:128]
    return ""


def _extract_author(payload: dict) -> str:
    candidates = [
        payload.get("sender", {}).get("login"),
        payload.get("user_username"),
        payload.get("user_name"),
        payload.get("pusher", {}).get("name"),
        payload.get("author", {}).get("name"),
    ]
    for value in candidates:
        if isinstance(value, str) and value:
            return value[:256]
    return ""


def _serialize_json(value: Any) -> str:
    return json.dumps(value, default=str)


def _store_event(
    db: Session,
    source: str,
    event_type: str,
    payload: dict,
    project_ref: str = "",
) -> dict:
    """Persist webhook event while preserving the public response shape."""
    event = {
        "id": hashlib.md5(
            f"{source}{event_type}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:12],
        "source": source,
        "event_type": event_type,
        "project_ref": project_ref,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload_summary": _summarize(payload),
    }

    repo_name = ""
    repository = payload.get("repository")
    if isinstance(repository, dict):
        repo_name = repository.get("full_name", "") or repository.get("name", "")

    params = {
        "event_id": event["id"],
        "source": source,
        "event_type": event_type,
        "project_ref": project_ref[:256],
        "payload": _serialize_json(payload),
        "payload_summary": _serialize_json(event["payload_summary"]),
        "commit_sha": _extract_commit_sha(payload),
        "branch": _extract_branch(payload),
        "repo_name": (repo_name or project_ref)[:256],
        "author": _extract_author(payload),
        "received_at": event["received_at"],
    }

    try:
        db.execute(
            text(
                """
                INSERT INTO cicd_webhook_events (
                    event_id, source, event_type, project_ref, payload, payload_summary,
                    commit_sha, branch, repo_name, author, received_at
                )
                VALUES (
                    :event_id, :source, :event_type, :project_ref,
                    CAST(:payload AS JSONB), CAST(:payload_summary AS JSONB),
                    :commit_sha, :branch, :repo_name, :author, :received_at
                )
                """
            ),
            params,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist CI/CD webhook event %s", event["id"])
        raise

    return event


def _list_events(db: Session, source: Optional[str] = None, limit: int = 50) -> dict:
    """Fetch recent CI/CD events with the legacy response payload shape."""
    safe_limit = max(1, min(limit, 500))
    rows = db.execute(
        text(
            """
            SELECT
                event_id AS id,
                source,
                event_type,
                project_ref,
                received_at,
                payload_summary
            FROM cicd_webhook_events
            WHERE (:source IS NULL OR source = :source)
            ORDER BY received_at DESC
            LIMIT :limit
            """
        ),
        {"source": source, "limit": safe_limit},
    ).mappings().all()

    total = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM cicd_webhook_events
            WHERE (:source IS NULL OR source = :source)
            """
        ),
        {"source": source},
    ).scalar_one()

    events = []
    for row in rows:
        payload_summary = row.get("payload_summary") or {}
        if isinstance(payload_summary, str):
            try:
                payload_summary = json.loads(payload_summary)
            except ValueError:
                payload_summary = {}

        received_at = row.get("received_at")
        if hasattr(received_at, "isoformat"):
            received_at = received_at.isoformat()

        events.append(
            {
                "id": row.get("id", ""),
                "source": row.get("source", ""),
                "event_type": row.get("event_type", ""),
                "project_ref": row.get("project_ref", ""),
                "received_at": received_at or "",
                "payload_summary": payload_summary if isinstance(payload_summary, dict) else {},
            }
        )

    return {"events": events, "total": int(total)}


def _verify_github_signature(body: bytes, signature: str) -> bool:
    if not signature:
        return False
    if not GITHUB_SECRET:
        return True
    expected = "sha256=" + hmac.new(GITHUB_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ─── GitHub ──────────────────────────────────────────────────────────────────

@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
):
    body = await request.body()
    if _webhook_secret_required() and not GITHUB_SECRET:
        logger.error("GitHub webhook secret zorunlu ama ayarlanmamis.")
        raise HTTPException(503, "GitHub webhook secret ayari eksik")
    if GITHUB_SECRET and not _verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(401, "Invalid GitHub webhook signature")

    payload: dict = {}
    try:
        payload = await request.json()
    except ValueError as exc:
        logger.warning("Invalid GitHub webhook payload: %s", exc)

    repo = payload.get("repository", {}).get("full_name", "unknown")
    ref = payload.get("ref", "")
    action = payload.get("action", "")
    conclusion = payload.get("workflow_run", {}).get("conclusion", "")

    ev = _store_event(db, "github", x_github_event, payload, project_ref=repo)

    # Auto-trigger TestwrightAI tests when a workflow run completes successfully
    if x_github_event == "workflow_run" and conclusion == "success":
        background_tasks.add_task(_auto_trigger_on_ci_success, "github", repo, ref, payload)

    return {"ok": True, "event_id": ev["id"], "event": x_github_event, "repo": repo}


# ─── GitLab ──────────────────────────────────────────────────────────────────

@router.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_gitlab_token: str = Header(default=""),
    x_gitlab_event: str = Header(default=""),
):
    _verify_header_token(
        token_name="GitLab webhook token",
        configured_token=GITLAB_TOKEN,
        provided_token=x_gitlab_token,
    )

    payload: dict = {}
    try:
        payload = await request.json()
    except ValueError as exc:
        logger.warning("Invalid GitLab webhook payload: %s", exc)

    object_kind = payload.get("object_kind", x_gitlab_event)
    project_ref = payload.get("project", {}).get("path_with_namespace", "unknown")
    pipeline_status = payload.get("object_attributes", {}).get("status", "")

    ev = _store_event(db, "gitlab", object_kind, payload, project_ref=project_ref)

    if object_kind == "pipeline" and pipeline_status == "success":
        ref = payload.get("object_attributes", {}).get("ref", "")
        background_tasks.add_task(_auto_trigger_on_ci_success, "gitlab", project_ref, ref, payload)

    return {"ok": True, "event_id": ev["id"], "event": object_kind, "project": project_ref}


# ─── Jenkins ─────────────────────────────────────────────────────────────────

@router.post("/webhook/jenkins")
async def jenkins_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_jenkins_token: str = Header(default=""),
):
    _verify_header_token(
        token_name="Jenkins webhook token",
        configured_token=JENKINS_TOKEN,
        provided_token=x_jenkins_token,
    )

    payload: dict = {}
    try:
        payload = await request.json()
    except ValueError as exc:
        logger.warning("Invalid Jenkins webhook payload: %s", exc)

    build_status = payload.get("build", {}).get("status", payload.get("status", ""))
    job_name = payload.get("name", payload.get("build", {}).get("full_url", "unknown"))

    ev = _store_event(db, "jenkins", "build", payload, project_ref=job_name)

    if build_status in ("SUCCESS", "success"):
        background_tasks.add_task(_auto_trigger_on_ci_success, "jenkins", job_name, "", payload)

    return {"ok": True, "event_id": ev["id"], "job": job_name, "status": build_status}


# ─── Events log ──────────────────────────────────────────────────────────────

@router.get("/events")
def list_events(
    source: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return _list_events(db, source=source, limit=limit)


# ─── Manual trigger ──────────────────────────────────────────────────────────

class TriggerIn(BaseModel):
    scenario_ids: list[str] = []
    tag: Optional[str] = None
    source: str = "cicd"
    ref: Optional[str] = None
    commit: Optional[str] = None


@router.post("/trigger/{project_id}")
async def trigger_tests(
    project_id: str,
    body: TriggerIn,
    x_ci_token: str = Header(default=""),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Trigger TestwrightAI test execution from external CI/CD pipeline."""
    # Strict mode: CICD_REQUIRE_TRIGGER_TOKEN=1 ama token tanimli degil
    if _ci_trigger_token_required() and not CI_TOKEN:
        raise HTTPException(503, "CI trigger token zorunlu ama yapilandirilmamis.")
    # CI token dogrulamasi
    if CI_TOKEN and not hmac.compare_digest(CI_TOKEN, x_ci_token):
        raise HTTPException(401, "Geçersiz CI token. X-CI-Token header'ını kontrol edin.")
    # CI token yoksa kullanici kimlik dogrulamasi zorunlu
    if not CI_TOKEN:
        if current_user is None:
            raise HTTPException(401, "Kimlik dogrulama gerekli")
        _require_project_access(db, current_user, project_id)
    import httpx
    payload = {
        "project_id": project_id,
        "scenario_ids": body.scenario_ids,
        "tag": body.tag,
        "triggered_by": body.source,
        "ref": body.ref,
        "commit": body.commit,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ENGINE_BASE}/api/run",
                json=payload,
                headers={"X-Internal-Key": ENGINE_KEY},
            )
            resp.raise_for_status()
            return {"triggered": True, "engine_response": resp.json()}
    except httpx.HTTPError as exc:
        logger.exception("CI trigger failed for project %s", project_id)
        return {"triggered": False, "error": str(exc)}
    except ValueError as exc:
        logger.exception("Engine returned invalid JSON for project %s", project_id)
        return {"triggered": False, "error": str(exc)}


# ─── Quality Gate ─────────────────────────────────────────────────────────────

class QualityGateRequest(BaseModel):
    gate_config: dict = {}          # overrides for thresholds
    execution_summary: dict         # {passed, failed, total, duration_s, ...}
    project: Optional[str] = ""
    run_url: Optional[str] = ""
    notify_emails: list[str] = []


@router.post("/quality-gate/evaluate")
async def evaluate_quality_gate(
    body: QualityGateRequest,
    background_tasks: BackgroundTasks,
    _current_user=Depends(get_current_user),
):
    """Verilen koşu özetini kalite kapısından geçirir."""
    from app.config import settings as app_settings
    from app.domains.cicd.quality_gate import build_gate_from_config

    # Varsayılan config + override birleştir
    default_cfg = {
        "name": body.gate_config.get("name", "Default Gate"),
        "min_pass_rate": body.gate_config.get("min_pass_rate", app_settings.qg_min_pass_rate),
        "max_failures":  body.gate_config.get("max_failures",  app_settings.qg_max_fail_count),
        "max_duration_s": body.gate_config.get("max_duration_s", app_settings.qg_max_duration_s),
    }
    if "max_new_flakies" in body.gate_config:
        default_cfg["max_new_flakies"] = body.gate_config["max_new_flakies"]
    if "min_coverage_pct" in body.gate_config:
        default_cfg["min_coverage_pct"] = body.gate_config["min_coverage_pct"]

    gate = build_gate_from_config(default_cfg)
    result = gate.evaluate(body.execution_summary)

    # E-posta bildirimi (arka planda)
    if body.notify_emails:
        background_tasks.add_task(
            _send_quality_gate_notification,
            emails=body.notify_emails,
            project=body.project or "Bilinmeyen Proje",
            gate_name=result.gate_name,
            result=result.result,
            checks=[c.to_dict() for c in result.checks],
            run_url=body.run_url or "",
        )

    return result.to_dict()


async def _send_quality_gate_notification(
    emails: list[str], project: str, gate_name: str,
    result: str, checks: list[dict], run_url: str
) -> None:
    from app.domains.notifications.email_service import notify_quality_gate
    notify_quality_gate(
        emails, project=project, gate_name=gate_name,
        result=result, checks=checks, run_url=run_url,
    )


# ─── Git Diff Impact Analysis ─────────────────────────────────────────────────

class ImpactAnalysisRequest(BaseModel):
    changed_files: list[str]
    branch: Optional[str] = None
    commit: Optional[str] = None
    limit: int = 50


@router.post("/impact-analysis/{project_id}")
async def impact_analysis(project_id: str, body: ImpactAnalysisRequest,
                           db: Session = Depends(get_db),
                           _current_user=Depends(get_current_user)):
    """Git diff'e göre hangi testlerin etkilendiğini hesaplar ve önceliklendirir."""
    _require_project_access(db, _current_user, project_id)
    from sqlalchemy import select
    from app.domains.tspm.models import TspmScenario, TspmExecutionResult, TspmExecution
    import statistics

    scenarios = list(db.execute(
        select(TspmScenario).where(TspmScenario.project_id == project_id)
    ).scalars().all())

    if not scenarios:
        return {"scenarios": [], "total": 0, "changed_files": body.changed_files}

    # Son 20 koşudan fail rate hesapla
    recent_execs = list(db.execute(
        select(TspmExecution)
        .where(TspmExecution.project_id == project_id)
        .order_by(TspmExecution.created_at.desc())
        .limit(20)
    ).scalars().all())

    fail_rates: dict[str, float] = {}
    durations: dict[str, list[float]] = {}

    for ex in recent_execs:
        results = list(db.execute(
            select(TspmExecutionResult).where(TspmExecutionResult.execution_id == ex.id)
        ).scalars().all())
        for r in results:
            sid = r.scenario_id
            if sid not in fail_rates:
                fail_rates[sid] = 0.0
                durations[sid] = []
            if r.status == "failed":
                fail_rates[sid] = fail_rates.get(sid, 0) + 1
            if r.duration_ms:
                durations[sid].append(r.duration_ms / 1000.0)

    # Normalize fail counts to rates
    total_runs = len(recent_execs) or 1
    for sid in fail_rates:
        fail_rates[sid] = round(fail_rates[sid] / total_runs, 3)

    # Compute impact score per scenario
    changed_lower = [f.lower() for f in body.changed_files]
    prioritized = []

    for sc in scenarios:
        score = 0.0
        tags = sc.tags or []
        tags_lower = " ".join(tags).lower()
        title_lower = sc.title.lower()

        # File name / keyword match
        file_match = any(
            any(kw in tags_lower or kw in title_lower for kw in _keywords_from_path(cf))
            for cf in changed_lower
        )
        if file_match:
            score += 0.45

        # Historical fail rate
        score += fail_rates.get(sc.id, 0) * 0.35

        # Avg duration (slow tests run first for fast feedback)
        dur_list = durations.get(sc.id, [])
        avg_dur = statistics.mean(dur_list) if dur_list else 0
        score += min(avg_dur / 120.0, 1.0) * 0.20

        prioritized.append({
            "id": sc.id,
            "title": sc.title,
            "tags": tags,
            "impact_score": round(score, 3),
            "file_match": file_match,
            "fail_rate": fail_rates.get(sc.id, 0),
            "avg_duration_s": round(avg_dur, 1),
            "priority": sc.priority if hasattr(sc, "priority") else "medium",
        })

    prioritized.sort(key=lambda x: x["impact_score"], reverse=True)

    return {
        "scenarios": prioritized[:body.limit],
        "total": len(prioritized),
        "changed_files": body.changed_files,
        "branch": body.branch,
        "commit": body.commit,
        "recommended_run_ids": [s["id"] for s in prioritized[:10] if s["impact_score"] > 0.2],
    }


def _keywords_from_path(file_path: str) -> list[str]:
    """Dosya yolundan anlamlı anahtar kelimeler çıkarır. Örn: src/auth/login.py → ['auth', 'login']"""
    import re
    parts = re.split(r"[/\\_\-.]", file_path.lower())
    skip = {"src", "test", "tests", "spec", "py", "ts", "js", "tsx", "jsx",
            "index", "main", "app", "utils", "helpers", "types", "models"}
    return [p for p in parts if p and len(p) > 2 and p not in skip]


# ─── Background task ─────────────────────────────────────────────────────────

async def _auto_trigger_on_ci_success(
    source: str, project_ref: str, ref: str, payload: dict
) -> None:
    """Auto-trigger smoke tests when CI pipeline succeeds."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(
                f"{ENGINE_BASE}/api/run",
                json={
                    "triggered_by": source,
                    "project_ref": project_ref,
                    "ref": ref,
                    "tag": "smoke",
                },
                headers={"X-Internal-Key": ENGINE_KEY},
            )
    except httpx.HTTPError:
        logger.exception(
            "Background CI auto-trigger failed for source %s and project %s",
            source,
            project_ref,
        )


# ─── Jenkins outbound integration ────────────────────────────────────────────
# Bağlantı yönetimi (URL + API token), test, job tetikleme, son build durumu.

from app.domains.cicd import jenkins_service as _jenkins_svc  # noqa: E402
from app.infra.models import User as _User  # noqa: E402


class JenkinsConnectionIn(BaseModel):
    name: str
    base_url: str
    username: str
    token: str


class JenkinsTriggerIn(BaseModel):
    job_name: str
    parameters: dict[str, str] = {}


def _tenant_of(user: _User) -> str:
    return getattr(user, "tenant_id", "") or "00000000-0000-0000-0000-000000000001"


@router.get("/jenkins/connections")
def jenkins_list_connections(
    db: Session = Depends(get_db),
    current_user: _User = Depends(get_current_user),
):
    return {"connections": _jenkins_svc.list_connections(db, _tenant_of(current_user))}


@router.post("/jenkins/connections", status_code=201)
def jenkins_create_connection(
    body: JenkinsConnectionIn,
    db: Session = Depends(get_db),
    current_user: _User = Depends(get_current_user),
):
    if not body.name.strip():
        raise HTTPException(400, "Bağlantı adı boş olamaz")
    if not body.base_url.lower().startswith(("http://", "https://")):
        raise HTTPException(400, "base_url http:// veya https:// ile başlamalı")
    try:
        conn = _jenkins_svc.create_connection(
            db,
            name=body.name.strip(),
            base_url=body.base_url.strip(),
            username=body.username.strip(),
            token=body.token,
            tenant_id=_tenant_of(current_user),
            owner_user_id=str(current_user.id),
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(409, "Bu isimde bir Jenkins bağlantısı zaten var") from exc
        logger.exception("Jenkins bağlantısı oluşturulamadı")
        raise HTTPException(500, "Bağlantı kaydedilemedi") from exc
    return conn


@router.delete("/jenkins/connections/{conn_id}", status_code=204)
def jenkins_delete_connection(
    conn_id: str,
    db: Session = Depends(get_db),
    current_user: _User = Depends(get_current_user),
):
    if not _jenkins_svc.delete_connection(db, conn_id, _tenant_of(current_user)):
        raise HTTPException(404, "Bağlantı bulunamadı")
    return None


@router.post("/jenkins/connections/{conn_id}/test")
async def jenkins_test_connection(
    conn_id: str,
    db: Session = Depends(get_db),
    current_user: _User = Depends(get_current_user),
):
    return await _jenkins_svc.test_connection(db, conn_id, _tenant_of(current_user))


@router.post("/jenkins/connections/{conn_id}/build")
async def jenkins_trigger_build_endpoint(
    conn_id: str,
    body: JenkinsTriggerIn,
    db: Session = Depends(get_db),
    current_user: _User = Depends(get_current_user),
):
    if not body.job_name.strip():
        raise HTTPException(400, "job_name zorunlu")
    return await _jenkins_svc.trigger_build(
        db,
        conn_id,
        _tenant_of(current_user),
        body.job_name.strip(),
        body.parameters or None,
    )


@router.get("/jenkins/connections/{conn_id}/jobs/{job_name}/last-build")
async def jenkins_last_build(
    conn_id: str,
    job_name: str,
    db: Session = Depends(get_db),
    current_user: _User = Depends(get_current_user),
):
    return await _jenkins_svc.last_build(
        db, conn_id, _tenant_of(current_user), job_name
    )
