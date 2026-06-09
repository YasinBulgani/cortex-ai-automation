"""FastAPI bağımlılıkları."""

from __future__ import annotations

from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

import jwt

from app.domains.auth.service import decode_token
from app.infra.database import get_db, get_read_db
from app.infra.models import User
from app.infra.read_replica import mark_write_occurred

security = HTTPBearer(auto_error=False)
ACCESS_TOKEN_COOKIE = "bgts_access_token"


def _resolve_bearer_token(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """S-HIGH-6: Token resolution priority matrix.

    Priority (highest to lowest):
    1. Authorization: Bearer header (most secure, explicit)
    2. Cookie (convenience, less secure if XSS occurs)

    Rationale: Header takes precedence because it's:
    - Not subject to CSRF on same-site (unlike cookies)
    - Explicitly provided (opt-in)
    - Default for API clients (curl, axios, fetch with credentials)
    """
    if creds is not None and creds.credentials:
        return creds.credentials
    return request.cookies.get(ACCESS_TOKEN_COOKIE)


def _assert_tenant_consistency(request: Request, payload: dict) -> None:
    """Defense-in-depth: RLS'e bağlanan tenant, doğrulanmış token tenant'ı ile aynı olmalı.

    TenantMiddleware, hız için tenant claim'ini İMZASIZ olarak çıkarıp RLS'i
    (`SET LOCAL app.current_tenant`) ondan besler. Burada token imzası
    doğrulanmış durumda; imzalı payload'tan gelen tenant ile RLS'e bağlanan
    (imzasız) tenant uyuşmazsa istek reddedilir — fail-closed. Legitim trafikte
    ikisi aynı token'dan türediği için bu kontrol asla tetiklenmez; sapma bir
    bug veya istismar işaretidir.
    """
    from app.core.tenant_middleware import _safe_tenant_id

    claim = payload.get("tenant") or payload.get("tenant_id")
    if claim is None:
        return  # tenant claim'i olmayan token → middleware da default'a düşer; sapma yok
    verified = _safe_tenant_id(str(claim))
    bound = _safe_tenant_id(getattr(request.state, "tenant_id", None))
    if verified != bound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant bağlamı tutarsız",
        )


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
    _assert_tenant_consistency(request, payload)
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
        # S-HIGH-1: Wildcard permission validation
        # Check exact admin.* match (not substring), then specific permission
        has_admin_wildcard = "admin.*" in perms
        has_permission = perm in perms
        if has_admin_wildcard or has_permission:
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
    try:
        _assert_tenant_consistency(request, payload)
    except HTTPException:
        return None
    user = db.get(User, sub)
    if user is None or not user.is_active:
        return None
    return user


# ── Faz 3.1: Read-Replica Helpers ──────────────────────────────────────────


def track_write_on_commit(request: Request, db: Session) -> None:
    """Mark write occurred on this request (Faz 3.1: sticky read-after-write).

    Call after db.commit() to start sticky read-after-write timer.
    Next ~5s of reads (from same request context) will use primary DB.

    Args:
        request: FastAPI Request object
        db: SQLAlchemy Session (sync or async)
    """
    mark_write_occurred(request)


async def get_read_db_async(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Async read-optimized database session (Faz 3.1).

    Automatically routes to read replica with sticky read-after-write protection:
    - If read_replica_enabled=false or read_replica_url empty → uses primary
    - If write occurred <5s ago → uses primary (sticky)
    - Otherwise → uses read replica (~100ms lag, scaled reads)

    Replaces get_async_db for read-only queries.
    Write queries should always use get_async_db.

    Usage in route:
        async def get_users(
            db: Annotated[AsyncSession, Depends(get_read_db_async)]
        ):
            result = await db.execute(...)
            return result.scalars().all()
    """
    async for session in get_read_db(request):
        yield session
