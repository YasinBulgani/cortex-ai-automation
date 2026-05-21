"""Feature flag yönetim API'si.

Endpoints:
    GET    /feature-flags                  → tüm flag'leri listele (admin)
    GET    /feature-flags/{key}            → tek flag detayı (admin)
    PUT    /feature-flags/{key}            → partial update / upsert (admin)
    DELETE /feature-flags/{key}            → sil (admin)
    GET    /feature-flags/evaluate/{key}   → bir tenant için karar + neden

``evaluate`` endpoint'i admin olmayan kullanıcılar için de açık — frontend UI
kendi tenant'ı için flag değerini öğrenir. Diğerleri admin yetkisi ister.
"""
from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_current_user, require_permission
from app.infra.models import User

from .schemas import FlagEvaluation, FlagOut, FlagUpdate
from .service import feature_flags

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


_ADMIN_PERM = "admin.feature_flags"


@router.get("", response_model=List[FlagOut])
def list_flags(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> List[FlagOut]:
    return feature_flags.list_flags()


@router.get("/evaluate/{key}", response_model=FlagEvaluation)
def evaluate_flag(
    key: str,
    user: Annotated[User, Depends(get_current_user)],
    tenant: Optional[str] = Query(
        default=None,
        description=(
            "Değerlendirilecek tenant. Verilmezse kullanıcının kendi tenant'ı. "
            "Anonim bucket'lı canary'de boş bırakmayın."
        ),
    ),
) -> FlagEvaluation:
    resolved_tenant = tenant or getattr(user, "tenant_id", None) or str(user.id)
    return feature_flags.evaluate(key, tenant_id=str(resolved_tenant))


@router.get("/{key}", response_model=FlagOut)
def get_flag(
    key: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> FlagOut:
    out = feature_flags.get(key)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag bulunamadı")
    return out


@router.put("/{key}", response_model=FlagOut)
def upsert_flag(
    key: str,
    payload: FlagUpdate,
    user: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> FlagOut:
    try:
        return feature_flags.set_flag(
            key, payload, actor=getattr(user, "email", None) or str(user.id)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flag(
    key: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> None:
    deleted = feature_flags.delete(key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag bulunamadı")
