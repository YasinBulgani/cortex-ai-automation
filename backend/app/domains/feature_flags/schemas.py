"""Feature flag domain için Pydantic şemaları.

Model:
    * FlagState   : tek bir bayrağın persist edilen durumu
    * FlagUpdate  : set/update için gelen request body
    * FlagOut     : API dışına açılan görünür alanlar
    * RolloutOut  : canary yüzdesini + tenant allow-list'i taşır

Tasarım:
    * Canary rollout: ``percent`` 0-100, ``allow_tenants`` explicit beyaz liste.
      Her ikisi de beraber kullanılabilir (tenant beyaz listede ise yüzde
      ne olursa olsun açık; değilse yüzde hash'e göre karar verilir).
    * Her flag'in kısa bir ``description`` alanı var — UI'da operator
      hangi epic için neyin değiştiğini görsün diye.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RolloutOut(BaseModel):
    percent: int = Field(default=0, ge=0, le=100)
    allow_tenants: List[str] = Field(default_factory=list)


class FlagOut(BaseModel):
    """UI'ya/operator'a açılan temsil."""

    key: str
    enabled: bool
    description: str = ""
    rollout: RolloutOut = Field(default_factory=RolloutOut)
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class FlagUpdate(BaseModel):
    """PUT /feature-flags/{key} body — kısmi güncelleme."""

    enabled: Optional[bool] = None
    description: Optional[str] = None
    percent: Optional[int] = Field(default=None, ge=0, le=100)
    allow_tenants: Optional[List[str]] = None

    @field_validator("allow_tenants")
    @classmethod
    def _strip_tenants(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        cleaned = [t.strip() for t in v if t and t.strip()]
        seen: set[str] = set()
        out: List[str] = []
        for t in cleaned:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out


class FlagEvaluation(BaseModel):
    """``GET /feature-flags/evaluate/{key}?tenant=...`` cevabı.

    Sadece bool değil, kararın nedenini de döner — debug + audit için değerli.
    """

    key: str
    enabled: bool
    reason: str  # "disabled" | "tenant_allowlist" | "rollout_percent" | "not_found"
    percent: int = 0
