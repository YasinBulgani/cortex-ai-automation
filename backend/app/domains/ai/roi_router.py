"""ROI REST API — tenant × günlük harcama → net kazanç raporu."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user, require_permission
from app.infra.models import User

from .roi_service import ROISummary, format_weekly_report, get_roi_summary

router = APIRouter(prefix="/roi", tags=["roi"])


_ADMIN_PERM = "admin.roi"


@router.get("/me", response_model=ROISummary)
def _my_roi(
    user: Annotated[User, Depends(get_current_user)],
    days: int = Query(default=30, ge=1, le=365),
) -> ROISummary:
    tenant = str(getattr(user, "tenant_id", None) or user.id)
    return get_roi_summary(tenant, days=days)


@router.get("/summary", response_model=ROISummary)
def _summary(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    tenant: Optional[str] = Query(default=None, description="Boş → tüm tenant'lar"),
    days: int = Query(default=30, ge=1, le=365),
) -> ROISummary:
    return get_roi_summary(tenant, days=days)


@router.get("/report/weekly.txt", response_class=None)
def _weekly_txt(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    tenant: Optional[str] = Query(default=None),
) -> str:
    """Plain-text haftalık rapor (PDF render sonraki sprint)."""
    summary = get_roi_summary(tenant, days=7)
    return format_weekly_report(summary)
