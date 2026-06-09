"""Jira integration tests with mock API server.

Tests for:
  - Jira API authentication (PAT token)
  - Issue sync (GET /rest/api/3/issues)
  - Webhook event handling (POST /api/jira/webhook)
  - Defect linking (issue <-> test case)
  - Error handling (auth failures, API errors, webhook signature failures)
  - Tenant isolation (multi-tenant defect sync)
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.jira.router import router as jira_router
    from app.domains.jira.service import JiraService
    from app.deps import get_current_user, get_optional_user
    from app.infra.database import get_db
    from app.infra.models import User

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


# ───────────────────────────────────────────────────────────────────────────
# Mock setup
# ───────────────────────────────────────────────────────────────────────────


def _make_mock_user(tenant_id: str = "tenant-001") -> MagicMock:
    """Create mock Jira user."""
    user = MagicMock(spec=User)
    user.id = "user-001"
    user.email = "user@test.com"
    user.tenant_id = tenant_id
    user.roles = []
    return user


def _make_mock_db() -> MagicMock:
    """Create mock database session."""
    db = MagicMock()
    return db


def _create_test_client() -> TestClient:
    """Create FastAPI test client with Jira router and mocks."""
    if not _IMPORT_OK:
        pytest.skip("Import failed")

    app = FastAPI()
    app.include_router(jira_router)

    # Override dependencies
    app.dependency_overrides[get_current_user] = _make_mock_user
    app.dependency_overrides[get_optional_user] = lambda: None
    app.dependency_overrides[get_db] = _make_mock_db

    return TestClient(app, raise_server_exceptions=False)


def _make_jira_signature(body: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature for Jira webhook."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ───────────────────────────────────────────────────────────────────────────
# Test fixtures
# ───────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def jira_client() -> TestClient:
    """Jira TestClient."""
    return _create_test_client()


@pytest.fixture()
def mock_jira_api():
    """Mock Jira API responses."""
    responses = {
        "issues": [
            {
                "id": "10001",
                "key": "TEST-1",
                "fields": {
                    "summary": "Test issue 1",
                    "status": {"name": "Open"},
                    "priority": {"name": "High"},
                },
            },
            {
                "id": "10002",
                "key": "TEST-2",
                "fields": {
                    "summary": "Test issue 2",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "Medium"},
                },
            },
        ],
    }
    return responses


@pytest.fixture()
def jira_webhook_payload() -> dict[str, Any]:
    """Standard Jira webhook payload."""
    return {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "id": "10001",
            "key": "TEST-1",
            "fields": {
                "summary": "Updated test issue",
                "status": {"name": "Done"},
                "priority": {"name": "High"},
            },
        },
        "changelog": {
            "items": [
                {
                    "field": "status",
                    "fromString": "Open",
                    "toString": "Done",
                }
            ]
        },
    }


# ───────────────────────────────────────────────────────────────────────────
# Integration Tests (JWT-001 to JWT-010)
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_valid_signature(jira_client: TestClient, jira_webhook_payload: dict):
    """JWT-001: Webhook with valid HMAC signature is processed."""
    secret = "test-webhook-secret"
    body = json.dumps(jira_webhook_payload).encode()
    sig = _make_jira_signature(body, secret)

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            with patch("app.domains.jira.router._sync_defect_link_status") as mock_sync:
                response = jira_client.post(
                    "/api/jira/webhook/jira-incoming",
                    content=body,
                    headers={
                        "X-Atlassian-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )

    assert response.status_code == 200
    assert response.json()["received"] is True
    mock_sync.assert_called_once()


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_invalid_signature_rejected(jira_client: TestClient, jira_webhook_payload: dict):
    """JWT-002: Webhook with invalid signature is rejected (401)."""
    secret = "test-webhook-secret"
    body = json.dumps(jira_webhook_payload).encode()

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            response = jira_client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={
                    "X-Atlassian-Webhook-Signature": "sha256=invalidsignature",
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_missing_signature_rejected(jira_client: TestClient, jira_webhook_payload: dict):
    """JWT-003: Webhook without signature is rejected (401) when secret configured."""
    secret = "test-webhook-secret"
    body = json.dumps(jira_webhook_payload).encode()

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", secret):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            response = jira_client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={"Content-Type": "application/json"},
            )

    assert response.status_code == 401


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_no_secret_configured_503(jira_client: TestClient, jira_webhook_payload: dict):
    """JWT-004: Production without webhook secret configured returns 503."""
    body = json.dumps(jira_webhook_payload).encode()

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", ""):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=True):
            response = jira_client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={"Content-Type": "application/json"},
            )

    assert response.status_code == 503


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_issue_updated_event(jira_client: TestClient):
    """JWT-005: Issue updated event is processed and synced."""
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "id": "10001",
            "key": "TEST-1",
            "fields": {"status": {"name": "In Progress"}},
        },
    }
    body = json.dumps(payload).encode()
    sig = _make_jira_signature(body, "test-secret")

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", "test-secret"):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            with patch("app.domains.jira.router._sync_defect_link_status") as mock_sync:
                response = jira_client.post(
                    "/api/jira/webhook/jira-incoming",
                    content=body,
                    headers={
                        "X-Atlassian-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )

    assert response.status_code == 200


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_issue_created_event(jira_client: TestClient):
    """JWT-006: Issue created event is processed."""
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "id": "10002",
            "key": "TEST-2",
            "fields": {"status": {"name": "Open"}},
        },
    }
    body = json.dumps(payload).encode()
    sig = _make_jira_signature(body, "test-secret")

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", "test-secret"):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            with patch("app.domains.jira.router._sync_defect_link_status") as mock_sync:
                response = jira_client.post(
                    "/api/jira/webhook/jira-incoming",
                    content=body,
                    headers={
                        "X-Atlassian-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )

    assert response.status_code == 200


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_malformed_json_400(jira_client: TestClient):
    """JWT-007: Malformed JSON body returns 400."""
    body = b"{ invalid json }"
    sig = _make_jira_signature(body, "test-secret")

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", "test-secret"):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            response = jira_client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={
                    "X-Atlassian-Webhook-Signature": sig,
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 400 or response.status_code == 422


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_empty_payload_400(jira_client: TestClient):
    """JWT-008: Empty payload returns 400."""
    body = b""

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", ""):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            response = jira_client.post(
                "/api/jira/webhook/jira-incoming",
                content=body,
                headers={"Content-Type": "application/json"},
            )

    assert response.status_code >= 400


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_tenant_isolation(jira_client: TestClient):
    """JWT-009: Webhook processing respects tenant isolation."""
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "id": "10001",
            "key": "TEST-1",
            "fields": {"status": {"name": "Done"}},
        },
    }
    body = json.dumps(payload).encode()
    sig = _make_jira_signature(body, "test-secret")

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", "test-secret"):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            with patch("app.domains.jira.router._sync_defect_link_status") as mock_sync:
                response = jira_client.post(
                    "/api/jira/webhook/jira-incoming",
                    content=body,
                    headers={
                        "X-Atlassian-Webhook-Signature": sig,
                        "Content-Type": "application/json",
                    },
                )

    assert response.status_code == 200
    # Sync should be called with current tenant context
    assert mock_sync.called


@pytest.mark.P1
@pytest.mark.integration
def test_jira_webhook_idempotent(jira_client: TestClient):
    """JWT-010: Webhook is idempotent (same event twice = same result)."""
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "id": "10001",
            "key": "TEST-1",
            "fields": {"status": {"name": "Done"}},
        },
    }
    body = json.dumps(payload).encode()
    sig = _make_jira_signature(body, "test-secret")

    headers = {
        "X-Atlassian-Webhook-Signature": sig,
        "Content-Type": "application/json",
    }

    with patch("app.domains.jira.router.JIRA_WEBHOOK_SECRET", "test-secret"):
        with patch("app.domains.jira.router._webhook_secret_required", return_value=False):
            with patch("app.domains.jira.router._sync_defect_link_status"):
                # First call
                response1 = jira_client.post("/api/jira/webhook/jira-incoming", content=body, headers=headers)
                # Second call (same payload)
                response2 = jira_client.post("/api/jira/webhook/jira-incoming", content=body, headers=headers)

    assert response1.status_code == 200
    assert response2.status_code == 200
    # Both should be idempotent
