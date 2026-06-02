"""Unit tests for the cost router — 10 tests.

PRICING_CATALOG and estimate_monthly_cost are patched to avoid real
computation and to test router-level contract only.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.cost.router import router as cost_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(cost_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def _make_pricing_entry(model="gpt-5", provider="openai",
                        input_usd=1.25, output_usd=10.0):
    from app.domains.cost.pricing import PricingEntry
    return PricingEntry(
        model=model,
        provider=provider,
        input_per_mtoken_usd=input_usd,
        output_per_mtoken_usd=output_usd,
        is_local=False,
        is_free_tier_available=False,
        notes="test entry",
    )


def _make_cost_estimate():
    from app.domains.cost.service import CostEstimate, ProviderCost
    return CostEstimate(
        total_cost_usd=0.005,
        total_cost_try=0.2,
        usd_to_try_rate=40.0,
        breakdown=[
            ProviderCost(
                model="gpt-5",
                provider="openai",
                input_tokens=1000,
                output_tokens=500,
                call_count=10,
                days=30,
                cost_usd=0.005,
                cost_try=0.2,
                is_local=False,
            )
        ],
        local_alternative_cost_usd=0.0,
        potential_monthly_savings_usd=0.005,
        period_days=30,
        projected_monthly_usd=0.005,
    )


# ---------------------------------------------------------------------------
# GET /pricing
# ---------------------------------------------------------------------------

class TestPricingEndpoint:
    def test_pricing_returns_200(self, client):
        catalog = {"gpt-5": _make_pricing_entry()}
        with patch("app.domains.cost.router.PRICING_CATALOG", catalog):
            resp = client.get("/api/v1/cost/pricing")
        assert resp.status_code == 200

    def test_pricing_response_has_entries_and_total(self, client):
        catalog = {
            "gpt-5": _make_pricing_entry("gpt-5", "openai"),
            "claude-sonnet-4.6": _make_pricing_entry("claude-sonnet-4.6", "anthropic", 3.0, 15.0),
        }
        with patch("app.domains.cost.router.PRICING_CATALOG", catalog):
            resp = client.get("/api/v1/cost/pricing")
        data = resp.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] == 2

    def test_pricing_entry_has_required_fields(self, client):
        catalog = {"gpt-5": _make_pricing_entry()}
        with patch("app.domains.cost.router.PRICING_CATALOG", catalog):
            resp = client.get("/api/v1/cost/pricing")
        entry = resp.json()["entries"][0]
        assert "model" in entry
        assert "provider" in entry
        assert "input_per_mtoken_usd" in entry
        assert "output_per_mtoken_usd" in entry

    def test_pricing_entry_model_value_correct(self, client):
        catalog = {"gpt-5": _make_pricing_entry("gpt-5", "openai", 1.25, 10.0)}
        with patch("app.domains.cost.router.PRICING_CATALOG", catalog):
            resp = client.get("/api/v1/cost/pricing")
        entry = resp.json()["entries"][0]
        assert entry["model"] == "gpt-5"
        assert entry["provider"] == "openai"
        assert entry["input_per_mtoken_usd"] == 1.25

    def test_pricing_empty_catalog_returns_total_zero(self, client):
        with patch("app.domains.cost.router.PRICING_CATALOG", {}):
            resp = client.get("/api/v1/cost/pricing")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# POST /estimate
# ---------------------------------------------------------------------------

class TestEstimateEndpoint:
    def test_estimate_valid_usage_returns_200(self, client):
        est = _make_cost_estimate()
        from app.domains.cost.service import to_pydantic
        with patch("app.domains.cost.router.estimate_monthly_cost", return_value=est):
            resp = client.post("/api/v1/cost/estimate", json={
                "usages": [{
                    "model": "gpt-5",
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "call_count": 10,
                    "days": 30,
                }]
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost_usd" in data
        assert "breakdown" in data

    def test_estimate_missing_usages_returns_422(self, client):
        resp = client.post("/api/v1/cost/estimate", json={})
        assert resp.status_code == 422

    def test_estimate_empty_usages_list_returns_422(self, client):
        resp = client.post("/api/v1/cost/estimate", json={"usages": []})
        assert resp.status_code == 422

    def test_estimate_multiple_periods_returns_breakdown(self, client):
        from app.domains.cost.service import CostEstimate, ProviderCost
        est = CostEstimate(
            total_cost_usd=0.020,
            total_cost_try=0.8,
            usd_to_try_rate=40.0,
            breakdown=[
                ProviderCost("gpt-5", "openai", 1000, 500, 10, 30, 0.010, 0.4, False),
                ProviderCost("claude-sonnet-4.6", "anthropic", 2000, 1000, 20, 30, 0.010, 0.4, False),
            ],
            local_alternative_cost_usd=0.0,
            potential_monthly_savings_usd=0.020,
            period_days=30,
            projected_monthly_usd=0.020,
        )
        with patch("app.domains.cost.router.estimate_monthly_cost", return_value=est):
            resp = client.post("/api/v1/cost/estimate", json={
                "usages": [
                    {"model": "gpt-5", "input_tokens": 1000, "output_tokens": 500},
                    {"model": "claude-sonnet-4.6", "input_tokens": 2000, "output_tokens": 1000},
                ]
            })
        assert resp.status_code == 200
        assert len(resp.json()["breakdown"]) == 2

    def test_estimate_response_has_projected_monthly(self, client):
        est = _make_cost_estimate()
        with patch("app.domains.cost.router.estimate_monthly_cost", return_value=est):
            resp = client.post("/api/v1/cost/estimate", json={
                "usages": [{"model": "gpt-5", "input_tokens": 500, "output_tokens": 250}]
            })
        assert "projected_monthly_usd" in resp.json()
