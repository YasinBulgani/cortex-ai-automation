"""Aylık maliyet tahmini servisi.

İki kaynak tüketim verisi destekler:
    1. ``UsagePeriod`` — istemci doğrudan toplam token'ları verir (test, tahmin)
    2. (gelecek) DB üzerindeki execution log'dan otomatik toplama — ayrı PR

Ayrıca ``project_potential_savings`` fonksiyonu "eğer Ollama'ya geçerseniz
X tasarruf edersiniz" hesaplar; dashboard CTA'sı için.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domains.cost.pricing import (
    PRICING_CATALOG,
    PricingEntry,
    estimate_cost_usd,
    get_pricing,
)


DEFAULT_USD_TO_TRY = 40.0   # Ballpark Nisan 2026 — env override önerilir


def _usd_to_try_rate() -> float:
    raw = os.environ.get("USD_TO_TRY")
    if not raw:
        return DEFAULT_USD_TO_TRY
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_USD_TO_TRY


@dataclass
class UsagePeriod:
    """Bir modelin bir dönem (default 30 gün) içindeki kullanım özeti."""

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    call_count: int = 0
    days: int = 30


@dataclass
class ProviderCost:
    """Model/provider bazında maliyet dökümü."""

    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    call_count: int
    days: int
    cost_usd: float
    cost_try: float
    is_local: bool


@dataclass
class CostEstimate:
    """Tüm dönem için özet."""

    total_cost_usd: float
    total_cost_try: float
    usd_to_try_rate: float
    breakdown: List[ProviderCost]
    local_alternative_cost_usd: float         # Aynı yükü lokal Ollama'da yapsak
    potential_monthly_savings_usd: float      # Toplam - lokal_alt
    period_days: int
    projected_monthly_usd: float              # 30 güne ölçeklenmiş


# ── Pydantic API modelleri ─────────────────────────────────────────────────


class ProviderCostModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    call_count: int
    days: int
    cost_usd: float
    cost_try: float
    is_local: bool


class CostEstimateModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_cost_usd: float
    total_cost_try: float
    usd_to_try_rate: float
    breakdown: List[ProviderCostModel]
    local_alternative_cost_usd: float
    potential_monthly_savings_usd: float
    period_days: int
    projected_monthly_usd: float


class UsagePeriodInput(BaseModel):
    """Analyze endpoint'inin gövdesi."""

    model: str = Field(..., description="Model adı (pricing catalog anahtarı)")
    input_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(0, ge=0)
    call_count: int = Field(0, ge=0)
    days: int = Field(30, ge=1, le=365)


# ── Core hesap ─────────────────────────────────────────────────────────────


def _scale_to_monthly(cost: float, days: int) -> float:
    if days <= 0:
        return 0.0
    return round(cost * (30.0 / days), 4)


def estimate_monthly_cost(usages: List[UsagePeriod]) -> CostEstimate:
    """Kullanım listesinden toplam maliyet + tasarruf fırsatı üret.

    Kurallar:
      - Lokal modellerin maliyeti 0 sayılır
      - Farklı dönemler farklı 'days' verdiyse projected_monthly_usd
        30 güne normalize edilir (breakdown olduğu gibi kalır)
      - local_alternative_cost_usd: her model için 'is_local=True' varsayılarak
        hesaplanan alternatif → hep 0 (ama alan yine raporlanır,
        gelecek iterasyonda "elektrik maliyeti" vb. modellenebilir)
    """
    usd_try = _usd_to_try_rate()
    breakdown: List[ProviderCost] = []
    total_usd = 0.0
    total_days_max = 0

    for u in usages:
        pricing: PricingEntry = get_pricing(u.model)
        cost_usd = estimate_cost_usd(
            u.model, input_tokens=u.input_tokens, output_tokens=u.output_tokens
        )
        total_usd += cost_usd
        total_days_max = max(total_days_max, u.days)
        breakdown.append(
            ProviderCost(
                model=u.model,
                provider=pricing.provider,
                input_tokens=u.input_tokens,
                output_tokens=u.output_tokens,
                call_count=u.call_count,
                days=u.days,
                cost_usd=round(cost_usd, 4),
                cost_try=round(cost_usd * usd_try, 2),
                is_local=pricing.is_local,
            )
        )

    local_alt = 0.0   # Lokal modelin birim maliyeti 0 → alternatif 0
    projected = _scale_to_monthly(total_usd, total_days_max or 30)

    return CostEstimate(
        total_cost_usd=round(total_usd, 4),
        total_cost_try=round(total_usd * usd_try, 2),
        usd_to_try_rate=usd_try,
        breakdown=breakdown,
        local_alternative_cost_usd=local_alt,
        potential_monthly_savings_usd=round(projected - local_alt, 4),
        period_days=total_days_max or 30,
        projected_monthly_usd=projected,
    )


def to_pydantic(est: CostEstimate) -> CostEstimateModel:
    """CostEstimate → Pydantic (HTTP response için)."""
    data = asdict(est)
    return CostEstimateModel.model_validate(data)
