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
    for role in user.roles:
        for rp in role.permissions:
            perms.add(rp.permission)
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
