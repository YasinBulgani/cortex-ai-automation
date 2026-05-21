"""
GitHub / GitLab / Generic Webhook Handler

Endpointler:
  POST /api/webhooks/github          — GitHub PR & push eventleri
  POST /api/webhooks/gitlab          — GitLab MR & push eventleri
  POST /api/webhooks/generic         — Genel webhook (herhangi bir CI)
  GET  /api/webhooks/events          — Son webhook olayları (log)
  GET  /api/webhooks/config          — Webhook URL'leri ve ayarları
  PUT  /api/webhooks/config          — Webhook ayarlarını güncelle

GitHub entegrasyonu:
  - PR açıldığında / güncellendiğinde → etkilenen testleri analiz et → smoke çalıştır
  - Push'ta → impact analysis → ilgili testleri çalıştır
  - Sonucu PR'a GitHub Checks API ile geri yaz (token gerektirir)
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

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

webhook_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")

_EVENTS_FILE = Path(__file__).parent.parent / "data" / "webhook_events.json"
_CONFIG_FILE = Path(__file__).parent.parent / "data" / "webhook_config.json"
_MAX_EVENTS = 100

_DEFAULT_CONFIG = {
    "github_secret": "",
    "github_token": "",
    "auto_run_on_pr": True,
    "auto_run_on_push": False,
    "run_browser": "chromium",
    "smoke_markers": "smoke",
    "notify_pr": True,
    "allowed_repos": [],
}


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


def _trigger_tests_async(event_id: str, changed_files: list[str], markers: str, browser: str, pr_url: str = "", config: dict | None = None) -> None:
    """Background thread'de test koşusunu tetikler."""
    try:
        import requests as req_lib

        # Impact analysis
        impact_resp = req_lib.post(
            "http://127.0.0.1:5001/api/ai/impact-analysis",
            json={"changed_files": changed_files},
            headers=_internal_headers(),
            timeout=30
        )
        impact = impact_resp.json() if impact_resp.ok else {}
        matched = impact.get("matched_tests", [])
        risk = impact.get("ai_analysis", {}).get("risk_level", "medium")

        logger.info("Webhook %s: %d eşleşen test, risk=%s", event_id, len(matched), risk)

        # Test koşusunu başlat
        run_payload = {"markers": markers, "browser": browser}
        if matched:
            run_payload["features_list"] = matched[:10]

        run_resp = req_lib.post(
            "http://127.0.0.1:5001/api/run",
            json=run_payload,
            headers=_internal_headers(),
            timeout=10
        )
        run_id = run_resp.json().get("run_id", "unknown")

        # PR'a yorum gönder (GitHub token varsa)
        cfg = config or _load_config()
        if pr_url and cfg.get("github_token") and cfg.get("notify_pr"):
            _post_github_pr_comment(pr_url, run_id, matched, risk, cfg["github_token"])

        # Olayı güncelle
        events = _load_events()
        for ev in events:
            if ev.get("id") == event_id:
                ev["run_id"] = run_id
                ev["matched_tests"] = matched
                ev["risk_level"] = risk
                ev["processed"] = True
                break
        _EVENTS_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error("Webhook test tetikleme hatası: %s", e)


def _post_github_pr_comment(pr_api_url: str, run_id: str, matched_tests: list, risk: str, token: str) -> None:
    """PR'a test sonucu yorumu ekler."""
    try:
        import requests as req_lib
        comment_url = pr_api_url.replace("/pulls/", "/issues/") + "/comments"
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
        body = f"""## 🤖 TestwrightAI Otomatik Test Analizi

{risk_emoji} **Risk Seviyesi:** {risk.upper()}
📋 **Etkilenen Test Sayısı:** {len(matched_tests)}
🔑 **Koşu ID:** `{run_id}`

**Etkilenen Testler:**
{chr(10).join(f"- `{t}`" for t in matched_tests[:5]) or "- Eşleşen test bulunamadı"}

[TestwrightAI Dashboard'da görüntüle](http://localhost:3000)
"""
        req_lib.post(
            comment_url,
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            json={"body": body},
            timeout=10
        )
    except Exception as e:
        logger.warning("GitHub PR yorum hatası: %s", e)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@webhook_bp.route("/github", methods=["POST"])
def github_webhook():
    cfg = _load_config()
    payload_bytes = request.get_data()

    # Signature doğrulama
    if _webhook_secret_required() and not cfg.get("github_secret"):
        return jsonify({"error": "github_secret zorunlu fakat ayarlanmamis"}), 503
    sig = request.headers.get("X-Hub-Signature-256", "")
    if cfg.get("github_secret") and not _verify_github_signature(payload_bytes, sig, cfg["github_secret"]):
        return jsonify({"error": "Invalid signature"}), 401

    event_type = request.headers.get("X-GitHub-Event", "unknown")
    payload = request.get_json(force=True) or {}

    repo = payload.get("repository", {}).get("full_name", "unknown")
    event_id = f"gh_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    event = {
        "id": event_id,
        "source": "github",
        "event_type": event_type,
        "repo": repo,
        "received_at": datetime.now().isoformat(),
        "processed": False,
        "run_id": None,
    }

    changed_files: list[str] = []
    pr_url = ""
    should_run = False

    if event_type == "pull_request" and cfg.get("auto_run_on_pr", True):
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            pr = payload.get("pull_request", {})
            changed_files = [f.get("filename", "") for f in payload.get("files", [])]
            pr_url = pr.get("url", "")
            event["pr_number"] = pr.get("number")
            event["pr_title"] = pr.get("title", "")
            event["branch"] = pr.get("head", {}).get("ref", "")
            should_run = True

    elif event_type == "push" and cfg.get("auto_run_on_push", False):
        commits = payload.get("commits", [])
        for c in commits:
            changed_files.extend(c.get("added", []) + c.get("modified", []))
        event["branch"] = payload.get("ref", "").replace("refs/heads/", "")
        should_run = bool(changed_files)

    _save_event(event)

    if should_run:
        threading.Thread(
            target=_trigger_tests_async,
            args=(event_id, changed_files, cfg.get("smoke_markers", "smoke"), cfg.get("run_browser", "chromium"), pr_url, cfg),
            daemon=True
        ).start()
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    return jsonify({"ok": True, "event_id": event_id, "status": "skipped", "reason": f"event_type={event_type} için auto_run devre dışı"})


@webhook_bp.route("/gitlab", methods=["POST"])
def gitlab_webhook():
    token = request.headers.get("X-Gitlab-Token", "")
    cfg = _load_config()
    expected_token = os.environ.get("GITLAB_WEBHOOK_TOKEN", "").strip()
    if _webhook_secret_required() and not expected_token:
        return jsonify({"error": "GITLAB_WEBHOOK_TOKEN zorunlu fakat ayarlanmamis"}), 503
    if expected_token and not hmac.compare_digest(token, expected_token):
        return jsonify({"error": "Invalid GitLab token"}), 401

    payload = request.get_json(force=True) or {}
    event_type = request.headers.get("X-Gitlab-Event", payload.get("object_kind", "unknown"))
    repo = payload.get("project", {}).get("path_with_namespace", "unknown")
    event_id = f"gl_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    event = {
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
            args=(event_id, changed_files, cfg.get("smoke_markers", "smoke"), cfg.get("run_browser", "chromium")),
            daemon=True
        ).start()
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    return jsonify({"ok": True, "event_id": event_id, "status": "skipped"})


@webhook_bp.route("/generic", methods=["POST"])
def generic_webhook():
    expected_token = os.environ.get("GENERIC_WEBHOOK_TOKEN", "").strip()
    provided_token = request.headers.get("X-Webhook-Token", "")
    if _webhook_secret_required() and not expected_token:
        return jsonify({"error": "GENERIC_WEBHOOK_TOKEN zorunlu fakat ayarlanmamis"}), 503
    if expected_token and not hmac.compare_digest(provided_token, expected_token):
        return jsonify({"error": "Invalid webhook token"}), 401

    payload = request.get_json(force=True) or {}
    event_id = f"gen_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    markers = payload.get("markers", "smoke")
    feature = payload.get("feature_path", "")
    browser = payload.get("browser", "chromium")

    _save_event({
        "id": event_id,
        "source": "generic",
        "event_type": "manual",
        "received_at": datetime.now().isoformat(),
        "processed": False,
    })

    def _run():
        try:
            import requests as req_lib
            body = {"markers": markers, "browser": browser}
            if feature:
                body["feature"] = feature
            req_lib.post(
                "http://127.0.0.1:5001/api/run",
                json=body,
                headers=_internal_headers(),
                timeout=10,
            )
        except Exception as e:
            logger.error("Generic webhook run hatası: %s", e)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "event_id": event_id, "status": "queued"})


@webhook_bp.route("/events", methods=["GET"])
def get_events():
    limit = int(request.args.get("limit", 20))
    source = request.args.get("source")
    events = _load_events()
    if source:
        events = [e for e in events if e.get("source") == source]
    return jsonify({"ok": True, "events": events[:limit], "total": len(events)})


@webhook_bp.route("/config", methods=["GET"])
def get_config():
    cfg = _load_config()
    # Token'ı maskeliyerek döndür
    safe = dict(cfg)
    if safe.get("github_token"):
        safe["github_token"] = safe["github_token"][:4] + "****" + safe["github_token"][-4:]
    if safe.get("github_secret"):
        safe["github_secret"] = "****"
    return jsonify(safe)


@webhook_bp.route("/config", methods=["PUT"])
def update_config():
    data = request.json or {}
    cfg = _load_config()
    updatable = ("auto_run_on_pr", "auto_run_on_push", "run_browser", "smoke_markers", "notify_pr", "allowed_repos")
    for key in updatable:
        if key in data:
            cfg[key] = data[key]
    # Hassas alanlar sadece boş değilse güncelle
    for key in ("github_secret", "github_token"):
        if data.get(key) and data[key] != "****":
            cfg[key] = data[key]
    _save_config(cfg)
    return jsonify({"ok": True})
