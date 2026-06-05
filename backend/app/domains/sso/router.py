"""SSO OAuth endpoints (Google, Azure AD).

Flow:
  1. GET /sso/{provider}/login  -> redirect to provider's authorize URL
  2. Provider redirects back to /sso/{provider}/callback?code=...
  3. We exchange code for id_token, verify, find or create the user,
     issue our own session cookies (same as /auth/login).

# TODO: SAML 2.0 desteği için python3-saml veya pysaml2 entegrasyonu gerekli.
# Şu anki implementasyon OAuth 2.0 (Google, Azure AD) destekliyor.
# SSO config management/settings API'sine kaydediliyor (usePatchManagementSetting).
"""

from __future__ import annotations

import logging
import secrets
from threading import RLock
from typing import Annotated, Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
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

_STATE_TTL_SECONDS = 600


class _StateStore:
    """Thread-safe SSO state store.

    Redis varsa state'ler orada saklanır (TTL=600s) — multi-instance
    ortamlarında CSRF koruması için gereklidir. Redis yoksa in-memory
    fallback kullanılır (tek instance için yeterli).
    """

    _KEY_PREFIX = "sso_state:"

    def __init__(self) -> None:
        self._lock = RLock()
        self._store: Dict[str, Any] = {}
        self._redis = self._try_redis()

    @staticmethod
    def _try_redis():
        try:
            import redis as _redis_lib
            client = _redis_lib.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            client.ping()
            logger.info("SSO: Redis state store bağlandı")
            return client
        except Exception as exc:
            logger.warning("SSO: Redis yok, in-memory state store kullanılıyor (%s)", exc)
            return None

    def set(self, state_key: str, value: Any, ttl: int = _STATE_TTL_SECONDS) -> None:
        import json as _json
        if self._redis:
            try:
                self._redis.setex(
                    f"{self._KEY_PREFIX}{state_key}",
                    ttl,
                    _json.dumps(value),
                )
                return
            except Exception as exc:
                logger.warning("SSO: Redis set hatası, in-memory fallback (%s)", exc)
        with self._lock:
            self._store[state_key] = value

    def get(self, state_key: str) -> Optional[Any]:
        import json as _json
        if self._redis:
            try:
                raw = self._redis.get(f"{self._KEY_PREFIX}{state_key}")
                if raw is not None:
                    return _json.loads(raw)
                return None
            except Exception as exc:
                logger.warning("SSO: Redis get hatası, in-memory fallback (%s)", exc)
        with self._lock:
            return self._store.get(state_key)

    def __setitem__(self, key: str, value: dict) -> None:
        self.set(key, value)

    def pop(self, state_key: str, *args) -> Optional[Any]:
        value = self.get(state_key)
        if value is None and args:
            return args[0]
        self.delete(state_key)
        return value

    def delete(self, state_key: str) -> None:
        if self._redis:
            try:
                self._redis.delete(f"{self._KEY_PREFIX}{state_key}")
                return
            except Exception as exc:
                logger.warning("SSO: Redis delete hatası, in-memory fallback (%s)", exc)
        with self._lock:
            self._store.pop(state_key, None)


_state_store = _StateStore()


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
    _state_store.set(state, {"provider": provider})
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
    if _state_store.get(state) is None:
        raise HTTPException(400, detail="Gecersiz state (CSRF korumasi)")
    _state_store.delete(state)

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

    user = db.execute(select(User).where(User.email == email)).scalars().first()
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
