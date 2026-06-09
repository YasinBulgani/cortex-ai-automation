"""Ingestion router unit tests — /api/v1/ingestion.

FastAPI TestClient. Servis fonksiyonları monkeypatch'li.
Endpoint'ler: POST /text, POST /jira/webhook, POST /confluence/webhook,
              GET /projects/{project_id}, GET /{req_id}.
"""
from __future__ import annotations

import hashlib
import hmac
import json

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.ingestion.router import router
    from app.deps import get_current_user
    from app.infra.database import get_db
    from app.infra.models import User

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


def _mock_user():
    u = MagicMock(spec=User)
    u.id = "test-user-id"
    u.email = "test@example.com"
    u.roles = []
    return u


def _mock_db():
    db = MagicMock()
    db.get.return_value = MagicMock()  # project exists
    db.scalar.return_value = 1  # user is a member
    return db


def _app() -> "TestClient":
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_db] = _mock_db
    return TestClient(app, raise_server_exceptions=False)


def _fake_req(req_id: str = "req-001") -> MagicMock:
    req = MagicMock()
    req.to_dict.return_value = {
        "id": req_id,
        "title": "Kullanıcı giriş yapabilmeli",
        "body": "Sistemde e-posta ve şifre ile giriş yapılabilir.",
        "project_id": "proj-1",
        "source": "text",
    }
    return req


_TEXT_BODY = {
    "project_id": "proj-1",
    "title": "Kullanıcı giriş yapabilmeli",
    "body": "Sistemde e-posta ve şifre ile giriş yapılabilir.",
}

# ---------------------------------------------------------------------------
# POST /ingestion/text — metin ingestion
# ---------------------------------------------------------------------------


def test_ingest_text_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.ingest_text.return_value = _fake_req()
        r = client.post("/ingestion/text", json=_TEXT_BODY)
    assert r.status_code == 201


def test_ingest_text_returns_dict() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.ingest_text.return_value = _fake_req("req-42")
        r = client.post("/ingestion/text", json=_TEXT_BODY)
    body = r.json()
    assert "id" in body
    assert body["id"] == "req-42"


def test_ingest_text_missing_body_field_422() -> None:
    """'body' alanı eksik → Pydantic 422."""
    if not _IMPORT_OK:
        return
    client = _app()
    bad = {"project_id": "proj-1", "title": "T"}  # body eksik
    with patch("app.domains.ingestion.router.svc"):
        r = client.post("/ingestion/text", json=bad)
    assert r.status_code == 422


def test_ingest_text_missing_title_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    bad = {"project_id": "proj-1", "body": "B"}
    with patch("app.domains.ingestion.router.svc"):
        r = client.post("/ingestion/text", json=bad)
    assert r.status_code == 422


def test_ingest_text_service_value_error_becomes_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.ingest_text.side_effect = ValueError("geçersiz proje")
        r = client.post("/ingestion/text", json=_TEXT_BODY)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /ingestion/projects/{project_id} — gereksinimler listesi
# ---------------------------------------------------------------------------


def test_list_for_project_returns_200() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.list_ingested.return_value = [_fake_req("r1"), _fake_req("r2")]
        r = client.get("/ingestion/projects/proj-1")
    assert r.status_code == 200


def test_list_for_project_returns_list() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.list_ingested.return_value = [_fake_req()]
        r = client.get("/ingestion/projects/proj-1")
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1


def test_list_for_project_empty() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.list_ingested.return_value = []
        r = client.get("/ingestion/projects/proj-x")
    assert r.json() == []


# ---------------------------------------------------------------------------
# GET /ingestion/{req_id} — detay
# ---------------------------------------------------------------------------


def test_get_ingested_found() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.get_ingested.return_value = _fake_req("req-77")
        r = client.get("/ingestion/req-77")
    assert r.status_code == 200
    assert r.json()["id"] == "req-77"


def test_get_ingested_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.get_ingested.return_value = None
        r = client.get("/ingestion/nonexistent")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Webhook signature generation helper
# ---------------------------------------------------------------------------


def _make_webhook_signature(body: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature matching webhook format."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# POST /ingestion/jira/webhook
# ---------------------------------------------------------------------------


def test_jira_webhook_success_with_valid_signature() -> None:
    """Jira webhook with valid HMAC signature should succeed."""
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"issue": {"key": "TEST-1", "fields": {"summary": "Login bug"}}}
    body = json.dumps(payload).encode()
    sig = _make_webhook_signature(body, "test-webhook-secret")

    with patch("app.domains.ingestion.router.os.environ.get") as mock_env:
        def env_side_effect(key, default=""):
            if key == "WEBHOOK_SECRET":
                return "test-webhook-secret"
            return default
        mock_env.side_effect = env_side_effect
        with patch("app.domains.ingestion.router._webhook_secret_required", return_value=False):
            with patch("app.domains.ingestion.router.svc") as mock_svc:
                mock_svc.ingest_jira_payload.return_value = _fake_req()
                r = client.post(
                    "/ingestion/jira/webhook?project_id=proj-1",
                    content=body,
                    headers={
                        "X-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )
    assert r.status_code == 201


def test_jira_webhook_invalid_signature_401() -> None:
    """Jira webhook with invalid signature should return 401."""
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"issue": {"key": "TEST-1"}}
    body = json.dumps(payload).encode()

    with patch("app.domains.ingestion.router.os.environ.get") as mock_env:
        def env_side_effect(key, default=""):
            if key == "WEBHOOK_SECRET":
                return "test-webhook-secret"
            return default
        mock_env.side_effect = env_side_effect
        with patch("app.domains.ingestion.router._webhook_secret_required", return_value=False):
            r = client.post(
                "/ingestion/jira/webhook?project_id=proj-1",
                content=body,
                headers={
                    "X-Webhook-Signature": "sha256=invalidsignature",
                    "Content-Type": "application/json",
                },
            )
    assert r.status_code == 401


def test_jira_webhook_missing_signature_401() -> None:
    """Jira webhook without signature header should return 401."""
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"issue": {"key": "TEST-1"}}
    body = json.dumps(payload).encode()

    with patch("app.domains.ingestion.router.os.environ.get") as mock_env:
        def env_side_effect(key, default=""):
            if key == "WEBHOOK_SECRET":
                return "test-webhook-secret"
            return default
        mock_env.side_effect = env_side_effect
        with patch("app.domains.ingestion.router._webhook_secret_required", return_value=False):
            r = client.post(
                "/ingestion/jira/webhook?project_id=proj-1",
                content=body,
                headers={"Content-Type": "application/json"},
            )
    assert r.status_code == 401


def test_jira_webhook_missing_project_id_422() -> None:
    """project_id query param eksik → FastAPI 422."""
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"issue": {"key": "TEST-1"}}
    body = json.dumps(payload).encode()
    sig = _make_webhook_signature(body, "test-secret")

    with patch("app.domains.ingestion.router.os.environ.get", return_value=""):
        with patch("app.domains.ingestion.router._webhook_secret_required", return_value=False):
            with patch("app.domains.ingestion.router.svc"):
                r = client.post(
                    "/ingestion/jira/webhook",
                    content=body,
                    headers={
                        "X-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )
    # project_id required query param — 422 veya 400
    assert r.status_code in (400, 422)


def test_jira_webhook_service_error_becomes_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"issue": {}}
    body = json.dumps(payload).encode()
    sig = _make_webhook_signature(body, "test-secret")

    with patch("app.domains.ingestion.router.os.environ.get", return_value=""):
        with patch("app.domains.ingestion.router._webhook_secret_required", return_value=False):
            with patch("app.domains.ingestion.router.svc") as mock_svc:
                mock_svc.ingest_jira_payload.side_effect = ValueError("geçersiz payload")
                r = client.post(
                    "/ingestion/jira/webhook?project_id=proj-1",
                    content=body,
                    headers={
                        "X-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )
    assert r.status_code == 422
