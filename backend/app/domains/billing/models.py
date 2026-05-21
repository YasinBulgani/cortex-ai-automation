"""Subscription persistence — one row per tenant.

Schema mirrors the eventual Stripe contract (plan_code, status, period
boundaries, external_subscription_id) so the storage layer doesn't change
when payments are wired in.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc)


class Subscription(Base):
    """One subscription per tenant. Source of truth for plan limits."""

    __tablename__ = "billing_subscriptions"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_billing_subscriptions_tenant"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        doc="active | trialing | past_due | canceled | paused",
    )
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    external_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, doc="Stripe subscription id (when wired)"
    )
    external_customer_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class UsageEvent(Base):
    """Append-only ledger of billable events. Aggregated for current-period stats.

    Common ``kind`` values: ``run.executed``, ``ai.token_spend``,
    ``storage.delta_mb``. ``amount`` is the metric increment (int for counts,
    Numeric for currency-like floats).
    """

    __tablename__ = "billing_usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    meta: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)


class ProcessedWebhook(Base):
    """Stripe event idempotency table — one row per event id we have handled."""

    __tablename__ = "billing_processed_webhooks"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
