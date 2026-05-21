"""Onboarding scorecard HTTP endpoint'leri."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from app.domains.onboarding.schemas import (
    OnboardingProgress,
    ProgressUpdateRequest,
)
from app.domains.onboarding.service import (
    DEFAULT_STEPS,
    compute_progress,
    progress_store,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get(
    "/steps",
    summary="Onboarding adım kataloğu (sabit)",
)
def steps():
    return {"total": len(DEFAULT_STEPS), "steps": [s.model_dump() for s in DEFAULT_STEPS]}


@router.get(
    "/progress/{project_id}",
    response_model=OnboardingProgress,
    summary="Proje için tamamlanma özeti",
)
def progress(project_id: str = Path(..., min_length=1, max_length=120)):
    completed = progress_store.get(project_id)
    return compute_progress(project_id=project_id, completed=completed)


@router.patch(
    "/progress",
    response_model=OnboardingProgress,
    summary="Tek bir adımın tamamlanma durumunu güncelle",
)
def update(req: ProgressUpdateRequest):
    # Adım ID doğrula — uydurma step_id kabul etme
    valid_ids = {s.id for s in DEFAULT_STEPS}
    if req.step_id not in valid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Bilinmeyen step_id: {req.step_id}. "
                   f"Geçerli: {sorted(valid_ids)}",
        )
    progress_store.set(req.project_id, req.step_id, req.done)
    completed = progress_store.get(req.project_id)
    return compute_progress(project_id=req.project_id, completed=completed)


@router.delete(
    "/progress/{project_id}",
    summary="Proje için onboarding state'i sıfırla (test/admin)",
)
def reset(project_id: str = Path(..., min_length=1, max_length=120)):
    progress_store.reset(project_id)
    return {"ok": True, "project_id": project_id}
