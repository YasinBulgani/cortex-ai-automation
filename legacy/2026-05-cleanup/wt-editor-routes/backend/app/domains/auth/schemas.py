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
    roles: list[str]
    permissions: list[str] = []

    model_config = {"from_attributes": False}


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None

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
