"""Unit tests for app.domains.cost.service and app.domains.cost.pricing.

Tests are fully self-contained: pure-Python, no DB, no HTTP, no external services.
"""
from __future__ import annotations

import os
import pytest

try:
    from app.domains.cost import service as cost_svc
    from app.domains.cost.service import (
        UsagePeriod,
        estimate_monthly_cost,
        _scale_to_monthly,
        _usd_to_try_rate,
        to_pydantic,
        DEFAULT_USD_TO_TRY,
    )
    from app.domains.cost.pricing import (
        get_pricing,
        estimate_cost_usd,
        PRICING_CATALOG,
        DEFAULT_PRICING,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="cost service import failed")


# ── _usd_to_try_rate ─────────────────────────────────────────────────────────


class TestUsdToTryRate:
    def test_returns_default_when_env_not_set(self, monkeypatch):
        """USD_TO_TRY env yokken DEFAULT_USD_TO_TRY döndürmeli."""
        monkeypatch.delenv("USD_TO_TRY", raising=False)
        rate = _usd_to_try_rate()
        assert rate == DEFAULT_USD_TO_TRY

    def test_returns_env_value_when_set(self, monkeypatch):
        """USD_TO_TRY env ayarlandığında o değeri döndürmeli."""
        monkeypatch.setenv("USD_TO_TRY", "38.5")
        rate = _usd_to_try_rate()
        assert rate == pytest.approx(38.5)

    def test_returns_default_for_invalid_env(self, monkeypatch):
        """Geçersiz USD_TO_TRY env için DEFAULT döndürmeli."""
        monkeypatch.setenv("USD_TO_TRY", "not-a-number")
        rate = _usd_to_try_rate()
        assert rate == DEFAULT_USD_TO_TRY


# ── _scale_to_monthly ────────────────────────────────────────────────────────


class TestScaleToMonthly:
    def test_30_day_period_unchanged(self):
        """30 günlük dönem için maliyet değişmemeli."""
        result = _scale_to_monthly(100.0, 30)
        assert result == pytest.approx(100.0)

    def test_15_day_period_doubles(self):
        """15 günlük dönem 30 güne ölçeklendiğinde maliyet 2x olmalı."""
        result = _scale_to_monthly(50.0, 15)
        assert result == pytest.approx(100.0, rel=1e-3)

    def test_zero_days_returns_zero(self):
        """0 gün için sıfır döndürmeli (sıfır bölmesini önlemeli)."""
        result = _scale_to_monthly(100.0, 0)
        assert result == 0.0


# ── get_pricing ──────────────────────────────────────────────────────────────


class TestGetPricing:
    def test_known_model_returns_correct_entry(self):
        """Bilinen model için fiyat kaydı döndürmeli."""
        entry = get_pricing("gpt-4o")
        assert entry.model == "gpt-4o"
        assert entry.provider == "openai"

    def test_unknown_model_returns_default(self):
        """Bilinmeyen model için pesimistik DEFAULT_PRICING döndürmeli."""
        entry = get_pricing("totally-unknown-model-xyz")
        assert entry.provider == "unknown"

    def test_empty_model_returns_default(self):
        """Boş model adı için DEFAULT_PRICING döndürmeli."""
        entry = get_pricing("")
        assert entry.provider == "unknown"

    def test_ollama_model_is_local(self):
        """Ollama modelleri is_local=True olmalı."""
        entry = get_pricing("qwen2.5-coder:7b")
        assert entry.is_local is True

    def test_anthropic_model_not_local(self):
        """Anthropic modelleri is_local=False olmalı."""
        entry = get_pricing("claude-sonnet-4.6")
        assert entry.is_local is False


# ── estimate_cost_usd ────────────────────────────────────────────────────────


class TestEstimateCostUsd:
    def test_local_model_cost_is_zero(self):
        """Lokal model (Ollama) maliyeti 0 olmalı."""
        cost = estimate_cost_usd("qwen2.5-coder:7b", input_tokens=100_000, output_tokens=50_000)
        assert cost == 0.0

    def test_cloud_model_cost_is_positive(self):
        """Bulut modeli için maliyet pozitif olmalı."""
        cost = estimate_cost_usd("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost > 0.0

    def test_zero_tokens_returns_zero(self):
        """Sıfır token için maliyet 0 olmalı."""
        cost = estimate_cost_usd("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_cost_increases_with_tokens(self):
        """Token sayısı arttıkça maliyet artmalı."""
        cost_low = estimate_cost_usd("gpt-4o", input_tokens=1_000, output_tokens=1_000)
        cost_high = estimate_cost_usd("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost_high > cost_low


# ── estimate_monthly_cost ────────────────────────────────────────────────────


class TestEstimateMonthlyCost:
    def test_single_usage_returns_estimate(self):
        """Tekli kullanım listesi için tahmin döndürmeli."""
        usages = [UsagePeriod(model="gpt-4o", input_tokens=100_000, output_tokens=50_000, call_count=10, days=30)]
        est = estimate_monthly_cost(usages)
        assert est.total_cost_usd >= 0
        assert est.total_cost_try >= 0

    def test_local_model_has_zero_cost(self):
        """Lokal model kullanımı sıfır maliyetle sonuçlanmalı."""
        usages = [UsagePeriod(model="qwen2.5-coder:7b", input_tokens=500_000, output_tokens=200_000, call_count=100, days=30)]
        est = estimate_monthly_cost(usages)
        assert est.total_cost_usd == 0.0

    def test_breakdown_length_matches_usages(self):
        """breakdown listesi giriş listesiyle aynı uzunlukta olmalı."""
        usages = [
            UsagePeriod(model="gpt-4o", input_tokens=10_000, output_tokens=5_000, call_count=5, days=30),
            UsagePeriod(model="claude-sonnet-4.6", input_tokens=20_000, output_tokens=10_000, call_count=10, days=30),
        ]
        est = estimate_monthly_cost(usages)
        assert len(est.breakdown) == 2

    def test_potential_savings_non_negative(self):
        """Tasarruf fırsatı negatif olmamalı."""
        usages = [UsagePeriod(model="gpt-4o", input_tokens=1_000_000, output_tokens=500_000, call_count=50, days=30)]
        est = estimate_monthly_cost(usages)
        assert est.potential_monthly_savings_usd >= 0

    def test_empty_usage_list_returns_zero_cost(self):
        """Boş kullanım listesi için maliyet sıfır olmalı."""
        est = estimate_monthly_cost([])
        assert est.total_cost_usd == 0.0
        assert est.breakdown == []

    def test_period_days_reflects_max_days(self):
        """period_days maksimum days değerini yansıtmalı."""
        usages = [
            UsagePeriod(model="gpt-4o", input_tokens=1_000, output_tokens=500, call_count=1, days=7),
            UsagePeriod(model="gpt-4o", input_tokens=1_000, output_tokens=500, call_count=1, days=14),
        ]
        est = estimate_monthly_cost(usages)
        assert est.period_days == 14


# ── to_pydantic ──────────────────────────────────────────────────────────────


class TestToPydantic:
    def test_to_pydantic_returns_model(self):
        """to_pydantic() CostEstimateModel döndürmeli."""
        from app.domains.cost.service import CostEstimateModel
        usages = [UsagePeriod(model="gpt-4o", input_tokens=10_000, output_tokens=5_000, call_count=2, days=30)]
        est = estimate_monthly_cost(usages)
        model = to_pydantic(est)
        assert isinstance(model, CostEstimateModel)

    def test_pydantic_model_preserves_total_cost(self):
        """Pydantic modeli orijinal maliyet değerini korumalı."""
        from app.domains.cost.service import CostEstimateModel
        usages = [UsagePeriod(model="gpt-4o", input_tokens=1_000_000, output_tokens=500_000, call_count=20, days=30)]
        est = estimate_monthly_cost(usages)
        model = to_pydantic(est)
        assert model.total_cost_usd == pytest.approx(est.total_cost_usd)
