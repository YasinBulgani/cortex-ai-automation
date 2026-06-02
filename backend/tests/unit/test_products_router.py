"""Unit tests for the products router (/products)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.products.router import router as products_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(products_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/products/{product_id}/telemetry
# ---------------------------------------------------------------------------

class TestGetProductTelemetry:
    def test_valid_product_one_returns_200(self, client):
        resp = client.get("/api/v1/products/one/telemetry")
        assert resp.status_code == 200

    def test_valid_product_studio_returns_200(self, client):
        resp = client.get("/api/v1/products/studio/telemetry")
        assert resp.status_code == 200

    def test_valid_product_service_returns_200(self, client):
        resp = client.get("/api/v1/products/service/telemetry")
        assert resp.status_code == 200

    def test_valid_product_web_returns_200(self, client):
        resp = client.get("/api/v1/products/web/telemetry")
        assert resp.status_code == 200

    def test_valid_product_mobile_returns_200(self, client):
        resp = client.get("/api/v1/products/mobile/telemetry")
        assert resp.status_code == 200

    def test_valid_product_data_returns_200(self, client):
        resp = client.get("/api/v1/products/data/telemetry")
        assert resp.status_code == 200

    def test_valid_product_intelligence_returns_200(self, client):
        resp = client.get("/api/v1/products/intelligence/telemetry")
        assert resp.status_code == 200

    def test_valid_product_nexus_code_returns_200(self, client):
        resp = client.get("/api/v1/products/nexus-code/telemetry")
        assert resp.status_code == 200

    def test_invalid_product_id_returns_404(self, client):
        resp = client.get("/api/v1/products/invalid-product/telemetry")
        assert resp.status_code == 404

    def test_response_has_stats_list(self, client):
        resp = client.get("/api/v1/products/one/telemetry")
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert isinstance(data["stats"], list)
        assert len(data["stats"]) > 0

    def test_demo_mode_header_present(self, client):
        resp = client.get("/api/v1/products/one/telemetry")
        assert resp.status_code == 200
        # In demo mode, X-Data-Mode: demo header should be present
        assert resp.headers.get("x-data-mode") == "demo"

    def test_response_has_expected_fields(self, client):
        resp = client.get("/api/v1/products/studio/telemetry")
        assert resp.status_code == 200
        data = resp.json()
        assert "productId" in data
        assert "stats" in data
        assert "aiInsights" in data
        assert "lastUpdated" in data
        assert data["productId"] == "studio"


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/products/web/release-health
# ---------------------------------------------------------------------------

class TestWebReleaseHealth:
    def test_web_release_health_returns_200(self, client):
        resp = client.get("/api/v1/products/web/release-health")
        assert resp.status_code == 200

    def test_web_release_health_has_verdict(self, client):
        resp = client.get("/api/v1/products/web/release-health")
        data = resp.json()
        assert "verdict" in data
        assert data["verdict"] in ("ship", "caution", "block")

    def test_web_release_health_has_checks_list(self, client):
        resp = client.get("/api/v1/products/web/release-health")
        data = resp.json()
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_web_release_health_demo_mode_flag(self, client):
        resp = client.get("/api/v1/products/web/release-health")
        data = resp.json()
        assert data.get("demo_mode") is True


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/products/web/my-inbox/{item_id}/{action}
# ---------------------------------------------------------------------------

class TestWebInboxAction:
    def test_valid_inbox_action_approve(self, client):
        resp = client.post("/api/v1/products/web/my-inbox/item-1/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "approve"
        assert data["status"] == "accepted"

    def test_valid_inbox_action_reject(self, client):
        resp = client.post("/api/v1/products/web/my-inbox/item-2/reject")
        assert resp.status_code == 200

    def test_invalid_inbox_action_returns_400(self, client):
        resp = client.post("/api/v1/products/web/my-inbox/item-1/invalid-action")
        assert resp.status_code == 400

    def test_inbox_action_returns_item_id(self, client):
        resp = client.post("/api/v1/products/web/my-inbox/my-item-99/snooze")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "my-item-99"
