"""SSO OAuth endpoints (Google, Azure AD).

Flow:
  1. GET /sso/{provider}/login  -> redirect to provider's authorize URL
  2. Provider redirects back to /sso/{provider}/callback?code=...
  3. We exchange code for id_token, verify, find or create the user,
     issue our own session cookies (same as /auth/login).
"""

from __future__ import annotations

import logging
import secrets
from typing import Annotated, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.domains.audit.service import log_audit
from app.domains.auth.router import ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE
from app.domains.auth.service import (
    create_access_token,
    create_refresh_token,
    hash_password,
)
from app.infra.database import get_db
from app.infra.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sso", tags=["sso"])

# In-memory state store (replace with Redis in prod for multi-instance)
_STATE_TTL_SECONDS = 600
_state_store: dict[str, dict] = {}


def _redirect_uri(provider: str) -> str:
    base = (settings.app_public_url or "http://localhost:3000").rstrip("/")
    # Backend handles callback then redirects to FE; FE-side callback alt.
    backend = (settings.cors_origin_list[0] if settings.cors_origin_list else base).rstrip("/")
    # Frontend reverse-proxies /api to backend, so use FE origin
    return f"{backend}/api/v1/sso/{provider}/callback"


def _provider_config(provider: str) -> dict:
    if provider == "google":
        if not settings.sso_google_client_id or not settings.sso_google_client_secret:
            raise HTTPException(503, detail="Google SSO yapilandirilmamis")
        return {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "client_id": settings.sso_google_client_id,
            "client_secret": settings.sso_google_client_secret,
            "scope": "openid email profile",
        }
    if provider == "azure":
        tenant = settings.sso_azure_tenant_id or "common"
        if not settings.sso_azure_client_id or not settings.sso_azure_client_secret:
            raise HTTPException(503, detail="Azure SSO yapilandirilmamis")
        return {
            "auth_url": f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            "token_url": f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
            "client_id": settings.sso_azure_client_id,
            "client_secret": settings.sso_azure_client_secret,
            "scope": "openid email profile",
        }
    raise HTTPException(404, detail=f"Bilinmeyen provider: {provider}")


def _email_domain_allowed(email: str) -> bool:
    raw = (settings.sso_allowed_email_domains or "").strip()
    if not raw:
        return True
    allowed = {d.strip().lower() for d in raw.split(",") if d.strip()}
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in allowed


@router.get("/{provider}/login")
def sso_login(provider: str):
    cfg = _provider_config(provider)
    state = secrets.token_urlsafe(24)
    _state_store[state] = {"provider": provider}
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": _redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{cfg['auth_url']}?{urlencode(params)}")


@router.get("/{provider}/callback")
def sso_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    error: Optional[str] = None,
):
    if error:
        raise HTTPException(400, detail=f"SSO hata: {error}")
    if state not in _state_store:
        raise HTTPException(400, detail="Gecersiz state (CSRF korumasi)")
    _state_store.pop(state, None)

    cfg = _provider_config(provider)

    # Exchange code -> token
    with httpx.Client(timeout=10.0) as client:
        token_res = client.post(
            cfg["token_url"],
            data={
                "code": code,
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "redirect_uri": _redirect_uri(provider),
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            logger.warning("SSO token exchange failed: %s", token_res.text)
            raise HTTPException(400, detail="Token degisimi basarisiz")
        tokens = token_res.json()
        access = tokens.get("access_token")
        if not access:
            raise HTTPException(400, detail="access_token yok")

        # Get userinfo
        info_res = client.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {access}"},
        )
        if info_res.status_code != 200:
            raise HTTPException(400, detail="Kullanici bilgisi alinamadi")
        info = info_res.json()

    email = (info.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(400, detail="SSO yanitinda email yok")
    if not _email_domain_allowed(email):
        raise HTTPException(403, detail="Bu email alani SSO icin izinli degil")

    full_name = info.get("name") or info.get("given_name") or None

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        if not settings.sso_auto_provision:
            raise HTTPException(403, detail="Hesabiniz yok; yoneticinizden davet isteyin")
        # Auto-provision with random password (user can reset)
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(24)),
            full_name=full_name,
            is_active=True,
        )
        db.add(user)
        db.flush()
        log_audit(db, user_id=user.id, action="sso.provision", resource=provider)

    log_audit(db, user_id=user.id, action="sso.login", resource=provider)
    db.commit()

    # Issue our session
    access_jwt = create_access_token(subject_user_id=user.id)
    refresh_jwt = create_refresh_token(
        user_id=user.id, db=db, user_agent=request.headers.get("user-agent", "")
    )

    fe_url = (settings.app_public_url or "http://localhost:3000").rstrip("/")
    response = RedirectResponse(f"{fe_url}/?sso=success")
    response.set_cookie(
        ACCESS_TOKEN_COOKIE, access_jwt, httponly=True, secure=False,
        samesite="lax", max_age=30 * 60,
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE, refresh_jwt, httponly=True, secure=False,
        samesite="lax", max_age=7 * 24 * 3600,
    )
    return response


@router.get("/providers")
def list_providers():
    """Aktif SSO saglayicilarini doner — login sayfasi butonlari icin."""
    out = []
    if settings.sso_google_client_id:
        out.append({"id": "google", "name": "Google"})
    if settings.sso_azure_client_id:
        out.append({"id": "azure", "name": "Microsoft / Azure AD"})
    return {"providers": out}
