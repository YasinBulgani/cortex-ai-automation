from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_strong_password(password: str) -> str:
    """
    Parola gucunu dogrula — bankacilik guvenligi standartlari.
    Kurallar:
      - En az 12 karakter
      - En az 1 buyuk harf
      - En az 1 kucuk harf
      - En az 1 rakam
      - En az 1 ozel karakter (!@#$%^&*...)
    """
    errors: list[str] = []
    if len(password) < 12:
        errors.append("en az 12 karakter")
    if not re.search(r"[A-Z]", password):
        errors.append("en az 1 buyuk harf")
    if not re.search(r"[a-z]", password):
        errors.append("en az 1 kucuk harf")
    if not re.search(r"\d", password):
        errors.append("en az 1 rakam")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        errors.append("en az 1 ozel karakter")
    if errors:
        raise ValueError(f"Parola yeterince guclu degil: {', '.join(errors)} gerekli")
    return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class UserMeResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    roles: list[str]
    permissions: list[str] = []
    tenant_id: Optional[str] = None

    model_config = {"from_attributes": False}


_PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    department: Optional[str] = Field(default=None, max_length=100)

    @field_validator("full_name")
    @classmethod
    def _clean_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Ad boş olamaz")
        return v

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if v and not _PHONE_RE.match(v):
            raise ValueError("Geçersiz telefon numarası formatı")
        return v

    @field_validator("department")
    @classmethod
    def _clean_department(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip() or None

class ProfileOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    roles: list[str] = []
    created_at: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=12)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_strong_password(v)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_strong_password(v)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    full_name: str = ""

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_strong_password(v)

class UserListOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True
    roles: list[str] = []
    created_at: Optional[str] = None

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    full_name: str = ""
    role: str = "viewer"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_strong_password(v)

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


# ── MFA / TOTP schemas ────────────────────────────────────────────────────────


class MfaSetupResponse(BaseModel):
    """Returned when the user initiates MFA setup."""
    secret: str                  # Base32 secret — shown ONCE, user saves it
    provisioning_uri: str        # otpauth:// URI for QR code rendering
    backup_codes: list[str]      # 8 single-use backup codes — shown ONCE


class MfaVerifyRequest(BaseModel):
    """User submits their first TOTP code to confirm setup."""
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class MfaLoginRequest(BaseModel):
    """Used when MFA is required during login (step 2)."""
    session_token: str           # opaque token from first login step
    code: str = Field(min_length=6, max_length=8)  # TOTP or backup code


class MfaStatusResponse(BaseModel):
    mfa_enabled: bool
    backup_codes_remaining: Optional[int] = None


class MfaDisableRequest(BaseModel):
    """Confirm current password + TOTP before disabling MFA."""
    password: str = Field(min_length=1)
    code: str = Field(min_length=6, max_length=8)


class LoginResponse(BaseModel):
    """Extended login response that may indicate MFA is required."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    mfa_required: bool = False
    mfa_session_token: Optional[str] = None  # short-lived token for MFA step
