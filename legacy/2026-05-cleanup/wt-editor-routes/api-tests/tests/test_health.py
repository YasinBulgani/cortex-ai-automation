"""Health & readiness endpoint tests."""

import pytest

from config.constants import FastAPIPaths, EnginePaths


@pytest.mark.smoke
class TestFastAPIHealth:

    def test_health_returns_ok(self, api):
        resp = api.get(FastAPIPaths.HEALTH)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ready_returns_database_status(self, api):
        resp = api.get(FastAPIPaths.READY)
        assert resp.status_code == 200
        data = resp.json()
        assert "ready" in data
        assert "database" in data

    def test_health_no_auth_required(self, api_noauth):
        resp = api_noauth.get(FastAPIPaths.HEALTH)
        assert resp.status_code == 200


@pytest.mark.smoke
class TestEngineHealth:

    def test_health_returns_ok(self, engine):
        resp = engine.get(EnginePaths.HEALTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_api_health(self, engine):
        resp = engine.get(EnginePaths.API_HEALTH)
        assert resp.status_code == 200
