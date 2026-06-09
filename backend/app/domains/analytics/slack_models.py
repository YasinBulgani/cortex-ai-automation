"""Slack integration models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz, date
from typing import Any, Optional

from sqlalchemy import Date, DateTime, Index, Integer, String, Text, UniqueConstraint, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(_tz.utc)


class SlackSubscription(Base):
    """Slack workspace subscription — per channel event subscriptions."""

    __tablename__ = "slack_subscriptions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Slack workspace identification
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Subscriptions
    event_types: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Webhook
    webhook_url: Mapped[str] = mapped_column(Text(), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Audit
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    notification_queues: Mapped[list[SlackNotificationQueue]] = relationship(
        "SlackNotificationQueue", back_populates="subscription", cascade="all, delete-orphan"
    )
    daily_digests: Mapped[list[SlackDailyDigest]] = relationship(
        "SlackDailyDigest", back_populates="subscription", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_slack_subscriptions_tenant', 'tenant_id'),
        Index('idx_slack_subscriptions_workspace', 'workspace_id'),
        Index('idx_slack_subscriptions_channel', 'channel_id'),
        Index('idx_slack_subscriptions_active', 'is_active'),
        UniqueConstraint('tenant_id', 'workspace_id', 'channel_id', name='uq_slack_sub_tenant_ws_ch'),
    )


class SlackNotificationQueue(Base):
    """Slack notification queue — outbox pattern for retries."""

    __tablename__ = "slack_notification_queue"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Foreign keys
    subscription_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("slack_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("analytics_events.id", ondelete="CASCADE"), nullable=False
    )

    # Message
    webhook_url: Mapped[str] = mapped_column(Text(), nullable=False)
    message_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)  # pending, sent, failed, dlq
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Error tracking
    last_error: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    subscription: Mapped[SlackSubscription] = relationship("SlackSubscription", back_populates="notification_queues")

    __table_args__ = (
        Index('idx_slack_queue_tenant', 'tenant_id'),
        Index('idx_slack_queue_status', 'status'),
        Index('idx_slack_queue_subscription', 'subscription_id'),
        Index('idx_slack_queue_status_tenant', 'status', 'tenant_id'),
        Index('idx_slack_queue_last_attempt', 'last_attempt_at'),
    )


class SlackDeliveryLog(Base):
    """Slack delivery audit log."""

    __tablename__ = "slack_delivery_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Reference to queue item
    notification_queue_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("slack_notification_queue.id", ondelete="SET NULL"), nullable=True
    )

    # Channel info
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Slack response
    message_ts: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    message_text: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    # Delivery result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    response_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=True)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index('idx_slack_delivery_tenant', 'tenant_id'),
        Index('idx_slack_delivery_channel', 'channel_id'),
        Index('idx_slack_delivery_success', 'success'),
        Index('idx_slack_delivery_timestamp', 'timestamp'),
        Index('idx_slack_delivery_queue_id', 'notification_queue_id'),
    )


class SlackDailyDigest(Base):
    """Slack daily digest — 24h summary at 00:00 UTC."""

    __tablename__ = "slack_daily_digests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Reference to subscription
    subscription_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("slack_subscriptions.id", ondelete="CASCADE"), nullable=False
    )

    # Digest content
    digest_date: Mapped[date] = mapped_column(Date(), nullable=False)
    digest_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Slack response
    message_ts: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    subscription: Mapped[SlackSubscription] = relationship("SlackSubscription", back_populates="daily_digests")

    __table_args__ = (
        Index('idx_slack_digest_tenant', 'tenant_id'),
        Index('idx_slack_digest_subscription', 'subscription_id'),
        Index('idx_slack_digest_date', 'digest_date'),
        Index('idx_slack_digest_sent', 'sent_at'),
        UniqueConstraint('tenant_id', 'subscription_id', 'digest_date', name='uq_slack_digest_tenant_sub_date'),
    )
