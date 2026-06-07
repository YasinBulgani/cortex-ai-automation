"""Onboarding scorecard HTTP endpoint'leri."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import _user_permissions, get_current_user
from app.domains.onboarding.schemas import (
    OnboardingProgress,
    ProgressUpdateRequest,
)
from app.domains.onboarding.service import (
    DEFAULT_STEPS,
    compute_progress,
    progress_store,
)
from app.infra.database import get_db
from app.infra.models import User


def _check_project_access(project_id: str, db: Session, user: User) -> None:
    from app.domains.tspm.models import TspmProject, TspmProjectMember
    if db.get(TspmProject, project_id) is None:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    if "admin.*" in _user_permissions(user):
        return
    is_member = db.scalar(
        select(func.count()).where(
            TspmProjectMember.project_id == project_id,
            TspmProjectMember.user_id == user.id,
        )
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="Bu projeye erişim yetkiniz yok")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get(
    "/steps",
    summary="Onboarding adım kataloğu (sabit)",
)
def steps():
    """Public endpoint — no auth required."""
    try:
        return {"total": len(DEFAULT_STEPS), "steps": [s.model_dump() for s in DEFAULT_STEPS]}
    except Exception as e:
        logger.error("onboarding steps failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/status",
    summary="Mevcut kullanıcının onboarding durumu",
)
def status(user: Annotated[User, Depends(get_current_user)]):
    """Kullanıcının onboarding tamamlanma durumunu döner.

    Frontend bu endpoint'i kullanarak onboarding widget'ını gösterip
    göstermeyeceğine karar verir.
    """
    try:
        # Global onboarding — proje ID olmadan genel durum
        project_id = str(getattr(user, "id", "global"))
        completed = progress_store.get(project_id)
        progress = compute_progress(project_id=project_id, completed=completed)
        return {
            "is_onboarded": progress.is_fully_onboarded,
            "completion_pct": progress.completion_pct,
            "completed_required": progress.completed_required,
            "total_required": progress.total_required,
            "project_id": project_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("onboarding status failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/checklist",
    summary="Onboarding yapılacaklar listesi",
)
def checklist(user: Annotated[User, Depends(get_current_user)]):
    """Onboarding adımlarını tamamlanma durumu ile birlikte döner.

    Her adım için ``done`` alanı tamamlanıp tamamlanmadığını gösterir.
    """
    try:
        project_id = str(getattr(user, "id", "global"))
        completed = progress_store.get(project_id)
        progress = compute_progress(project_id=project_id, completed=completed)

        items = []
        for step in progress.steps:
            items.append({
                "id": step.id,
                "title": step.title,
                "description": step.description,
                "is_optional": step.is_optional,
                "done": progress.completed.get(step.id, False),
                "action_url": step.action_url,
                "order": step.order,
            })

        return {
            "project_id": project_id,
            "items": items,
            "completion_pct": progress.completion_pct,
            "is_fully_onboarded": progress.is_fully_onboarded,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("onboarding checklist failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/progress/{project_id}",
    response_model=OnboardingProgress,
    summary="Proje için tamamlanma özeti",
)
def progress(
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    project_id: str = Path(..., min_length=1, max_length=120),
):
    try:
        _check_project_access(project_id, db, user)
        completed = progress_store.get(project_id)
        return compute_progress(project_id=project_id, completed=completed)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("onboarding progress(%s) failed: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/progress",
    response_model=OnboardingProgress,
    summary="Tek bir adımın tamamlanma durumunu güncelle",
)
def update(req: ProgressUpdateRequest, user: Annotated[User, Depends(get_current_user)]):
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("onboarding update failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/progress/{project_id}",
    summary="Proje için onboarding state'i sıfırla (test/admin)",
)
def reset(
    user: Annotated[User, Depends(get_current_user)],
    project_id: str = Path(..., min_length=1, max_length=120),
):
    try:
        if "admin.*" not in _user_permissions(user):
            raise HTTPException(403, "Admin yetkisi gerekli")
        progress_store.reset(project_id)
        return {"ok": True, "project_id": project_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("onboarding reset(%s) failed: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
