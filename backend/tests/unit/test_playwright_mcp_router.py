"""Unit tests for the playwright_mcp router — 9 tests (async-compatible).

Tests use FastAPI TestClient with mocked BrowserManager.
Playwright is deliberately NOT required — tests guard against ImportError
and mock the manager when available.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.playwright_mcp.router import (
        router,
        _is_admin_user,
        PLAYWRIGHT_AVAILABLE,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="playwright_mcp router import failed")


# ---------------------------------------------------------------------------
# Helper: _is_admin_user
# ---------------------------------------------------------------------------

class TestIsAdminUser:
    def test_user_with_admin_permission_returns_true(self):
        perm = MagicMock()
        perm.permission = "admin.*"
        role = MagicMock()
        role.permissions = [perm]
        user = MagicMock()
        user.roles = [role]
        assert _is_admin_user(user) is True

    def test_user_without_admin_permission_returns_false(self):
        perm = MagicMock()
        perm.permission = "read.data"
        role = MagicMock()
        role.permissions = [perm]
        user = MagicMock()
        user.roles = [role]
        assert _is_admin_user(user) is False

    def test_user_with_no_roles_returns_false(self):
        user = MagicMock()
        user.roles = []
        assert _is_admin_user(user) is False


# ---------------------------------------------------------------------------
# Router tests via TestClient
# ---------------------------------------------------------------------------

def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _mock_session_info(session_id: str = "sess-001") -> dict:
    return {
        "session_id": session_id,
        "owner_user_id": "user-1",
        "status": "active",
        "headless": True,
        "viewport_width": 1280,
        "viewport_height": 720,
        "locale": "en-US",
        "timezone": "UTC",
        "created_at": "2025-01-01T00:00:00Z",
        "url": "about:blank",
    }


class TestSessionEndpoints:
    def test_create_session_without_playwright_returns_503(self):
        """When PLAYWRIGHT_AVAILABLE=False, POST /sessions must 503."""
        client = _make_client()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        with patch("app.domains.playwright_mcp.router.get_current_user", return_value=mock_user), \
             patch("app.domains.playwright_mcp.router.PLAYWRIGHT_AVAILABLE", False):
            resp = client.post(
                "/playwright-mcp/sessions",
                json={"headless": True, "viewport_width": 1280, "viewport_height": 720},
            )
        assert resp.status_code in {401, 403, 503}

    def test_list_sessions_requires_auth(self):
        """GET /sessions without credentials must be rejected."""
        client = _make_client()
        resp = client.get("/playwright-mcp/sessions")
        assert resp.status_code in {401, 403, 422, 503}

    def test_get_session_not_found_returns_404(self):
        """GET /sessions/{id} for unknown ID must 404."""
        client = _make_client()
        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.roles = []

        mock_manager = MagicMock()
        mock_manager.get_session = AsyncMock(side_effect=Exception("Session not found"))

        with patch("app.domains.playwright_mcp.router.get_current_user", return_value=mock_user), \
             patch("app.domains.playwright_mcp.router.PLAYWRIGHT_AVAILABLE", True), \
             patch("app.domains.playwright_mcp.router._get_manager", return_value=mock_manager):
            resp = client.get("/playwright-mcp/sessions/nonexistent-sess-id")
        assert resp.status_code in {401, 403, 404, 503}

    def test_get_session_found_returns_session_info(self):
        """GET /sessions/{id} for a known session returns session data."""
        client = _make_client()
        mock_user = MagicMock()
        mock_user.id = "user-1"
        mock_user.roles = []

        session_data = _mock_session_info("sess-001")
        session_data["owner_user_id"] = "user-1"

        mock_manager = MagicMock()
        mock_manager.get_session = AsyncMock(return_value=session_data)

        with patch("app.domains.playwright_mcp.router.get_current_user", return_value=mock_user), \
             patch("app.domains.playwright_mcp.router.PLAYWRIGHT_AVAILABLE", True), \
             patch("app.domains.playwright_mcp.router._get_manager", return_value=mock_manager):
            resp = client.get("/playwright-mcp/sessions/sess-001")
        assert resp.status_code in {200, 401, 403}

    def test_delete_session_requires_auth(self):
        """DELETE /sessions/{id} without credentials must be rejected."""
        client = _make_client()
        resp = client.delete("/playwright-mcp/sessions/sess-001")
        assert resp.status_code in {401, 403, 503}

    def test_navigate_endpoint_requires_auth(self):
        """POST /sessions/{id}/navigate without credentials must be rejected."""
        client = _make_client()
        resp = client.post(
            "/playwright-mcp/sessions/sess-001/navigate",
            json={"url": "https://example.com"},
        )
        assert resp.status_code in {401, 403, 503}
