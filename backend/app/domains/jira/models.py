"""Jira entegrasyon domain modelleri."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.crypto import EncryptedString
from app.infra.database import Base

_DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(_tz.utc)


class JiraIntegration(Base):
    """Jira bağlantı ayarları. Tenant başına bir kayıt tutulur."""

    __tablename__ = "jira_integrations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default=_DEFAULT_TENANT_ID, index=True
    )
    jira_url: Mapped[str] = mapped_column(String(500), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Token Fernet ile şifreli saklanır — plain-text asla yazılmaz.
    api_token: Mapped[str] = mapped_column(EncryptedString(1024), nullable=False)
    default_project_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
