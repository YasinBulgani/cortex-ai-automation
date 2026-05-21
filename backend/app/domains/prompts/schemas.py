"""Prompts domain Pydantic şemaları.

Ayrımlar:
    * *In: dışarıdan gelen upsert payload'u
    * *Out: API cevabı (+ read-only alanlar: timestamps, version no)
    * Rollout ayrı modelde — bir prompt'un birden çok env'de farklı rollout
      durumu olabilir.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


Env = Literal["prod", "staging", "dev"]


class PromptIn(BaseModel):
    """Prompt create/update (version'sız meta)."""

    description: str = ""
    task_type: Optional[str] = None

    @field_validator("task_type")
    @classmethod
    def _strip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class PromptOut(BaseModel):
    id: str
    description: str = ""
    task_type: Optional[str] = None
    archived: bool = False
    created_at: datetime
    created_by: Optional[str] = None
    updated_at: datetime
    latest_version: Optional[int] = None


class PromptVersionIn(BaseModel):
    """Yeni bir versiyon ekle."""

    system_prompt: str = ""
    user_template: str = ""
    model_hint: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=200_000)
    notes: Optional[str] = None


class PromptVersionOut(BaseModel):
    id: int
    prompt_id: str
    version: int
    system_prompt: str
    user_template: str
    model_hint: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None


class RolloutIn(BaseModel):
    """Rollout upsert — active + canary.

    Validasyon:
        * ``canary_pct > 0`` ise ``canary_version`` zorunlu
        * ``canary_version == active_version`` ise semantik anlamsız ama
          reddedilmez (operator kasten aynı tutabilir — geçici güvenli durum)
    """

    active_version: int = Field(ge=1)
    canary_version: Optional[int] = Field(default=None, ge=1)
    canary_pct: int = Field(default=0, ge=0, le=100)

    @field_validator("canary_pct")
    @classmethod
    def _canary_pct_needs_version(cls, v: int, info) -> int:
        values = info.data
        if v > 0 and values.get("canary_version") is None:
            raise ValueError(
                "canary_pct > 0 için canary_version zorunlu"
            )
        return v


class RolloutOut(BaseModel):
    prompt_id: str
    env: Env
    active_version: int
    canary_version: Optional[int] = None
    canary_pct: int = 0
    updated_at: datetime
    updated_by: Optional[str] = None


class ResolvedPrompt(BaseModel):
    """Bir çağrı için çözülmüş prompt — caller bu nesne ile LLM'e gider.

    ``decision_reason``:
        "active"          → canary kapalı veya trafik yüzdeye düşmedi
        "canary_allowlist"→ henüz yok, reserved
        "canary_percent"  → canary_pct üstünden hit
        "fallback_active" → canary versiyon kaydı bozuksa active'e fallback
    """

    prompt_id: str
    env: Env
    version: int
    system_prompt: str
    user_template: str
    model_hint: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    decision_reason: str
    active_version: int
    canary_version: Optional[int] = None
    canary_pct: int = 0
