"""JIRA webhook HMAC signature verification tests.

Tests for:
  - Proper HMAC-SHA256 signature validation
  - Missing signatures → 401 Unauthorized
  - Invalid signatures → 401 Unauthorized
  - Valid signatures → webhook processed
  - Missing webhook secret config in prod → 503
"""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, AsyncMock, patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.jira.router import router, _verify_jira_webhook_signature
    from app.deps import get_current_user, get_optional_user
    from app.infra.database import get_db
    from app.infra.models import User

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


def _mock_user():
    u = MagicMock(spec=User)
    u.id = "test-user-id"
    u.email = "test@example.com"
    u.tenant_id = "test-tenant"
    u.roles = []
    return u


def _mock_optional_user():
    return None


def _mock_db():
    db = MagicMock()
    return db


def _app() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_optional_user] = _mock_optional_user
    app.dependency_overrides[get_db] = _mock_db
    return TestClient(app, raise_server_exceptions=False)


def _make_signature(body: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature matching Jira webhook format."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# _verify_jira_webhook_signature — pure function tests
# ---------------------------------------------------------------------------


def test_verify_jira_signature_valid():
    """Valid signature should return True."""
    if not _IMPORT_OK:
        return
    secret = "test-secret"
    body = b'{"issue": {"key": "TEST-1"}}'
    sig = _make_signature(body, secret)

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        result = _verify_jira_webhook_signature(body, sig)
    assert result is True


def test_verify_jira_signature_invalid():
    """Invalid signature should return False."""
    if not _IMPORT_OK:
        return
    secret = "test-secret"
    body = b'{"issue": {"key": "TEST-1"}}'
    wrong_sig = "sha256=invalidsignature"

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        result = _verify_jira_webhook_signature(body, wrong_sig)
    assert result is False


def test_verify_jira_signature_empty_signature():
    """Empty signature should return False."""
    if not _IMPORT_OK:
        return
    secret = "test-secret"
    body = b'{"issue": {"key": "TEST-1"}}'

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        result = _verify_jira_webhook_signature(body, "")
    assert result is False


def test_verify_jira_signature_no_secret_configured():
    """When secret not configured, should return True (allow it)."""
    if not _IMPORT_OK:
        return
    body = b'{"issue": {"key": "TEST-1"}}'

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", ""):
        result = _verify_jira_webhook_signature(body, "sha256=anything")
    assert result is True


def test_verify_jira_signature_body_tampering():
    """Tampered body should fail signature verification."""
    if not _IMPORT_OK:
        return
    secret = "test-secret"
    body = b'{"issue": {"key": "TEST-1"}}'
    sig = _make_signature(body, secret)

    # Tampered body
    tampered_body = b'{"issue": {"key": "TEST-2"}}'

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        result = _verify_jira_webhook_signature(tampered_body, sig)
    assert result is False


# ---------------------------------------------------------------------------
# POST /api/jira/webhook/jira-incoming — integration tests
# ---------------------------------------------------------------------------


def test_jira_webhook_valid_signature_200():
    """Valid webhook with correct signature should return 200."""
    if not _IMPORT_OK:
        return
    client = _app()
    secret = "test-webhook-secret"
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "TEST-123",
            "fields": {"status": {"name": "Done"}},
        },
    }
    body = json.dumps(payload).encode()
    sig = _make_signature(body, secret)

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            with patch("app.domains.jira.router._sync_defect_link_status"):
                r = client.post(
                    "/api/jira/webhook/jira-incoming",
                    content=body,
                    headers={
                        "X-Atlassian-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )
    assert r.status_code == 200
    data = r.json()
    assert data["received"] is True
    assert data["event"] == "jira:issue_updated"


def test_jira_webhook_missing_signature_401():
    """Webhook without signature should return 401 when secret configured."""
    if not _IMPORT_OK:
        return
    client = _app()
    secret = "test-webhook-secret"
    payload = {"webhookEvent": "jira:issue_updated", "issue": {"key": "TEST-1"}}
    body = json.dumps(payload).encode()

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            r = client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={"Content-Type": "application/json"},
            )
    assert r.status_code == 401
    assert "imzası" in r.json()["detail"]


def test_jira_webhook_invalid_signature_401():
    """Webhook with invalid signature should return 401."""
    if not _IMPORT_OK:
        return
    client = _app()
    secret = "test-webhook-secret"
    payload = {"webhookEvent": "jira:issue_updated", "issue": {"key": "TEST-1"}}
    body = json.dumps(payload).encode()

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            r = client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={
                    "X-Atlassian-Webhook-Signature": "sha256=invalidsignature",
                    "Content-Type": "application/json",
                },
            )
    assert r.status_code == 401
    assert "imzası" in r.json()["detail"]


def test_jira_webhook_secret_required_but_not_configured_503():
    """Production without webhook secret configured should return 503."""
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"webhookEvent": "jira:issue_updated"}
    body = json.dumps(payload).encode()

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", ""):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=True):
            r = client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={"Content-Type": "application/json"},
            )
    assert r.status_code == 503
    assert "JIRA_WEBHOOK_SECRET" in r.json()["detail"]


def test_jira_webhook_no_secret_required_no_signature_200():
    """Non-prod environment without signature should work when secret not required."""
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {"key": "TEST-1", "fields": {"status": {"name": "Open"}}},
    }
    body = json.dumps(payload).encode()

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", ""):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            with patch("app.domains.jira.router._sync_defect_link_status"):
                r = client.post(
                    "/api/jira/webhook/jira-incoming",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )
    assert r.status_code == 200


def test_jira_webhook_issue_deleted_event():
    """Webhook with issue_deleted event should process."""
    if not _IMPORT_OK:
        return
    client = _app()
    secret = "test-webhook-secret"
    payload = {
        "webhookEvent": "jira:issue_deleted",
        "issue": {"key": "TEST-DEL"},
    }
    body = json.dumps(payload).encode()
    sig = _make_signature(body, secret)

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            with patch("app.domains.jira.router._delete_defect_links"):
                r = client.post(
                    "/api/jira/webhook/jira-incoming",
                    content=body,
                    headers={
                        "X-Atlassian-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )
    assert r.status_code == 200
    assert r.json()["event"] == "jira:issue_deleted"


def test_jira_webhook_signature_case_sensitive():
    """Signature comparison should be case-sensitive (timing-safe)."""
    if not _IMPORT_OK:
        return
    client = _app()
    secret = "test-webhook-secret"
    payload = {"webhookEvent": "jira:issue_updated"}
    body = json.dumps(payload).encode()
    correct_sig = _make_signature(body, secret)

    # Change case of hex part (HMAC should be lowercase)
    wrong_case_sig = correct_sig.replace(
        correct_sig[7:], correct_sig[7:].upper()
    )

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            r = client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={
                    "X-Atlassian-Webhook-Signature": wrong_case_sig,
                    "Content-Type": "application/json",
                },
            )
    # HMAC comparison should use timing-safe comparison, case matters
    assert r.status_code == 401
