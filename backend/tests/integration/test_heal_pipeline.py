"""Integration tests for Heal Pipeline endpoints (/api/v1/agents/heal/)."""

import pytest
from fastapi.testclient import TestClient


class _FakeHealResult:
    total_broken = 1
    healed = 1
    verified = 1
    updated_files = 0
    duration_ms = 42
    details = [
        {
            "file": "tests/login.spec.ts",
            "test_name": "should login",
            "broken_selector": "#login-btn",
            "new_selector": "[data-testid='login-button']",
            "healed": True,
            "strategy": "heuristic",
            "tier": "tier1",
            "confidence": 0.91,
            "verified_in_browser": False,
            "live_dom_used": False,
            "file_updated": False,
            "screenshot_before": "",
            "screenshot_after": "",
            "error": "",
        }
    ]


class _FakeHealPipeline:
    def __init__(self, project_root, project_id: str = ""):
        self.project_root = project_root
        self.project_id = project_id

    async def run(self, *, failed_tests, session_id: str):
        return _FakeHealResult()


@pytest.fixture
def fake_heal_pipeline(monkeypatch):
    monkeypatch.setattr(
        "app.domains.agents.banking_team.heal_pipeline.HealPipeline",
        _FakeHealPipeline,
    )


class TestHealPipeline:
    """Heal Pipeline endpoint tests.

    The heal pipeline depends on KnowledgeStore and HealPipeline internals
    that may not be fully available in CI.  Tests accept graceful empty
    responses alongside normal ones.
    """

    PREFIX = "/api/v1/agents/heal"

    # ── Auth guard ──────────────────────────────────────────────────────

    def test_heal_run_requires_auth(self, client: TestClient) -> None:
        """POST /heal/run without auth must return 401."""
        r = client.post(
            f"{self.PREFIX}/run",
            json={
                "failed_tests": [
                    {"file": "test.ts", "test_name": "t1", "selector": "#x"}
                ]
            },
        )
        assert r.status_code == 401

    # ── History ─────────────────────────────────────────────────────────

    def test_heal_history(
        self, client: TestClient, auth_headers: dict, project_id: str
    ) -> None:
        """GET /heal/history returns a list."""
        r = client.get(f"{self.PREFIX}/history?project_id={project_id}", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "count" in body
        assert "entries" in body
        assert isinstance(body["entries"], list)

    # ── Stats ───────────────────────────────────────────────────────────

    def test_heal_stats(
        self, client: TestClient, auth_headers: dict, project_id: str
    ) -> None:
        """GET /heal/stats returns a stats object."""
        r = client.get(f"{self.PREFIX}/stats?project_id={project_id}", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "total_heals" in body
        assert "success_rate" in body
        assert "by_strategy" in body

    def test_heal_history_requires_project_membership(
        self,
        client: TestClient,
        viewer_headers: dict[str, str],
        project_id: str,
    ) -> None:
        r = client.get(
            f"{self.PREFIX}/history?project_id={project_id}",
            headers=viewer_headers,
        )
        assert r.status_code == 403

    # ── Run ─────────────────────────────────────────────────────────────

    def test_heal_run_schema(
        self,
        client: TestClient,
        auth_headers: dict,
        project_id: str,
        fake_heal_pipeline,
    ) -> None:
        """POST /heal/run with minimal body returns a structured heal result."""
        r = client.post(
            f"{self.PREFIX}/run",
            json={
                "project_id": project_id,
                "failed_tests": [
                    {
                        "file": "tests/login.spec.ts",
                        "test_name": "should login",
                        "selector": "#login-btn",
                        "error": "Element not found: #login-btn",
                        "dom_snippet": "<div id='sign-in'>Sign In</div>",
                        "page_url": "https://example.com/login",
                    }
                ],
                "auto_update": False,
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "total_broken" in body
        assert "healed" in body
        assert "details" in body
