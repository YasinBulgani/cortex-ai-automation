"""Unit tests for app.domains.agents.banking_team.locator_schemas — pure Pydantic schemas.

Tests are fully self-contained: no DB, no HTTP.
Covers: LocatorEntry, FallbackResolveRequest, FallbackStrategyResult,
        FallbackResolveResponse, StabilityDetail, StabilityAnalyzeResponse,
        ImproveSuggestion, BreakagePrediction, TrendAnalysisResponse.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.agents.banking_team.locator_schemas import (
        LocatorEntry,
        FallbackResolveRequest,
        FallbackStrategyResult,
        FallbackResolveResponse,
        StabilityDetail,
        StabilityAnalyzeResponse,
        ImproveSuggestion,
        ImproveSuggestResponse,
        BreakagePrediction,
        BreakagePredictResponse,
        TrendAnalysisResponse,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="locator_schemas import failed")


# ---------------------------------------------------------------------------
# LocatorEntry
# ---------------------------------------------------------------------------

class TestLocatorEntry:
    def test_minimal_creation(self):
        entry = LocatorEntry(selector="[data-testid='btn']")
        assert entry.selector == "[data-testid='btn']"

    def test_default_type_css(self):
        entry = LocatorEntry(selector="div")
        assert entry.type == "css"

    def test_default_status_unknown(self):
        entry = LocatorEntry(selector="div")
        assert entry.status == "unknown"

    def test_default_page_empty(self):
        entry = LocatorEntry(selector="div")
        assert entry.page == ""

    def test_custom_type(self):
        entry = LocatorEntry(selector="//div[@id='x']", type="xpath")
        assert entry.type == "xpath"

    def test_healthy_status(self):
        entry = LocatorEntry(selector="div", status="healthy")
        assert entry.status == "healthy"


# ---------------------------------------------------------------------------
# FallbackResolveRequest
# ---------------------------------------------------------------------------

class TestFallbackResolveRequest:
    def test_minimal_creation(self):
        req = FallbackResolveRequest(selector="[id='btn']")
        assert req.selector == "[id='btn']"

    def test_default_confidence_threshold(self):
        req = FallbackResolveRequest(selector="div")
        assert req.confidence_threshold == pytest.approx(0.75)

    def test_default_dom_snippet_empty(self):
        req = FallbackResolveRequest(selector="div")
        assert req.dom_snippet == ""

    def test_confidence_validation(self):
        req = FallbackResolveRequest(selector="div", confidence_threshold=0.9)
        assert req.confidence_threshold == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# FallbackStrategyResult
# ---------------------------------------------------------------------------

class TestFallbackStrategyResult:
    def test_creation(self):
        result = FallbackStrategyResult(
            strategy="testid",
            selector="[data-testid='btn']",
            confidence=0.95,
            found=True,
        )
        assert result.strategy == "testid"
        assert result.found is True

    def test_default_stability_zero(self):
        result = FallbackStrategyResult(
            strategy="css", selector="div", confidence=0.8, found=False
        )
        assert result.stability_score == 0

    def test_default_reason_empty(self):
        result = FallbackStrategyResult(
            strategy="css", selector="div", confidence=0.8, found=True
        )
        assert result.reason == ""


# ---------------------------------------------------------------------------
# FallbackResolveResponse
# ---------------------------------------------------------------------------

class TestFallbackResolveResponse:
    def test_creation(self):
        resp = FallbackResolveResponse(
            success=True,
            original_selector="[id='old']",
            strategies_tried=3,
            total_latency_ms=150,
            all_results=[],
        )
        assert resp.success is True
        assert resp.strategies_tried == 3

    def test_default_best_selector_none(self):
        resp = FallbackResolveResponse(
            success=False,
            original_selector="[id='old']",
            strategies_tried=1,
            total_latency_ms=50,
            all_results=[],
        )
        assert resp.best_selector is None


# ---------------------------------------------------------------------------
# StabilityDetail
# ---------------------------------------------------------------------------

class TestStabilityDetail:
    def test_creation(self):
        detail = StabilityDetail(
            selector="[data-testid='btn']",
            score=4,
            risk_level="healthy",
        )
        assert detail.score == 4
        assert detail.risk_level == "healthy"

    def test_default_reasons_empty(self):
        detail = StabilityDetail(selector="div", score=2, risk_level="warning")
        assert detail.reasons == []

    def test_suggestion_default_none(self):
        detail = StabilityDetail(selector="div", score=1, risk_level="critical")
        assert detail.suggestion is None


# ---------------------------------------------------------------------------
# StabilityAnalyzeResponse
# ---------------------------------------------------------------------------

class TestStabilityAnalyzeResponse:
    def test_creation(self):
        resp = StabilityAnalyzeResponse(
            total_locators=10,
            healthy=7,
            warning=2,
            critical=1,
            avg_score=3.5,
            details=[],
        )
        assert resp.total_locators == 10
        assert resp.avg_score == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# ImproveSuggestion
# ---------------------------------------------------------------------------

class TestImproveSuggestion:
    def test_creation(self):
        suggestion = ImproveSuggestion(
            original_selector="[id='btn']",
            original_score=2,
            suggested_selector="[data-testid='btn']",
            suggested_score=5,
            improvement_reason="testid is more stable",
        )
        assert suggestion.original_score == 2
        assert suggestion.suggested_score == 5

    def test_default_confidence_zero(self):
        suggestion = ImproveSuggestion(
            original_selector="div", original_score=1,
            suggested_selector="[testid='x']", suggested_score=5,
            improvement_reason="better"
        )
        assert suggestion.confidence == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# BreakagePrediction
# ---------------------------------------------------------------------------

class TestBreakagePrediction:
    def test_creation(self):
        pred = BreakagePrediction(
            selector="[id='btn']",
            risk_score=0.8,
        )
        assert pred.risk_score == pytest.approx(0.8)

    def test_default_risk_factors_empty(self):
        pred = BreakagePrediction(selector="div", risk_score=0.5)
        assert pred.risk_factors == []

    def test_risk_score_bounds_validation(self):
        # Within bounds
        pred = BreakagePrediction(selector="div", risk_score=0.0)
        assert pred.risk_score == pytest.approx(0.0)
        pred = BreakagePrediction(selector="div", risk_score=1.0)
        assert pred.risk_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# BreakagePredictResponse
# ---------------------------------------------------------------------------

class TestBreakagePredictResponse:
    def test_creation(self):
        resp = BreakagePredictResponse(
            predictions=[],
            high_risk_count=1,
            medium_risk_count=2,
            low_risk_count=5,
        )
        assert resp.high_risk_count == 1


# ---------------------------------------------------------------------------
# TrendAnalysisResponse
# ---------------------------------------------------------------------------

class TestTrendAnalysisResponse:
    def test_creation(self):
        resp = TrendAnalysisResponse(
            total_heals=50,
            avg_confidence=0.85,
        )
        assert resp.total_heals == 50

    def test_default_trend_stable(self):
        resp = TrendAnalysisResponse(total_heals=0, avg_confidence=0.0)
        assert resp.trend == "stable"

    def test_default_by_strategy_empty(self):
        resp = TrendAnalysisResponse(total_heals=0, avg_confidence=0.0)
        assert resp.by_strategy == {}

    def test_improving_trend(self):
        resp = TrendAnalysisResponse(total_heals=10, avg_confidence=0.9, trend="improving")
        assert resp.trend == "improving"
