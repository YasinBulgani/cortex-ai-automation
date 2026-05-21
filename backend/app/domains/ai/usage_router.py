"""AI kullanım + bütçe REST API'si.

Endpoints:
    GET    /ai/usage                      → kullanıcının kendi tenant'ı için rapor
    GET    /ai/usage/summary?tenant=X     → admin için any tenant
    GET    /ai/budget                     → tüm politikalar (admin)
    GET    /ai/budget/{tenant_id}         → tek politika (admin veya kendisi)
    PUT    /ai/budget/{tenant_id}         → upsert (admin)
    DELETE /ai/budget/{tenant_id}         → sil (admin)
    GET    /ai/budget/check/{tenant_id}   → anlık bütçe durumu (admin)

Tenant proxy: User modelinde henüz tenant_id alanı yok — fallback olarak
user.id kullanılır. Multi-tenant modeline geçişte bu router değişmeden
çalışmalı çünkü ``getattr(user, 'tenant_id', user.id)`` pattern'i koruyor.
"""
from __future__ import annotations

from typing import Annotated, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.deps import get_current_user, require_permission
from app.infra.models import User

from .budget import (
    BudgetPolicyIn,
    BudgetPolicyOut,
    BudgetStatus,
    check_budget,
    delete_policy,
    get_policy,
    list_policies,
    upsert_policy,
)
from .usage_service import get_tenant_usage

router = APIRouter(prefix="/ai", tags=["ai-usage"])


_ADMIN_PERM = "admin.ai_usage"


def _resolve_tenant(user: User) -> str:
    return str(getattr(user, "tenant_id", None) or user.id)


# ── Usage ─────────────────────────────────────────────────────────────────


@router.get("/usage")
def my_usage(
    user: Annotated[User, Depends(get_current_user)],
    days: int = Query(default=7, ge=1, le=90),
    group_by: Literal["day", "model", "provider"] = Query(default="day"),
) -> dict:
    tenant = _resolve_tenant(user)
    return get_tenant_usage(tenant, days=days, group_by=group_by)


@router.get("/usage/summary")
def any_tenant_usage(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    tenant: Optional[str] = Query(default=None, description="Boş → tüm tenant'lar"),
    days: int = Query(default=7, ge=1, le=90),
    group_by: Literal["day", "model", "provider"] = Query(default="day"),
) -> dict:
    return get_tenant_usage(tenant or "", days=days, group_by=group_by)


# ── Budget policies ───────────────────────────────────────────────────────


class BudgetStatusOut(BaseModel):
    tenant_id: str
    allowed: bool
    reason: str
    today_usd: float
    daily_cap_usd: float
    notify_at_pct: int
    hard_cap: bool
    pct_used: float


def _status_to_out(tenant_id: str, s: BudgetStatus) -> BudgetStatusOut:
    return BudgetStatusOut(
        tenant_id=tenant_id,
        allowed=s.allowed,
        reason=s.reason,
        today_usd=s.today_usd,
        daily_cap_usd=s.daily_cap_usd,
        notify_at_pct=s.notify_at_pct,
        hard_cap=s.hard_cap,
        pct_used=s.pct_used(),
    )


@router.get("/budget", response_model=List[BudgetPolicyOut])
def list_budget_policies(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> List[BudgetPolicyOut]:
    return list_policies()


@router.get("/budget/check/{tenant_id}", response_model=BudgetStatusOut)
def budget_status(
    tenant_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> BudgetStatusOut:
    status_ = check_budget(tenant_id)
    return _status_to_out(tenant_id, status_)


@router.get("/budget/me", response_model=BudgetStatusOut)
def my_budget_status(
    user: Annotated[User, Depends(get_current_user)],
) -> BudgetStatusOut:
    tenant = _resolve_tenant(user)
    return _status_to_out(tenant, check_budget(tenant))


@router.get("/budget/{tenant_id}", response_model=BudgetPolicyOut)
def get_budget_policy(
    tenant_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> BudgetPolicyOut:
    out = get_policy(tenant_id)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Politika yok")
    return out


@router.put("/budget/{tenant_id}", response_model=BudgetPolicyOut)
def upsert_budget_policy(
    tenant_id: str,
    payload: BudgetPolicyIn,
    user: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> BudgetPolicyOut:
    try:
        return upsert_policy(
            tenant_id, payload, actor=getattr(user, "email", None) or str(user.id)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete("/budget/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_policy(
    tenant_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> None:
    if not delete_policy(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Politika yok")
