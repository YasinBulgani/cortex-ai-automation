"""SQLAlchemy models for API key management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(_tz.utc)


class ApiKey(Base):
    """User API key with rotation support."""

    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "is_active"),
        Index("ix_api_keys_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Hashed key (never store plaintext)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Key metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rotation tracking
    rotated_from_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    rotation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Audit trail
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Usually "manual" or user_id
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<ApiKey(user_id={self.user_id}, name={self.name}, active={self.is_active})>"
