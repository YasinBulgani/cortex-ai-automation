"""
Auth routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/auth_routes.py — Blueprint, session-based auth, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/auth.py — APIRouter, port 8000 (consolidated)

NOT: Flask session tabanlı kimlik doğrulama burada in-memory store'a
     port edilmiştir. Üretim kullanımı için ana backend'in JWT/OAuth
     akışına entegre edilmesi planlanmaktadır (Wave-25 ADR).

Endpointler:
  POST /api/auth/register          — Yeni kullanıcı kaydı
  POST /api/auth/login             — Giriş (token döndürür)
  GET  /api/auth/verify/{token}    — E-posta doğrulama
  POST /api/auth/logout            — Çıkış (token iptal)
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["engine", "auth"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    token: Optional[str] = None


class LogoutResponse(BaseModel):
    success: bool


# ─── In-memory user store (placeholder) ──────────────────────────────────────

class _UserStore:
    """
    Geçici in-memory kullanıcı deposu.
    Flask engine'deki core.db (PostgreSQL) entegre edilince kaldırılacak.
    Token geçerliliği 24 saat olarak ayarlanmıştır.
    """

    def __init__(self) -> None:
        self._users: dict[str, dict] = {}          # email → user record
        self._verify_tokens: dict[str, str] = {}   # token → email
        self._session_tokens: dict[str, dict] = {} # session_token → {email, expires_at}

    def _hash_password(self, password: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), b"engine_salt", 260_000).hex()

    def create_user(self, email: str, password: str) -> dict:
        if email in self._users:
            return {"success": False, "error": "Bu e-posta zaten kayıtlı."}
        hashed = self._hash_password(password)
        token = secrets.token_hex(16)
        self._users[email] = {
            "id": len(self._users) + 1,
            "email": email,
            "password_hash": hashed,
            "is_verified": False,
            "created_at": datetime.now().isoformat(),
        }
        self._verify_tokens[token] = email
        return {"success": True, "verify_token": token}

    def verify_user(self, token: str) -> bool:
        email = self._verify_tokens.pop(token, None)
        if not email or email not in self._users:
            return False
        self._users[email]["is_verified"] = True
        return True

    def authenticate(self, email: str, password: str) -> dict:
        user = self._users.get(email)
        if not user:
            return {"success": False, "error": "Geçersiz e-posta veya şifre."}
        if user["password_hash"] != self._hash_password(password):
            return {"success": False, "error": "Geçersiz e-posta veya şifre."}
        if not user["is_verified"]:
            return {"success": False, "error": "Lütfen e-posta adresinizi doğrulayın.", "unverified": True}
        session_token = secrets.token_hex(32)
        self._session_tokens[session_token] = {
            "email": email,
            "expires_at": datetime.now() + timedelta(hours=24),
        }
        return {"success": True, "token": session_token}

    def revoke_token(self, token: str) -> None:
        self._session_tokens.pop(token, None)


_store = _UserStore()


def _dev_auth_shortcuts_enabled() -> bool:
    app_env = os.environ.get("APP_ENV", "development").lower()
    if app_env not in {"development", "dev", "local"}:
        return False
    return os.environ.get("ENGINE_DEV_AUTH_SHORTCUTS", "").lower() in {"1", "true", "yes"}


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> AuthResponse:
    """
    Yeni kullanıcı kaydı oluşturur.
    Development modunda ENGINE_DEV_AUTH_SHORTCUTS=1 ise e-posta doğrulaması atlanır.
    """
    result = _store.create_user(body.email, body.password)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Kayıt başarısız."),
        )

    if _dev_auth_shortcuts_enabled():
        _store.verify_user(result["verify_token"])
        logger.debug("Dev shortcut: %s otomatik doğrulandı", body.email)

    return AuthResponse(success=True, message="Kayıt başarılı! Giriş yapabilirsiniz.")


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    """Kullanıcıyı doğrular ve session token döndürür."""
    result = _store.authenticate(body.email, body.password)
    if not result["success"]:
        code = (
            status.HTTP_403_FORBIDDEN
            if result.get("unverified")
            else status.HTTP_401_UNAUTHORIZED
        )
        raise HTTPException(status_code=code, detail=result.get("error", "Giriş başarısız."))

    return AuthResponse(success=True, token=result["token"])


@router.get("/verify/{token}")
def verify_email(token: str) -> dict:
    """
    E-posta doğrulama token'ını işler.
    HTML yanıt yerine JSON döndürür (API-first pattern).
    """
    success = _store.verify_user(token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz veya süresi dolmuş doğrulama token'ı.",
        )
    return {"success": True, "message": "Hesabınız doğrulandı! Giriş yapabilirsiniz."}


@router.post("/logout", response_model=LogoutResponse)
def logout(body: dict = {}) -> LogoutResponse:
    """
    Session token'ı iptal eder.
    Token, Authorization header yerine request body'de beklenir (legacy compat).
    """
    token = body.get("token", "") if isinstance(body, dict) else ""
    if token:
        _store.revoke_token(token)
    return LogoutResponse(success=True)
