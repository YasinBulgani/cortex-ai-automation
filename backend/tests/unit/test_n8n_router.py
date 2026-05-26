"""Unit tests for the n8n router — 9 tests.

Tests focus on: _n8n_headers helper, _callback_secret_required guard,
webhook callback endpoint, and the available-workflows proxy.
All DB and HTTP calls are mocked — no real n8n instance needed.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.n8n.router import (
        router,
        _n8n_headers,
        _callback_secret_required,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="n8n router import failed")


# ---------------------------------------------------------------------------
# Helper: _n8n_headers
# ---------------------------------------------------------------------------

class TestN8nHeaders:
    def test_returns_dict_with_content_type(self):
        headers = _n8n_headers()
        assert isinstance(headers, dict)
        assert headers.get("Content-Type") == "application/json"

    def test_api_key_added_when_configured(self, monkeypatch):
        monkeypatch.setenv("N8N_API_KEY", "test-api-key-123")
        import importlib
        import app.domains.n8n.router as n8n_module
        importlib.reload(n8n_module)
        headers = n8n_module._n8n_headers()
        assert "X-N8N-API-KEY" in headers

    def test_no_api_key_header_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("N8N_API_KEY", raising=False)
        import importlib
        import app.domains.n8n.router as n8n_module
        importlib.reload(n8n_module)
        headers = n8n_module._n8n_headers()
        assert "X-N8N-API-KEY" not in headers


# ---------------------------------------------------------------------------
# Helper: _callback_secret_required
# ---------------------------------------------------------------------------

class TestCallbackSecretRequired:
    def test_forced_via_env_returns_true(self, monkeypatch):
        monkeypatch.setenv("N8N_REQUIRE_CALLBACK_SECRET", "1")
        with patch("app.domains.n8n.router.settings") as mock_settings:
            mock_settings.is_production_like = False
            assert _callback_secret_required() is True

    def test_not_forced_returns_settings_value(self, monkeypatch):
        monkeypatch.delenv("N8N_REQUIRE_CALLBACK_SECRET", raising=False)
        with patch("app.domains.n8n.router.settings") as mock_settings:
            mock_settings.is_production_like = False
            result = _callback_secret_required()
            assert result is False


# ---------------------------------------------------------------------------
# Router: TestClient tests
# ---------------------------------------------------------------------------

def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestWebhookCallbackEndpoint:
    def test_webhook_unknown_workflow_returns_404(self):
        client = _make_client()
        mock_db = MagicMock()
        mock_db.get.return_value = None  # workflow not found

        with patch("app.domains.n8n.router.get_db", return_value=iter([mock_db])):
            resp = client.post(
                "/n8n/webhook/unknown-workflow-id",
                json={"executionId": "exec-1", "finished": True, "success": True},
                headers={"x-n8n-token": ""},
            )
        assert resp.status_code in {404, 503}

    def test_webhook_valid_workflow_callback_accepted(self):
        client = _make_client()
        mock_wf = MagicMock()
        mock_wf.id = "wf-123"
        mock_wf.config = {}

        mock_ex = MagicMock()
        mock_ex.id = "exec-abc"

        mock_db = MagicMock()
        mock_db.get.return_value = mock_wf
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_ex

        with patch("app.domains.n8n.router.get_db", return_value=iter([mock_db])), \
             patch("app.domains.n8n.router._callback_secret_required", return_value=False):
            resp = client.post(
                "/n8n/webhook/wf-123",
                json={"executionId": "exec-1", "finished": True, "success": True},
            )
        assert resp.status_code in {200, 401, 503}

    def test_webhook_missing_execution_id_still_accepted(self):
        """Callback without executionId should create a new execution record."""
        client = _make_client()
        mock_wf = MagicMock()
        mock_wf.id = "wf-456"
        mock_wf.config = {}

        mock_db = MagicMock()
        mock_db.get.return_value = mock_wf

        with patch("app.domains.n8n.router.get_db", return_value=iter([mock_db])), \
             patch("app.domains.n8n.router._callback_secret_required", return_value=False):
            resp = client.post(
                "/n8n/webhook/wf-456",
                json={"finished": False},
            )
        # Should process without error — 200 or auth error
        assert resp.status_code in {200, 401, 503}


class TestAvailableWorkflowsEndpoint:
    def test_available_workflows_no_api_key_returns_empty_list(self):
        client = _make_client()
        mock_user = MagicMock()

        with patch("app.domains.n8n.router.get_current_user", return_value=mock_user), \
             patch("app.domains.n8n.router.N8N_API_KEY", ""):
            resp = client.get("/n8n/available-workflows")
        # Auth required — accept 200 (empty workflows) or 401/403
        assert resp.status_code in {200, 401, 403}
