"""Cost estimator HTTP endpoint.

Yollar:
    GET  /api/v1/cost/pricing      → fiyat tablosu (tüm provider'lar)
    POST /api/v1/cost/estimate     → kullanım → maliyet tahmini
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domains.cost.pricing import PRICING_CATALOG
from app.domains.cost.service import (
    CostEstimateModel,
    UsagePeriod,
    UsagePeriodInput,
    estimate_monthly_cost,
    to_pydantic,
)

router = APIRouter(prefix="/cost", tags=["cost"])


class PricingRow(BaseModel):
    model: str
    provider: str
    input_per_mtoken_usd: float
    output_per_mtoken_usd: float
    is_local: bool
    is_free_tier_available: bool
    notes: str = ""


class PricingCatalogResponse(BaseModel):
    entries: List[PricingRow]
    total: int


@router.get(
    "/pricing",
    response_model=PricingCatalogResponse,
    summary="Tüm LLM provider fiyatları (USD / 1M token)",
)
def pricing() -> PricingCatalogResponse:
    entries = [
        PricingRow(
            model=p.model,
            provider=p.provider,
            input_per_mtoken_usd=p.input_per_mtoken_usd,
            output_per_mtoken_usd=p.output_per_mtoken_usd,
            is_local=p.is_local,
            is_free_tier_available=p.is_free_tier_available,
            notes=p.notes or "",
        )
        for p in PRICING_CATALOG.values()
    ]
    # Lokal olanlar sona, provider bazında grupla, sonra fiyata göre sırala
    entries.sort(key=lambda e: (e.is_local, e.provider, e.input_per_mtoken_usd))
    return PricingCatalogResponse(entries=entries, total=len(entries))


class EstimateRequest(BaseModel):
    usages: List[UsagePeriodInput] = Field(
        ..., min_length=1, description="En az bir model kullanımı"
    )


@router.post(
    "/estimate",
    response_model=CostEstimateModel,
    summary="Kullanım listesinden aylık maliyet tahmini",
)
def estimate(req: EstimateRequest) -> CostEstimateModel:
    usages: List[UsagePeriod] = [
        UsagePeriod(
            model=u.model,
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            call_count=u.call_count,
            days=u.days,
        )
        for u in req.usages
    ]
    est = estimate_monthly_cost(usages)
    return to_pydantic(est)
