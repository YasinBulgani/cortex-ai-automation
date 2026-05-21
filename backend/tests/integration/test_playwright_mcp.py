"""Integration tests for Playwright MCP endpoints (/api/v1/playwright-mcp/)."""

import asyncio

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_playwright_state(client: TestClient) -> None:
    """Isolate shared client cookies and browser sessions between tests."""
    from app.domains.playwright_mcp import router as playwright_router

    client.cookies.clear()
    manager = getattr(playwright_router, "_manager", None)
    if manager is not None:
        asyncio.run(manager.shutdown())

    yield

    client.cookies.clear()
    if manager is not None:
        asyncio.run(manager.shutdown())


class TestPlaywrightMCP:
    """Playwright MCP browser automation endpoint tests.

    Playwright may not be installed, so most session-dependent endpoints
    are expected to return either the normal status code or 503 (Service
    Unavailable).
    """

    PREFIX = "/api/v1/playwright-mcp"

    # ── Health ──────────────────────────────────────────────────────────

    def test_health_endpoint(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """GET /health returns 200 with a status field."""
        r = client.get(f"{self.PREFIX}/health", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "status" in body

    def test_health_playwright_status(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """GET /health exposes playwright_available boolean."""
        r = client.get(f"{self.PREFIX}/health", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "playwright_available" in body
        assert isinstance(body["playwright_available"], bool)

    # ── Auth guard ──────────────────────────────────────────────────────

    def test_sessions_requires_auth(self, client: TestClient) -> None:
        """GET /sessions without token must return 401."""
        r = client.get(f"{self.PREFIX}/sessions")
        assert r.status_code == 401

    # ── Session lifecycle ───────────────────────────────────────────────

    def test_create_session_schema(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /sessions returns 201 / 503 / 429 (rate-limited in full suite)."""
        r = client.post(
            f"{self.PREFIX}/sessions",
            json={"headless": True},
            headers=auth_headers,
        )
        # 429: tam pytest akışında önceki testler rate-limit'i doldurmuş olabilir
        # 503: Playwright browser indirilmemiş
        assert r.status_code in (201, 429, 503)
        if r.status_code == 201:
            body = r.json()
            assert "session_id" in body
            assert "status" in body

    def test_list_sessions(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """GET /sessions returns a list or 503."""
        r = client.get(f"{self.PREFIX}/sessions", headers=auth_headers)
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            assert isinstance(r.json(), list)

    def test_close_nonexistent_session(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """DELETE /sessions/fake-id returns 404 or 503."""
        r = client.delete(
            f"{self.PREFIX}/sessions/fake-id", headers=auth_headers
        )
        assert r.status_code in (404, 503)

    # ── Navigation ──────────────────────────────────────────────────────

    def test_navigate_requires_session(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /sessions/fake/navigate returns 404 or 503."""
        r = client.post(
            f"{self.PREFIX}/sessions/fake/navigate",
            json={"url": "https://example.com"},
            headers=auth_headers,
        )
        assert r.status_code in (404, 503)

    # ── Screenshot ──────────────────────────────────────────────────────

    def test_screenshot_requires_session(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /sessions/fake/screenshot returns 404 or 503."""
        r = client.post(
            f"{self.PREFIX}/sessions/fake/screenshot",
            json={},
            headers=auth_headers,
        )
        assert r.status_code in (404, 503)

    # ── DOM ─────────────────────────────────────────────────────────────

    def test_dom_requires_session(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /sessions/fake/dom returns 404 or 503."""
        r = client.post(
            f"{self.PREFIX}/sessions/fake/dom",
            json={},
            headers=auth_headers,
        )
        assert r.status_code in (404, 503)

    # ── Selectors ───────────────────────────────────────────────────────

    def test_validate_selectors_schema(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /sessions/fake/selectors/validate with body returns 404 or 503."""
        r = client.post(
            f"{self.PREFIX}/sessions/fake/selectors/validate",
            json={"selectors": ["#login-btn", ".submit"]},
            headers=auth_headers,
        )
        assert r.status_code in (404, 503)

    def test_suggest_selectors_schema(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /sessions/fake/selectors/suggest returns 404 or 503."""
        r = client.post(
            f"{self.PREFIX}/sessions/fake/selectors/suggest",
            json={"target_description": "Login button"},
            headers=auth_headers,
        )
        assert r.status_code in (404, 503)

    # ── Action ──────────────────────────────────────────────────────────

    def test_action_schema(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /sessions/fake/action returns 404 or 503."""
        r = client.post(
            f"{self.PREFIX}/sessions/fake/action",
            json={"action": "click", "selector": "#btn"},
            headers=auth_headers,
        )
        assert r.status_code in (404, 503)

    # ── Heal verify ─────────────────────────────────────────────────────

    def test_heal_verify_schema(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /sessions/fake/heal/verify returns 404 or 503."""
        r = client.post(
            f"{self.PREFIX}/sessions/fake/heal/verify",
            json={
                "original_selector": "#old-btn",
                "healed_selector": "#new-btn",
            },
            headers=auth_headers,
        )
        assert r.status_code in (404, 503)

    def test_session_access_is_user_scoped(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        viewer_headers: dict[str, str],
        monkeypatch,
    ) -> None:
        from app.domains.playwright_mcp import router as playwright_router

        owner_id = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]

        class _FakeManager:
            async def get_session(self, session_id: str):
                return {
                    "session_id": session_id,
                    "status": "active",
                    "current_url": "https://example.com",
                    "created_at": "2026-01-01T00:00:00Z",
                    "page_title": "Example",
                    "owner_user_id": owner_id,
                }

        monkeypatch.setattr(playwright_router, "_get_manager", lambda: _FakeManager())

        forbidden = client.get(
            f"{self.PREFIX}/sessions/session-owned-by-admin",
            headers=viewer_headers,
        )
        assert forbidden.status_code == 403
