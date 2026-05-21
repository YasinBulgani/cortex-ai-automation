"""Integration tests for Locator Intelligence endpoints (/api/v1/agents/locator/)."""

import pytest
from fastapi.testclient import TestClient


# Sample locator entries reused across tests
_SAMPLE_LOCATORS = [
    {"name": "login_btn", "selector": "#login-button", "type": "css"},
    {"name": "user_input", "selector": "input[name='username']", "type": "css"},
]


class _FakeFallbackChain:
    def __init__(self, project_id: str = ""):
        self.project_id = project_id

    async def resolve(self, **kwargs):
        return {
            "success": True,
            "best_selector": "[data-testid='login-button']",
            "best_strategy": "heuristic",
            "best_confidence": 0.93,
            "best_stability": 4,
            "total_latency_ms": 12,
            "results": [
                {
                    "strategy": "heuristic",
                    "selector": "[data-testid='login-button']",
                    "confidence": 0.93,
                    "stability_score": 4,
                    "found": True,
                    "reason": "stable id match",
                    "latency_ms": 12,
                }
            ],
        }


class _FakeLocatorIntelligence:
    async def analyze_stability(self, **kwargs):
        return {
            "total_locators": 2,
            "healthy": 1,
            "warning": 1,
            "critical": 0,
            "avg_score": 3.5,
            "details": [
                {
                    "selector": "#login-button",
                    "name": "login_btn",
                    "score": 4,
                    "risk_level": "healthy",
                    "reasons": ["stable id"],
                    "suggestion": None,
                }
            ],
            "improvements": ["Prefer test ids for dynamic nodes"],
        }

    async def suggest_improvements(self, **kwargs):
        return {
            "suggestions": [
                {
                    "original_selector": "#login-button",
                    "original_score": 2,
                    "suggested_selector": "[data-testid='login-button']",
                    "suggested_score": 5,
                    "improvement_reason": "test id is more stable",
                    "confidence": 0.95,
                }
            ],
            "total_improved": 1,
        }

    async def generate_page_object(self, **kwargs):
        return {
            "page_name": "LoginPage",
            "language": "typescript",
            "code": "export class LoginPage {}",
            "element_count": 2,
            "file_name": "LoginPage.ts",
        }

    async def predict_breakage(self, **kwargs):
        return {
            "predictions": [
                {
                    "selector": "#login-button",
                    "name": "login_btn",
                    "risk_score": 0.2,
                    "risk_factors": ["minor dom churn"],
                    "recommendation": "keep under observation",
                }
            ],
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 1,
        }


@pytest.fixture
def fake_locator_services(monkeypatch):
    monkeypatch.setattr(
        "app.domains.agents.banking_team.locator_fallback_chain.LocatorFallbackChain",
        _FakeFallbackChain,
    )
    monkeypatch.setattr(
        "app.domains.agents.banking_team.locator_intelligence.LocatorIntelligence",
        _FakeLocatorIntelligence,
    )


class TestLocatorIntelligence:
    """Locator Intelligence endpoint tests.

    The underlying LocatorIntelligence / LocatorFallbackChain modules may not
    be available, so endpoints can return 501 (Not Implemented) or 500
    alongside the expected status codes.
    """

    PREFIX = "/api/v1/agents/locator"

    # ── Auth guard ──────────────────────────────────────────────────────

    def test_resolve_requires_auth(self, client: TestClient) -> None:
        """POST /locator/resolve without auth must return 401."""
        r = client.post(
            f"{self.PREFIX}/resolve",
            json={"selector": "#broken"},
        )
        assert r.status_code == 401

    # ── Resolve ─────────────────────────────────────────────────────────

    def test_resolve_selector(
        self,
        client: TestClient,
        auth_headers: dict,
        project_id: str,
        fake_locator_services,
    ) -> None:
        """POST /locator/resolve with a selector body returns a stable fallback."""
        r = client.post(
            f"{self.PREFIX}/resolve",
            json={
                "project_id": project_id,
                "selector": "#broken-selector",
                "dom_snippet": "<div id='new-btn'>Click</div>",
                "page_url": "https://example.com/login",
                "error_message": "Element not found",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "success" in body
        assert "original_selector" in body

    # ── Stability ───────────────────────────────────────────────────────

    def test_stability_analysis(
        self, client: TestClient, auth_headers: dict, fake_locator_services
    ) -> None:
        """POST /locator/stability analyzes selector stability."""
        r = client.post(
            f"{self.PREFIX}/stability",
            json={
                "locators": _SAMPLE_LOCATORS,
                "dom_snippet": "<div id='login-button'>Login</div>",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "total_locators" in body
        assert "details" in body

    # ── Improve ─────────────────────────────────────────────────────────

    def test_improve_suggestions(
        self, client: TestClient, auth_headers: dict, fake_locator_services
    ) -> None:
        """POST /locator/improve suggests selector improvements."""
        r = client.post(
            f"{self.PREFIX}/improve",
            json={
                "locators": _SAMPLE_LOCATORS,
                "dom_snippet": "<form><input name='username'/></form>",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "suggestions" in body

    # ── POM Generate ────────────────────────────────────────────────────

    def test_pom_generate(
        self, client: TestClient, auth_headers: dict, fake_locator_services
    ) -> None:
        """POST /locator/pom/generate creates a Page Object Model."""
        r = client.post(
            f"{self.PREFIX}/pom/generate",
            json={
                "page_name": "LoginPage",
                "page_url": "https://example.com/login",
                "elements": [
                    {"tag": "input", "name": "username", "selector": "#user"},
                    {"tag": "button", "name": "submit", "selector": "#submit"},
                ],
                "language": "typescript",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "code" in body
        assert body["page_name"] == "LoginPage"

    # ── Predict ─────────────────────────────────────────────────────────

    def test_predict_breakage(
        self, client: TestClient, auth_headers: dict, fake_locator_services
    ) -> None:
        """POST /locator/predict estimates breakage risk."""
        r = client.post(
            f"{self.PREFIX}/predict",
            json={
                "locators": _SAMPLE_LOCATORS,
                "recent_changes": "diff --git a/login.tsx",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "predictions" in body

    # ── Trends ──────────────────────────────────────────────────────────

    def test_trends(
        self, client: TestClient, auth_headers: dict, project_id: str
    ) -> None:
        """GET /locator/trends returns heal trend analysis."""
        r = client.get(f"{self.PREFIX}/trends?project_id={project_id}", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "total_heals" in body
        assert "trend" in body

    def test_trends_requires_project_membership(
        self,
        client: TestClient,
        viewer_headers: dict[str, str],
        project_id: str,
    ) -> None:
        r = client.get(
            f"{self.PREFIX}/trends?project_id={project_id}",
            headers=viewer_headers,
        )
        assert r.status_code == 403
