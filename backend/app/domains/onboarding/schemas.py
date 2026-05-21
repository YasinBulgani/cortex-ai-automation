"""Onboarding scorecard Pydantic şemaları."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OnboardingStep(BaseModel):
    """Tek bir onboarding adımının tanımı (sabit katalog)."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Stable ID, ör. 'create_project'")
    order: int = Field(..., ge=1, le=100)
    title: str
    description: str
    is_optional: bool = False
    action_url: Optional[str] = Field(
        None, description="Tamamlamak için gidilecek sayfa (frontend route)"
    )
    help_doc: Optional[str] = Field(
        None, description="docs/user-guide bağlantısı"
    )


class OnboardingProgress(BaseModel):
    """Bir proje için ilerleme özeti."""

    model_config = ConfigDict(extra="ignore")

    project_id: str
    steps: List[OnboardingStep]
    completed: Dict[str, bool] = Field(
        default_factory=dict,
        description="step_id → tamamlandı mı (eksik adımlar False)",
    )
    completion_pct: float = Field(
        ..., ge=0.0, le=100.0,
        description="Tamamlanma yüzdesi (zorunlu adımlar üzerinden)",
    )
    total_required: int
    completed_required: int
    is_fully_onboarded: bool = Field(
        ..., description="Tüm zorunlu adımlar tamam mı? True → widget gizlenir"
    )


class ProgressUpdateRequest(BaseModel):
    """PATCH body."""

    project_id: str = Field(..., min_length=1, max_length=120)
    step_id: str = Field(..., min_length=1, max_length=80)
    done: bool = True
