"""Cost estimator + pricing kataloğu için birim testler — UX-F2-205."""
from __future__ import annotations

import pytest

from app.domains.cost.pricing import (
    DEFAULT_PRICING,
    PRICING_CATALOG,
    estimate_cost_usd,
    get_pricing,
)
from app.domains.cost.service import (
    UsagePeriod,
    estimate_monthly_cost,
    to_pydantic,
)


# ── Pricing catalog bütünlüğü ────────────────────────────────────────────


def test_catalog_not_empty() -> None:
    assert len(PRICING_CATALOG) >= 15


def test_every_entry_has_required_fields() -> None:
    for model, entry in PRICING_CATALOG.items():
        assert entry.model == model, f"{model}: entry.model mismatch"
        assert entry.provider, f"{model}: provider yok"
        assert entry.input_per_mtoken_usd >= 0
        assert entry.output_per_mtoken_usd >= 0


def test_local_models_have_zero_price() -> None:
    for entry in PRICING_CATALOG.values():
        if entry.is_local:
            assert entry.input_per_mtoken_usd == 0.0
            assert entry.output_per_mtoken_usd == 0.0


def test_cloud_models_have_positive_price() -> None:
    for entry in PRICING_CATALOG.values():
        if not entry.is_local:
            assert entry.input_per_mtoken_usd > 0
            assert entry.output_per_mtoken_usd > 0


# ── get_pricing ──────────────────────────────────────────────────────────


def test_get_pricing_exact_match() -> None:
    p = get_pricing("gpt-5")
    assert p.provider == "openai"
    assert p.input_per_mtoken_usd == 1.25


def test_get_pricing_unknown_falls_back() -> None:
    p = get_pricing("random-model-xyz")
    assert p is DEFAULT_PRICING


def test_get_pricing_empty_returns_default() -> None:
    assert get_pricing("") is DEFAULT_PRICING


def test_get_pricing_ollama_quant_normalization() -> None:
    """Ollama isimleri 'qwen2.5-coder:14b-instruct-q4_K_M' gibi gelebilir."""
    p = get_pricing("qwen2.5-coder:14b-instruct-q4_K_M")
    assert p.is_local is True
    assert p.model == "qwen2.5-coder:14b"


# ── estimate_cost_usd ────────────────────────────────────────────────────


def test_estimate_cost_local_is_zero() -> None:
    assert estimate_cost_usd(
        "qwen2.5-coder:7b", input_tokens=1_000_000, output_tokens=500_000
    ) == 0.0


def test_estimate_cost_gpt5_known() -> None:
    # 1M input * $1.25 + 1M output * $10.00 = $11.25
    cost = estimate_cost_usd(
        "gpt-5", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert cost == pytest.approx(11.25, rel=1e-6)


def test_estimate_cost_small_rounded() -> None:
    # 500 input * $1.25/M + 100 output * $10/M = 0.000625 + 0.001 = 0.001625
    cost = estimate_cost_usd("gpt-5", input_tokens=500, output_tokens=100)
    assert cost == pytest.approx(0.001625, rel=1e-6)


# ── estimate_monthly_cost (service) ──────────────────────────────────────


def test_single_cloud_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USD_TO_TRY", "40.0")
    usages = [
        UsagePeriod(
            model="gpt-5",
            input_tokens=2_000_000,
            output_tokens=500_000,
            call_count=100,
            days=30,
        )
    ]
    # 2M * 1.25 = 2.5, 0.5M * 10 = 5.0, total = 7.5 USD = 300 TRY
    est = estimate_monthly_cost(usages)
    assert est.total_cost_usd == pytest.approx(7.5, rel=1e-3)
    assert est.total_cost_try == pytest.approx(300.0, rel=1e-3)
    assert est.usd_to_try_rate == 40.0
    assert len(est.breakdown) == 1
    assert est.breakdown[0].provider == "openai"
    assert est.breakdown[0].is_local is False


def test_mixed_local_and_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USD_TO_TRY", "40.0")
    usages = [
        UsagePeriod(model="gpt-5", input_tokens=1_000_000, output_tokens=500_000, days=30),
        UsagePeriod(model="qwen2.5-coder:14b", input_tokens=10_000_000, output_tokens=5_000_000, days=30),
    ]
    est = estimate_monthly_cost(usages)
    # Sadece gpt-5 sayılır: 1M*1.25 + 0.5M*10 = 6.25
    assert est.total_cost_usd == pytest.approx(6.25, rel=1e-3)
    # Breakdown 2 satır ama biri local
    assert len(est.breakdown) == 2
    local = next(b for b in est.breakdown if b.is_local)
    cloud = next(b for b in est.breakdown if not b.is_local)
    assert local.cost_usd == 0.0
    assert cloud.cost_usd > 0


def test_projected_monthly_scaling(monkeypatch: pytest.MonkeyPatch) -> None:
    """7 günlük veri verilirse 30 güne ölçeklenir."""
    monkeypatch.setenv("USD_TO_TRY", "40.0")
    usages = [UsagePeriod(model="gpt-5", input_tokens=1_000_000, output_tokens=0, days=7)]
    # 1M * 1.25 = 1.25 USD (7 gün)
    # projected = 1.25 * (30/7) ≈ 5.357
    est = estimate_monthly_cost(usages)
    assert est.total_cost_usd == pytest.approx(1.25, rel=1e-3)
    assert est.projected_monthly_usd == pytest.approx(5.357, rel=1e-2)
    assert est.period_days == 7


def test_all_local_zero_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USD_TO_TRY", "40.0")
    usages = [
        UsagePeriod(model="qwen2.5-coder:14b", input_tokens=10_000_000, output_tokens=5_000_000),
        UsagePeriod(model="bge-m3", input_tokens=1_000_000, output_tokens=0),
    ]
    est = estimate_monthly_cost(usages)
    assert est.total_cost_usd == 0.0
    assert est.total_cost_try == 0.0
    assert est.potential_monthly_savings_usd == 0.0


def test_usd_to_try_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USD_TO_TRY", "50.0")
    usages = [UsagePeriod(model="gpt-5-nano", input_tokens=1_000_000, output_tokens=1_000_000)]
    # 1M * 0.05 + 1M * 0.40 = 0.45 USD → 22.50 TRY
    est = estimate_monthly_cost(usages)
    assert est.total_cost_usd == pytest.approx(0.45, rel=1e-3)
    assert est.total_cost_try == pytest.approx(22.50, rel=1e-3)


def test_unknown_rate_default_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """USD_TO_TRY geçersizse DEFAULT_USD_TO_TRY kullanılır."""
    monkeypatch.setenv("USD_TO_TRY", "notanumber")
    usages = [UsagePeriod(model="gpt-5", input_tokens=1_000_000, output_tokens=0)]
    est = estimate_monthly_cost(usages)
    assert est.usd_to_try_rate == 40.0   # DEFAULT


def test_to_pydantic_shape() -> None:
    usages = [UsagePeriod(model="gpt-5", input_tokens=1_000_000, output_tokens=100_000)]
    est = estimate_monthly_cost(usages)
    model = to_pydantic(est)
    assert model.total_cost_usd == est.total_cost_usd
    assert len(model.breakdown) == 1
