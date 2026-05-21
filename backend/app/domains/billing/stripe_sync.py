"""Apply Stripe webhook events to billing_subscriptions.

Stripe sends a lot of event types; we only act on the ones that change
subscription state. Unhandled events return cleanly so Stripe stops
retrying. Idempotency is enforced upstream via ProcessedWebhook insert.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.billing.models import Subscription
from app.domains.billing.plans import PLAN_CATALOG

logger = logging.getLogger(__name__)


# Stripe sub status → our status. Anything not mapped is forwarded raw.
_STATUS_MAP = {
    "trialing": "trialing",
    "active": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "canceled",
    "paused": "paused",
    "incomplete": "trialing",
    "incomplete_expired": "canceled",
}


def _ts(epoch: Any) -> datetime | None:
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _plan_code_from_subscription(sub: dict) -> str | None:
    """Extract plan_code from metadata, falling back to price-id mapping."""
    meta = (sub.get("metadata") or {})
    code = meta.get("plan_code")
    if code in PLAN_CATALOG:
        return code
    return None


def _upsert_subscription(
    db: Session,
    tenant_id: str,
    *,
    plan_code: str | None,
    status: str | None,
    external_subscription_id: str | None,
    external_customer_id: str | None,
    current_period_start: datetime | None,
    current_period_end: datetime | None,
    cancel_at_period_end: bool | None,
) -> Subscription:
    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if sub is None:
        sub = Subscription(tenant_id=tenant_id, plan_code=plan_code or "free")
        db.add(sub)

    if plan_code:
        sub.plan_code = plan_code
    if status:
        sub.status = _STATUS_MAP.get(status, status)
    if external_subscription_id:
        sub.external_subscription_id = external_subscription_id
    if external_customer_id:
        sub.external_customer_id = external_customer_id
    if current_period_start:
        sub.current_period_start = current_period_start
    if current_period_end:
        sub.current_period_end = current_period_end
    if cancel_at_period_end is not None:
        sub.cancel_at_period_end = cancel_at_period_end

    db.flush()
    return sub


def apply_event(db: Session, event: dict) -> str:
    """Route a Stripe event payload to the right handler.

    Returns a short human-readable status string for logging.
    Callers are responsible for commit/rollback.
    """
    event_type = event.get("type", "")
    data = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        return _handle_checkout_completed(db, data)
    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        return _handle_subscription_change(db, data, event_type)
    if event_type == "invoice.payment_failed":
        return _handle_payment_failed(db, data)

    logger.debug("stripe: unhandled event type %s", event_type)
    return "ignored"


def _handle_checkout_completed(db: Session, session: dict) -> str:
    """The subscription is created in a follow-up event; here we just record
    the customer link so we can build a portal URL even before the first
    subscription.updated comes in."""
    tenant_id = (session.get("metadata") or {}).get("tenant_id")
    if not tenant_id:
        logger.warning("stripe: checkout.completed without tenant_id metadata")
        return "no-tenant"
    plan_code = (session.get("metadata") or {}).get("plan_code")
    _upsert_subscription(
        db,
        tenant_id,
        plan_code=plan_code if plan_code in PLAN_CATALOG else None,
        status="trialing",
        external_subscription_id=session.get("subscription"),
        external_customer_id=session.get("customer"),
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=None,
    )
    return "checkout-linked"


def _handle_subscription_change(db: Session, sub: dict, event_type: str) -> str:
    tenant_id = (sub.get("metadata") or {}).get("tenant_id")
    if not tenant_id:
        logger.warning(
            "stripe: %s without tenant_id metadata (sub=%s)", event_type, sub.get("id")
        )
        return "no-tenant"
    status = "canceled" if event_type.endswith(".deleted") else sub.get("status")
    plan_code = _plan_code_from_subscription(sub)
    period_start = _ts(sub.get("current_period_start"))
    period_end = _ts(sub.get("current_period_end"))
    _upsert_subscription(
        db,
        tenant_id,
        plan_code=plan_code,
        status=status,
        external_subscription_id=sub.get("id"),
        external_customer_id=sub.get("customer"),
        current_period_start=period_start,
        current_period_end=period_end,
        cancel_at_period_end=bool(sub.get("cancel_at_period_end")),
    )

    # Best-effort email notifications — never block the webhook on email.
    try:
        from app.domains.billing import notifier
        if event_type == "customer.subscription.deleted":
            notifier.notify_subscription_canceled(
                db, tenant_id, period_end.isoformat() if period_end else None
            )
        elif event_type == "customer.subscription.created" and plan_code:
            notifier.notify_plan_changed(
                db,
                tenant_id,
                plan_code,
                period_start.isoformat() if period_start else None,
            )
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("notifier error after %s: %s", event_type, exc)

    return f"sub-{event_type.rsplit('.', 1)[-1]}"


def _handle_payment_failed(db: Session, invoice: dict) -> str:
    customer_id = invoice.get("customer")
    if not customer_id:
        return "no-customer"
    sub = db.execute(
        select(Subscription).where(Subscription.external_customer_id == customer_id)
    ).scalar_one_or_none()
    if sub is None:
        return "no-sub"
    sub.status = "past_due"
    db.flush()

    try:
        from app.domains.billing import notifier
        notifier.notify_payment_failed(db, sub.tenant_id)
    except Exception as exc:  # pragma: no cover
        logger.warning("notifier error after payment_failed: %s", exc)

    return "marked-past-due"
