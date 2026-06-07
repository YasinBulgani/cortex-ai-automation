"""Admin domain router.

Neurex yönetici endpoint'leri. Tüm işlemler ``admin.*`` yetkisi gerektirir.
Auth domain'deki user CRUD, organizations'taki team listeleme ve rbac'taki
roller bu router üzerinden de /api/v1/admin/* altında sunulur.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import User

CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User) -> None:
    """Kullanıcının admin yetkisine sahip olduğunu doğrular."""
    from app.deps import _user_permissions

    perms = _user_permissions(user)
    if "admin.*" not in perms and "system.admin" not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için admin yetkisi gereklidir.",
        )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users", summary="Tüm kullanıcıları listele (admin)")
def admin_list_users(user: Annotated[User, Depends(get_current_user)], db: DB) -> list[dict]:
    """Sistemdeki tüm kullanıcıları döner. ``admin.*`` yetkisi gerektirir."""
    _require_admin(user)

    users = list(
        db.scalars(
            select(User).options(joinedload(User.roles)).order_by(User.created_at.desc())
        ).unique()
    )
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": getattr(u, "full_name", None),
            "department": getattr(u, "department", None),
            "is_active": getattr(u, "is_active", True),
            "roles": [r.name for r in getattr(u, "roles", [])],
            "created_at": str(u.created_at) if u.created_at else None,
        }
        for u in users
    ]


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@router.get("/teams", summary="Tüm takımları listele (admin)")
def admin_list_teams(user: Annotated[User, Depends(get_current_user)], db: DB) -> list[dict]:
    """Tüm organizasyon takımlarını döner. ``admin.*`` yetkisi gerektirir."""
    _require_admin(user)

    from app.infra.models import Team

    teams = list(db.scalars(select(Team).order_by(Team.name)))
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "organization_id": str(t.organization_id) if hasattr(t, "organization_id") else None,
            "description": getattr(t, "description", None),
            "created_at": str(t.created_at) if hasattr(t, "created_at") and t.created_at else None,
        }
        for t in teams
    ]


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


@router.get("/roles", summary="Tüm rolleri listele (admin)")
def admin_list_roles(user: Annotated[User, Depends(get_current_user)], db: DB) -> list[dict]:
    """Tanımlı tüm rolleri ve izinlerini döner. ``admin.*`` yetkisi gerektirir."""
    _require_admin(user)

    from app.infra.models import Role

    roles = list(
        db.scalars(select(Role).options(joinedload(Role.permissions)).order_by(Role.name)).unique()
    )
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "permissions": [p.permission for p in r.permissions],
        }
        for r in roles
    ]
