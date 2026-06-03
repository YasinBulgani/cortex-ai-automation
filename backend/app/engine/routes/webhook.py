"""
Webhook routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/webhook_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/webhook.py — APIRouter, port 8000 (consolidated)

Endpointler:
  POST /api/webhooks/github   — GitHub PR & push eventleri
  POST /api/webhooks/gitlab   — GitLab MR & push eventleri
  POST /api/webhooks/generic  — Genel webhook (herhangi bir CI)
  GET  /api/webhooks/events   — Son webhook olayları (log)
  GET  /api/webhooks/config   — Webhook URL'leri ve ayarları
  PUT  /api/webhooks/config   — Webhook ayarlarını güncelle
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["engine", "webhooks"])

_EVENTS_FILE = Path(__file__).parent.parent.parent.parent.parent / "engine" / "data" / "webhook_events.json"
_CONFIG_FILE = Path(__file__).parent.parent.parent.parent.parent / "engine" / "data" / "webhook_config.json"
_MAX_EVENTS = 100

_DEFAULT_CONFIG: dict[str, Any] = {
    "github_secret": "",
    "github_token": "",
    "auto_run_on_pr": True,
    "auto_run_on_push": False,
    "run_browser": "chromium",
    "smoke_markers": "smoke",
    "notify_pr": True,
    "allowed_repos": [],
}


# ─── Schemas ─────────────────────────────────────────────────────────────────

class WebhookConfigUpdate(BaseModel):
    auto_run_on_pr: Optional[bool] = None
    auto_run_on_push: Optional[bool] = None
    run_browser: Optional[str] = None
    smoke_markers: Optional[str] = None
    notify_pr: Optional[bool] = None
    allowed_repos: Optional[list[str]] = None
    github_secret: Optional[str] = None
    github_token: Optional[str] = None


class GenericWebhookPayload(BaseModel):
    markers: str = Field(default="smoke")
    feature_path: str = Field(default="")
    browser: str = Field(default="chromium")


class WebhookEventOut(BaseModel):
    id: str
    source: str
    event_type: str
    received_at: str
    processed: bool
    run_id: Optional[str] = None


class EventsResponse(BaseModel):
    ok: bool
    events: list[dict]
    total: int


class WebhookResponse(BaseModel):
    ok: bool
    event_id: str
    status: str
    reason: Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _webhook_secret_required() -> bool:
    app_env = os.environ.get("APP_ENV", "development").lower()
    forced = os.environ.get("WEBHOOK_REQUIRE_SECRETS", "").lower() in {"1", "true", "yes"}
    return forced or app_env in {"production", "prod", "staging"}


def _internal_headers() -> dict[str, str]:
    internal_key = os.environ.get("ENGINE_INTERNAL_KEY", "").strip()
    if not internal_key:
        return {}
    return {"X-Internal-Key": internal_key}


def _load_events() -> list[dict]:
    try:
        if _EVENTS_FILE.exists():
            return json.loads(_EVENTS_FILE.read_text())
    except Exception:
        pass
    return []


def _save_event(event: dict) -> None:
    try:
        _EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        events = _load_events()
        events.insert(0, event)
        _EVENTS_FILE.write_text(json.dumps(events[:_MAX_EVENTS], ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error("Event kaydetme hatası: %s", e)


def _load_config() -> dict:
    try:
        if _CONFIG_FILE.exists():
            saved = json.loads(_CONFIG_FILE.read_text())
            return {**_DEFAULT_CONFIG, **saved}
    except Exception:
        pass
    cfg = dict(_DEFAULT_CONFIG)
    cfg["github_secret"] = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    cfg["github_token"] = os.environ.get("GITHUB_TOKEN", "")
    return cfg


def _save_config(cfg: dict) -> None:
    try:
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error("Config kaydetme hatası: %s", e)


def _verify_github_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return not _webhook_secret_required()
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _trigger_tests_async(
    event_id: str,
    changed_files: list[str],
    markers: str,
    browser: str,
    pr_url: str = "",
    config: dict | None = None,
) -> None:
    """Background thread'de test koşusunu tetikler."""
    try:
        import requests as req_lib

        impact_resp = req_lib.post(
            "http://127.0.0.1:5001/api/ai/impact-analysis",
            json={"changed_files": changed_files},
            headers=_internal_headers(),
            timeout=30,
        )
        impact = impact_resp.json() if impact_resp.ok else {}
        matched = impact.get("matched_tests", [])
        risk = impact.get("ai_analysis", {}).get("risk_level", "medium")

        logger.info("Webhook %s: %d eşleşen test, risk=%s", event_id, len(matched), risk)

        run_payload: dict[str, Any] = {"markers": markers, "browser": browser}
        if matched:
            run_payload["features_list"] = matched[:10]

        run_resp = req_lib.post(
            "http://127.0.0.1:5001/api/run",
            json=run_payload,
            headers=_internal_headers(),
            timeout=10,
        )
        run_id = run_resp.json().get("run_id", "unknown")

        cfg = config or _load_config()
        if pr_url and cfg.get("github_token") and cfg.get("notify_pr"):
            _post_github_pr_comment(pr_url, run_id, matched, risk, cfg["github_token"])

        events = _load_events()
        for ev in events:
            if ev.get("id") == event_id:
                ev["run_id"] = run_id
                ev["matched_tests"] = matched
                ev["risk_level"] = risk
                ev["processed"] = True
                break
        if _EVENTS_FILE.exists():
            _EVENTS_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error("Webhook test tetikleme hatası: %s", e)


def _post_github_pr_comment(
    pr_api_url: str, run_id: str, matched_tests: list, risk: str, token: str
) -> None:
    """PR'a test sonucu yorumu ekler."""
    try:
        import requests as req_lib

        comment_url = pr_api_url.replace("/pulls/", "/issues/") + "/comments"
        risk_label = {"low": "[LOW]", "medium": "[MEDIUM]", "high": "[HIGH]"}.get(risk, "[UNKNOWN]")
        body = (
            f"## Neurex Otomatik Test Analizi\n\n"
            f"Risk Seviyesi: {risk_label} {risk.upper()}\n"
            f"Etkilenen Test Sayisi: {len(matched_tests)}\n"
            f"Kosu ID: `{run_id}`\n\n"
            f"Etkilenen Testler:\n"
            + "\n".join(f"- `{t}`" for t in matched_tests[:5])
            or "- Esleşen test bulunamadi"
        )
        req_lib.post(
            comment_url,
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            json={"body": body},
            timeout=10,
        )
    except Exception as e:
        logger.warning("GitHub PR yorum hatası: %s", e)


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/github", response_model=WebhookResponse)
async def github_webhook(
    request: Request,
    x_hub_signature_256: Annotated[str, Header(alias="X-Hub-Signature-256")] = "",
    x_github_event: Annotated[str, Header(alias="X-GitHub-Event")] = "unknown",
):
    """GitHub PR ve push webhook'larını alır, etkilenen testleri async olarak çalıştırır."""
    cfg = _load_config()
    payload_bytes = await request.body()

    if _webhook_secret_required() and not cfg.get("github_secret"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="github_secret zorunlu fakat ayarlanmamis",
        )
    if cfg.get("github_secret") and not _verify_github_signature(
        payload_bytes, x_hub_signature_256, cfg["github_secret"]
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    payload: dict = await request.json() or {}
    repo = payload.get("repository", {}).get("full_name", "unknown")
    event_id = f"gh_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    event: dict[str, Any] = {
        "id": event_id,
        "source": "github",
        "event_type": x_github_event,
        "repo": repo,
        "received_at": datetime.now().isoformat(),
        "processed": False,
        "run_id": None,
    }

    changed_files: list[str] = []
    pr_url = ""
    should_run = False

    if x_github_event == "pull_request" and cfg.get("auto_run_on_pr", True):
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            pr = payload.get("pull_request", {})
            changed_files = [f.get("filename", "") for f in payload.get("files", [])]
            pr_url = pr.get("url", "")
            event["pr_number"] = pr.get("number")
            event["pr_title"] = pr.get("title", "")
            event["branch"] = pr.get("head", {}).get("ref", "")
            should_run = True

    elif x_github_event == "push" and cfg.get("auto_run_on_push", False):
        commits = payload.get("commits", [])
        for c in commits:
            changed_files.extend(c.get("added", []) + c.get("modified", []))
        event["branch"] = payload.get("ref", "").replace("refs/heads/", "")
        should_run = bool(changed_files)

    _save_event(event)

    if should_run:
        threading.Thread(
            target=_trigger_tests_async,
            args=(
                event_id,
                changed_files,
                cfg.get("smoke_markers", "smoke"),
                cfg.get("run_browser", "chromium"),
                pr_url,
                cfg,
            ),
            daemon=True,
        ).start()
        return {"ok": True, "event_id": event_id, "status": "queued"}

    return {
        "ok": True,
        "event_id": event_id,
        "status": "skipped",
        "reason": f"event_type={x_github_event} için auto_run devre dışı",
    }


@router.post("/gitlab", response_model=WebhookResponse)
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: Annotated[str, Header(alias="X-Gitlab-Token")] = "",
    x_gitlab_event: Annotated[str, Header(alias="X-Gitlab-Event")] = "",
):
    """GitLab MR ve push webhook'larını alır."""
    cfg = _load_config()
    expected_token = os.environ.get("GITLAB_WEBHOOK_TOKEN", "").strip()

    if _webhook_secret_required() and not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GITLAB_WEBHOOK_TOKEN zorunlu fakat ayarlanmamis",
        )
    if expected_token and not hmac.compare_digest(x_gitlab_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitLab token")

    payload: dict = await request.json() or {}
    event_type = x_gitlab_event or payload.get("object_kind", "unknown")
    repo = payload.get("project", {}).get("path_with_namespace", "unknown")
    event_id = f"gl_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    event: dict[str, Any] = {
        "id": event_id,
        "source": "gitlab",
        "event_type": event_type,
        "repo": repo,
        "received_at": datetime.now().isoformat(),
        "processed": False,
        "run_id": None,
    }
    _save_event(event)

    changed_files: list[str] = []
    should_run = False

    if event_type in ("Merge Request Hook", "merge_request") and cfg.get("auto_run_on_pr", True):
        mr = payload.get("object_attributes", {})
        if mr.get("action") in ("open", "update", "reopen"):
            event["mr_title"] = mr.get("title", "")
            event["branch"] = mr.get("source_branch", "")
            should_run = True

    elif event_type in ("Push Hook", "push") and cfg.get("auto_run_on_push", False):
        commits = payload.get("commits", [])
        for c in commits:
            changed_files.extend(c.get("added", []) + c.get("modified", []))
        should_run = bool(changed_files)

    if should_run:
        threading.Thread(
            target=_trigger_tests_async,
            args=(
                event_id,
                changed_files,
                cfg.get("smoke_markers", "smoke"),
                cfg.get("run_browser", "chromium"),
            ),
            daemon=True,
        ).start()
        return {"ok": True, "event_id": event_id, "status": "queued"}

    return {"ok": True, "event_id": event_id, "status": "skipped"}


@router.post("/generic", response_model=WebhookResponse)
async def generic_webhook(
    body: GenericWebhookPayload,
    x_webhook_token: Annotated[str, Header(alias="X-Webhook-Token")] = "",
):
    """Genel CI/CD webhook'u — markers, feature_path ve browser alır."""
    expected_token = os.environ.get("GENERIC_WEBHOOK_TOKEN", "").strip()

    if _webhook_secret_required() and not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GENERIC_WEBHOOK_TOKEN zorunlu fakat ayarlanmamis",
        )
    if expected_token and not hmac.compare_digest(x_webhook_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook token")

    event_id = f"gen_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    _save_event({
        "id": event_id,
        "source": "generic",
        "event_type": "manual",
        "received_at": datetime.now().isoformat(),
        "processed": False,
    })

    def _run() -> None:
        try:
            import requests as req_lib

            run_body: dict[str, Any] = {"markers": body.markers, "browser": body.browser}
            if body.feature_path:
                run_body["feature"] = body.feature_path
            req_lib.post(
                "http://127.0.0.1:5001/api/run",
                json=run_body,
                headers=_internal_headers(),
                timeout=10,
            )
        except Exception as e:
            logger.error("Generic webhook run hatası: %s", e)

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "event_id": event_id, "status": "queued"}


@router.get("/events", response_model=EventsResponse)
def get_events(
    limit: int = Query(default=20, ge=1, le=_MAX_EVENTS),
    source: Optional[str] = Query(default=None),
):
    """Son webhook olaylarını döndürür. source filtresi: github | gitlab | generic."""
    events = _load_events()
    if source:
        events = [e for e in events if e.get("source") == source]
    return {"ok": True, "events": events[:limit], "total": len(events)}


@router.get("/config")
def get_config() -> dict:
    """Webhook ayarlarını döndürür. Hassas alanlar maskelenir."""
    cfg = _load_config()
    safe = dict(cfg)
    if safe.get("github_token"):
        safe["github_token"] = safe["github_token"][:4] + "****" + safe["github_token"][-4:]
    if safe.get("github_secret"):
        safe["github_secret"] = "****"
    return safe


@router.put("/config")
def update_config(data: WebhookConfigUpdate) -> dict:
    """Webhook ayarlarını günceller. Hassas alanlar yalnızca boş değilse yazılır."""
    cfg = _load_config()
    update_data = data.model_dump(exclude_none=True)

    updatable = ("auto_run_on_pr", "auto_run_on_push", "run_browser", "smoke_markers", "notify_pr", "allowed_repos")
    for key in updatable:
        if key in update_data:
            cfg[key] = update_data[key]

    for key in ("github_secret", "github_token"):
        val = update_data.get(key)
        if val and val != "****":
            cfg[key] = val

    _save_config(cfg)
    return {"ok": True}
