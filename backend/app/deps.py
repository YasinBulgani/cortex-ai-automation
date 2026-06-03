"""FastAPI bağımlılıkları."""

from __future__ import annotations

from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

import jwt

from app.domains.auth.service import decode_token
from app.infra.database import get_db
from app.infra.models import User

security = HTTPBearer(auto_error=False)
ACCESS_TOKEN_COOKIE = "bgts_access_token"


def _resolve_bearer_token(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if creds is not None and creds.credentials:
        return creds.credentials
    return request.cookies.get(ACCESS_TOKEN_COOKIE)


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> User:
    token = _resolve_bearer_token(request, creds)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama gerekli",
        )
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
        ) from None
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz token")
    user = db.get(User, sub)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı")
    return user


def _user_permissions(user: User) -> set[str]:
    perms: set[str] = set()
    for role in (user.roles or []):
        for rp in (role.permissions or []):
            perm_value = getattr(rp, "permission", None)
            if perm_value:
                perms.add(perm_value)
    return perms


def require_permission(perm: str) -> Callable:
    def dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        perms = _user_permissions(user)
        if "admin.*" in perms or perm in perms:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Bu işlem için yetkiniz yok: {perm}",
        )
    return dependency


# ── Project-level ACL ─────────────────────────────────────────────
# Project member roles -> set of permission strings that override globals
_PROJECT_ROLE_PERMS: dict[str, set[str]] = {
    "viewer": {
        "project.read",
        "scenario.read",
        "test_management.read",
    },
    "member": {
        "project.read",
        "scenario.read",
        "scenario.create",
        "scenario.update",
        "test_management.read",
        "test_management.write",
        "execution.create",
    },
    "operator": {
        "project.read",
        "project.update",
        "scenario.create",
        "scenario.read",
        "scenario.update",
        "scenario.delete",
        "execution.create",
        "execution.update",
        "test_management.read",
        "test_management.write",
        "test_management.execute",
        "approval.decide",
    },
    "admin": {"admin.*"},
}


def resolve_project_permissions(
    db: Session, user: User, project_id: str
) -> set[str]:
    """Compute effective permissions = global role perms ∪ project member perms."""
    perms = _user_permissions(user)
    from app.infra.models import ProjectMember
    pm = db.get(ProjectMember, (project_id, user.id))
    if pm is not None:
        perms = perms | _PROJECT_ROLE_PERMS.get(pm.role, set())
    return perms


def require_project_permission(perm: str) -> Callable:
    """Permission check augmented with project membership.

    The route must accept `project_id` as a path or query param; FastAPI binds
    it via the dependency signature below.
    """
    def dependency(
        project_id: str,
        user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> User:
        effective = resolve_project_permissions(db, user, project_id)
        if "admin.*" in effective or perm in effective:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Proje icin yetkiniz yok: {perm}",
        )
    return dependency


def get_optional_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> Optional[User]:
    """Token varsa kullanıcı döndür, yoksa None."""
    token = _resolve_bearer_token(request, creds)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    user = db.get(User, sub)
    if user is None or not user.is_active:
        return None
    return user
