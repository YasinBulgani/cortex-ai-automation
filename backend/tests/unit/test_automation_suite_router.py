"""Unit tests for the automation_suite router.

Uses FastAPI TestClient to exercise the router in isolation. All service
calls are patched so no external process (engine, DB) is needed.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.automation_suite.router import router
    from app.domains.automation_suite.schemas import (
        SuiteCatalogSuggestResponse,
        SuiteGenerateResponse,
        SuiteHealthResponse,
        SuiteRunResponse,
        SuiteRunStatus,
    )
    from app.domains.automation_suite.mobile import MobileGenerateResponse

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="automation_suite deps not available")


# ---------------------------------------------------------------------------
# Test app fixture — overrides auth dependency so tests don't need a real DB
# ---------------------------------------------------------------------------

@pytest.fixture()
def client() -> "TestClient":
    from app.deps import get_current_user
    from app.infra.models import User

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    fake_user = MagicMock(spec=User)
    fake_user.id = "test-user-id"
    fake_user.email = "test@example.com"

    app.dependency_overrides[get_current_user] = lambda: fake_user
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateEndpoint:
    """POST /api/v1/automation-suite/generate"""

    def test_generate_returns_200_on_success(self, client: "TestClient") -> None:
        mock_response = MagicMock(spec=SuiteGenerateResponse)
        mock_response.model_dump.return_value = {"gherkin": "Feature: demo", "code": "pass"}

        with patch(
            "app.domains.automation_suite.service.generate_from_manual_test",
            new=AsyncMock(return_value=mock_response),
        ):
            r = client.post(
                "/api/v1/automation-suite/generate",
                json={"manual_test": "Login as admin", "language": "python"},
            )
        assert r.status_code == 200

    def test_generate_returns_502_on_runtime_error(self, client: "TestClient") -> None:
        with patch(
            "app.domains.automation_suite.service.generate_from_manual_test",
            new=AsyncMock(side_effect=RuntimeError("engine down")),
        ):
            r = client.post(
                "/api/v1/automation-suite/generate",
                json={"manual_test": "Click login", "language": "python"},
            )
        assert r.status_code == 502

    def test_generate_returns_400_on_value_error(self, client: "TestClient") -> None:
        with patch(
            "app.domains.automation_suite.service.generate_from_manual_test",
            new=AsyncMock(side_effect=ValueError("bad input")),
        ):
            r = client.post(
                "/api/v1/automation-suite/generate",
                json={"manual_test": "", "language": "python"},
            )
        assert r.status_code == 400


class TestRunEndpoint:
    """POST /api/v1/automation-suite/run"""

    def test_run_returns_202_on_success(self, client: "TestClient") -> None:
        mock_response = MagicMock(spec=SuiteRunResponse)
        mock_response.model_dump.return_value = {"run_id": "abc-123", "status": "queued"}

        with patch(
            "app.domains.automation_suite.service.start_run",
            new=AsyncMock(return_value=mock_response),
        ):
            r = client.post(
                "/api/v1/automation-suite/run",
                json={"feature_path": "features/login.feature"},
            )
        assert r.status_code == 202

    def test_run_returns_400_on_value_error(self, client: "TestClient") -> None:
        with patch(
            "app.domains.automation_suite.service.start_run",
            new=AsyncMock(side_effect=ValueError("feature not found")),
        ):
            r = client.post(
                "/api/v1/automation-suite/run",
                json={"feature_path": "missing.feature"},
            )
        assert r.status_code == 400


class TestRunStatusEndpoint:
    """GET /api/v1/automation-suite/runs/{run_id}"""

    def test_get_run_returns_200_when_found(self, client: "TestClient") -> None:
        mock_status = MagicMock(spec=SuiteRunStatus)
        mock_status.model_dump.return_value = {"run_id": "abc-123", "status": "passed"}

        with patch(
            "app.domains.automation_suite.service.get_run_status",
            return_value=mock_status,
        ):
            r = client.get("/api/v1/automation-suite/runs/abc-123")
        assert r.status_code == 200

    def test_get_run_returns_404_when_not_found(self, client: "TestClient") -> None:
        with patch(
            "app.domains.automation_suite.service.get_run_status",
            return_value=None,
        ):
            r = client.get("/api/v1/automation-suite/runs/nonexistent-run")
        assert r.status_code == 404


class TestCatalogSuggestEndpoint:
    """POST /api/v1/automation-suite/catalog/suggest"""

    def test_suggest_returns_200(self, client: "TestClient") -> None:
        mock_response = MagicMock(spec=SuiteCatalogSuggestResponse)
        mock_response.model_dump.return_value = {"suggestions": ["click element", "fill input"]}

        with patch(
            "app.domains.automation_suite.service.suggest_from_description",
            return_value=mock_response,
        ):
            r = client.post(
                "/api/v1/automation-suite/catalog/suggest",
                json={"description": "click the login button", "limit": 5},
            )
        assert r.status_code == 200


class TestHealthEndpoint:
    """GET /api/v1/automation-suite/health"""

    def test_health_returns_200(self, client: "TestClient") -> None:
        mock_health = MagicMock(spec=SuiteHealthResponse)
        mock_health.model_dump.return_value = {"backend": "ok", "engine": "ok", "dsl": "ok"}

        with patch(
            "app.domains.automation_suite.service.health_snapshot",
            new=AsyncMock(return_value=mock_health),
        ):
            r = client.get("/api/v1/automation-suite/health")
        assert r.status_code == 200


class TestMobileGenerateEndpoint:
    """POST /api/v1/automation-suite/mobile/generate"""

    def test_mobile_generate_returns_200(self, client: "TestClient") -> None:
        mock_response = MagicMock(spec=MobileGenerateResponse)
        mock_response.model_dump.return_value = {"gherkin": "Feature: mobile login"}

        with patch(
            "app.domains.automation_suite.mobile.generate_mobile_scenario",
            return_value=mock_response,
        ):
            r = client.post(
                "/api/v1/automation-suite/mobile/generate",
                json={"description": "tap login", "device": "iPhone 14"},
            )
        assert r.status_code == 200

    def test_mobile_generate_returns_502_on_runtime_error(self, client: "TestClient") -> None:
        with patch(
            "app.domains.automation_suite.mobile.generate_mobile_scenario",
            side_effect=RuntimeError("Ollama unreachable"),
        ):
            r = client.post(
                "/api/v1/automation-suite/mobile/generate",
                json={"description": "tap logout", "device": "Pixel 7"},
            )
        assert r.status_code == 502

    def test_mobile_generate_returns_400_on_value_error(self, client: "TestClient") -> None:
        with patch(
            "app.domains.automation_suite.mobile.generate_mobile_scenario",
            side_effect=ValueError("empty description"),
        ):
            r = client.post(
                "/api/v1/automation-suite/mobile/generate",
                json={"description": "", "device": "Pixel 7"},
            )
        assert r.status_code == 400
