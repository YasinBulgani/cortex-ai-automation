"""Webhooks domain models — outgoing & incoming webhook management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz
from typing import Any, Optional, Literal

from sqlalchemy import (
    DateTime, Index, Integer, String, Text, UniqueConstraint, Boolean,
    ForeignKey, Enum as SQLEnum, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(_tz.utc)


class WebhookConfig(Base):
    """Webhook configuration — outgoing or incoming webhook registration."""

    __tablename__ = "webhook_configs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Webhook type: "outgoing" (Neurex → external), "incoming" (external → Neurex)
    webhook_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Provider integration (if incoming): "jira", "github", "gitlab", "azure_devops", "slack"
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Outgoing: URL target; Incoming: integration metadata
    target_url: Mapped[str] = mapped_column(String(512), nullable=False)
    secret: Mapped[str] = mapped_column(String(256), nullable=False)  # HMAC key

    # Event subscriptions: ["test_run.completed", "defect.created", ...]
    events: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Rate limiting (per minute, per day)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    rate_limit_per_day: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)

    # Retry strategy
    max_retries: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Status & metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=True)

    # OAuth/auth for incoming webhooks
    auth_method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # "basic", "bearer", "hmac"
    auth_credentials: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_webhook_configs_tenant_id", "tenant_id"),
        Index("ix_webhook_configs_provider", "provider"),
        Index("ix_webhook_configs_is_active", "is_active"),
        UniqueConstraint("tenant_id", "target_url", "webhook_type", name="uq_webhook_tenant_url_type"),
    )


class WebhookDelivery(Base):
    """Webhook delivery attempt — tracks outgoing webhook deliveries."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    webhook_config_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("webhook_configs.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Event trigger
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)  # "test_run.completed"
    entity_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Delivery attempt
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # "pending", "success", "failed", "retrying"
    http_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Request/response
    request_body: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_webhook_deliveries_webhook_config_id", "webhook_config_id"),
        Index("ix_webhook_deliveries_tenant_id", "tenant_id"),
        Index("ix_webhook_deliveries_status", "status"),
        Index("ix_webhook_deliveries_created_at", "created_at"),
    )


class WebhookLog(Base):
    """Audit log — all webhook activity (create, update, test, receive)."""

    __tablename__ = "webhook_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    webhook_config_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Action: "created", "updated", "deleted", "tested", "delivery_sent", "signature_validated", "rate_limited"
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_webhook_logs_tenant_id", "tenant_id"),
        Index("ix_webhook_logs_webhook_config_id", "webhook_config_id"),
        Index("ix_webhook_logs_action", "action"),
        Index("ix_webhook_logs_created_at", "created_at"),
    )
