"""Pydantic schemas for organizations, teams, invitations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator
from app.domains.auth.schemas import _validate_strong_password


# ── Organizations ────────────────────────────────────────────────
class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str
    plan_code: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)


# ── Teams ────────────────────────────────────────────────────────
class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None


class TeamOut(BaseModel):
    id: str
    organization_id: str
    name: str
    slug: str
    description: Optional[str] = None
    created_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True


class TeamMemberAdd(BaseModel):
    user_id: str
    role: str = Field(default="member", pattern=r"^(owner|admin|member|viewer)$")


class TeamMemberOut(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: str
    joined_at: datetime


# ── Invitations ──────────────────────────────────────────────────
class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern=r"^(admin|operator|member|viewer)$")
    team_id: Optional[str] = None


class InvitationOut(BaseModel):
    id: str
    organization_id: str
    team_id: Optional[str] = None
    email: str
    role: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime

    @computed_field
    @property
    def status(self) -> str:
        if self.revoked_at is not None:
            return "revoked"
        if self.accepted_at is not None:
            return "accepted"
        from datetime import datetime, timezone
        if datetime.now(timezone.utc) > self.expires_at:
            return "expired"
        return "pending"

    class Config:
        from_attributes = True


class InvitationAccept(BaseModel):
    token: str
    full_name: Optional[str] = None
    password: str = Field(default="", max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            return v  # empty = existing user flow (validated at route level)
        return _validate_strong_password(v)


# ── Project members ──────────────────────────────────────────────
class ProjectMemberAdd(BaseModel):
    user_id: str
    role: str = Field(default="viewer", pattern=r"^(admin|operator|member|viewer)$")


class ProjectMemberOut(BaseModel):
    project_id: str
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: str
    added_at: datetime
