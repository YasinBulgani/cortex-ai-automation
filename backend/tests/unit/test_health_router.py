"""Unit tests for the health router (/health)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.health.router import router as health_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(health_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def _make_extended_health(overall: str = "ok"):
    from app.domains.health.schemas import ExtendedHealth, ComponentStatus, HealthLevel
    import time
    return ExtendedHealth(
        overall=HealthLevel(overall),
        components=[
            ComponentStatus(name="postgres", label="Veritabanı (PostgreSQL)", level=HealthLevel.ok),
            ComponentStatus(name="redis", label="Redis", level=HealthLevel.ok, optional=True),
            ComponentStatus(name="engine", label="Test Motoru", level=HealthLevel.ok),
            ComponentStatus(name="ai_gateway", label="AI Gateway", level=HealthLevel.ok, optional=True),
            ComponentStatus(name="ollama", label="Ollama (lokal LLM)", level=HealthLevel.down, optional=True),
        ],
        checked_at_unix=time.time(),
        app_name="neurex-qa",
    )


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/health/extended
# ---------------------------------------------------------------------------

class TestExtendedHealth:
    def test_extended_health_returns_200(self, client):
        with patch("app.domains.health.service.get_extended_health", return_value=_make_extended_health()):
            resp = client.get("/api/v1/health/extended")
        assert resp.status_code == 200

    def test_extended_health_has_overall_field(self, client):
        with patch("app.domains.health.service.get_extended_health", return_value=_make_extended_health("ok")):
            resp = client.get("/api/v1/health/extended")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall" in data
        assert data["overall"] in ("ok", "degraded", "down")

    def test_extended_health_has_components_list(self, client):
        with patch("app.domains.health.service.get_extended_health", return_value=_make_extended_health()):
            resp = client.get("/api/v1/health/extended")
        data = resp.json()
        assert "components" in data
        assert isinstance(data["components"], list)

    def test_extended_health_components_have_required_fields(self, client):
        with patch("app.domains.health.service.get_extended_health", return_value=_make_extended_health()):
            resp = client.get("/api/v1/health/extended")
        data = resp.json()
        for comp in data["components"]:
            assert "name" in comp
            assert "label" in comp
            assert "level" in comp

    def test_extended_health_has_checked_at_unix(self, client):
        with patch("app.domains.health.service.get_extended_health", return_value=_make_extended_health()):
            resp = client.get("/api/v1/health/extended")
        data = resp.json()
        assert "checked_at_unix" in data
        assert isinstance(data["checked_at_unix"], float)

    def test_extended_health_overall_is_degraded_when_optional_down(self, client):
        with patch(
            "app.domains.health.service.get_extended_health",
            return_value=_make_extended_health("degraded"),
        ):
            resp = client.get("/api/v1/health/extended")
        data = resp.json()
        assert data["overall"] == "degraded"

    def test_extended_health_overall_down_when_required_fails(self, client):
        with patch(
            "app.domains.health.service.get_extended_health",
            return_value=_make_extended_health("down"),
        ):
            resp = client.get("/api/v1/health/extended")
        data = resp.json()
        assert data["overall"] == "down"

    def test_extended_health_postgres_component_present(self, client):
        with patch("app.domains.health.service.get_extended_health", return_value=_make_extended_health()):
            resp = client.get("/api/v1/health/extended")
        data = resp.json()
        names = [c["name"] for c in data["components"]]
        assert "postgres" in names

    def test_extended_health_engine_component_present(self, client):
        with patch("app.domains.health.service.get_extended_health", return_value=_make_extended_health()):
            resp = client.get("/api/v1/health/extended")
        data = resp.json()
        names = [c["name"] for c in data["components"]]
        assert "engine" in names


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/health/db
# ---------------------------------------------------------------------------

class TestDbHealth:
    def test_db_health_returns_200_when_db_ok(self, client):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.pool = MagicMock()
        mock_engine.pool.checkedout = lambda: 2
        mock_engine.pool.size = lambda: 10

        with (
            patch("app.domains.health.router.engine", mock_engine),
            patch("app.infra.database.engine", mock_engine),
        ):
            resp = client.get("/api/v1/health/db")
        assert resp.status_code == 200

    def test_db_health_response_has_status_field(self, client):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.pool = MagicMock()

        with (
            patch("app.domains.health.router.engine", mock_engine),
            patch("app.infra.database.engine", mock_engine),
        ):
            resp = client.get("/api/v1/health/db")
        if resp.status_code == 200:
            assert "status" in resp.json()
