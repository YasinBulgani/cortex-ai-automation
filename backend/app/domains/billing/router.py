"""Billing API — usage stats, plan catalog, plan change requests.

Mounted at ``/api/v1/admin/billing``. Read endpoints require auth; plan
changes require admin permission.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user, require_permission
from app.domains.billing.models import ProcessedWebhook
from app.domains.billing.plans import PLAN_CATALOG, list_plans
from app.domains.billing.service import (
    compute_usage_snapshot,
    get_or_create_subscription,
    set_plan,
)
from app.domains.billing import stripe_client, stripe_sync
from app.infra.database import get_db
from app.infra.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/billing", tags=["billing"])


class PlanChangeRequest(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=32)


@router.get("/usage")
def get_usage(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Return the current usage snapshot for the caller's tenant."""
    snapshot = compute_usage_snapshot(db, user.tenant_id)
    return snapshot.to_dict()


@router.get("/plans")
def get_plans():
    """Public plan catalog — same shape used by the upgrade picker."""
    return {"plans": list_plans()}


@router.get("/subscription")
def get_subscription_info(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    sub = get_or_create_subscription(db, user.tenant_id)
    return {
        "tenant_id": sub.tenant_id,
        "plan_code": sub.plan_code,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat()
        if sub.current_period_start
        else None,
        "current_period_end": sub.current_period_end.isoformat()
        if sub.current_period_end
        else None,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "external_subscription_id": sub.external_subscription_id,
    }


@router.post("/plan")
def change_plan(
    payload: PlanChangeRequest,
    user: Annotated[User, Depends(require_permission("admin.*"))],
    db: Annotated[Session, Depends(get_db)],
):
    """Change tenant plan.

    Enterprise requires sales contact (not self-serve).
    Until Stripe is wired, free/starter/pro changes are recorded directly.
    """
    if payload.plan_code not in PLAN_CATALOG:
        raise HTTPException(status_code=400, detail="Geçersiz plan kodu")

    if payload.plan_code == "enterprise":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Kurumsal plan için satış ekibiyle iletişime geçin",
                "contact_email": "sales@neurexqa.com",
            },
        )

    try:
        sub = set_plan(db, user.tenant_id, payload.plan_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    logger.info(
        "tenant %s plan changed to %s by user %s",
        user.tenant_id,
        payload.plan_code,
        user.id,
    )
    return {
        "ok": True,
        "plan_code": sub.plan_code,
        "status": sub.status,
    }


# ── Stripe integration ──────────────────────────────────────────────────────


_PRICE_MAP = {
    "starter": "stripe_price_starter",
    "pro": "stripe_price_pro",
}


class CheckoutRequest(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=32)


@router.post("/checkout")
def create_checkout(
    payload: CheckoutRequest,
    user: Annotated[User, Depends(require_permission("admin.*"))],
    db: Annotated[Session, Depends(get_db)],
):
    """Open a Stripe Checkout Session for the requested plan."""
    if payload.plan_code not in _PRICE_MAP:
        raise HTTPException(
            status_code=400,
            detail="Self-serve checkout yalnizca starter ve pro icin acik",
        )
    price_id = getattr(settings, _PRICE_MAP[payload.plan_code], "")
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "billing.stripe_not_configured",
                "message": "Stripe price ID yapilandirilmamis. Yoneticiye haber verin.",
            },
        )
    sub = get_or_create_subscription(db, user.tenant_id)
    try:
        session = stripe_client.create_checkout_session(
            price_id=price_id,
            customer_email=user.email if not sub.external_customer_id else None,
            customer_id=sub.external_customer_id,
            tenant_id=user.tenant_id,
            plan_code=payload.plan_code,
            success_url=settings.stripe_success_url,
            cancel_url=settings.stripe_cancel_url,
        )
    except stripe_client.StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except stripe_client.StripeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    return {"checkout_url": session.get("url"), "session_id": session.get("id")}


@router.post("/portal")
def create_portal(
    user: Annotated[User, Depends(require_permission("admin.*"))],
    db: Annotated[Session, Depends(get_db)],
):
    """Return a Stripe Customer Portal URL the user can manage billing in."""
    sub = get_or_create_subscription(db, user.tenant_id)
    if not sub.external_customer_id:
        raise HTTPException(
            status_code=409,
            detail="Henuz Stripe musterisi olusturulmamis. Once bir plan secin.",
        )
    try:
        session = stripe_client.create_billing_portal_session(
            customer_id=sub.external_customer_id,
            return_url=settings.stripe_portal_return_url,
        )
    except stripe_client.StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except stripe_client.StripeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    return {"portal_url": session.get("url")}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    stripe_signature: Annotated[str | None, Header()] = None,
):
    """Receive Stripe events. Verifies signature, idempotently applies state."""
    payload = await request.body()
    try:
        event = stripe_client.verify_webhook_signature(
            payload,
            stripe_signature or "",
        )
    except stripe_client.StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    event_id = event.get("id")
    event_type = event.get("type", "")
    if not event_id:
        raise HTTPException(status_code=400, detail="event.id eksik")

    db.add(ProcessedWebhook(event_id=event_id, event_type=event_type))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info("stripe: replayed event %s (%s) — skipped", event_id, event_type)
        return {"ok": True, "status": "duplicate"}

    try:
        status = stripe_sync.apply_event(db, event)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("stripe: failed to apply event %s (%s)", event_id, event_type)
        raise HTTPException(status_code=500, detail="webhook apply failed")

    return {"ok": True, "status": status, "event_type": event_type}
