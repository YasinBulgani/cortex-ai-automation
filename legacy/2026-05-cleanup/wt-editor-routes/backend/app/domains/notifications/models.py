"""Notification domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NotificationPrefs(Base):
    """Per-user notification preferences."""

    __tablename__ = "notification_prefs"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sd_users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    notify_on_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    slack_webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=True
    )
