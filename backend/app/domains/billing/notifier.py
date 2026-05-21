"""Tenant-aware billing email triggers.

Best-effort: any failure is logged and swallowed so a flaky SMTP server
or a missing User table (in isolated SQLite tests) never blocks a webhook
from being marked processed.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.billing.plans import get_plan

logger = logging.getLogger(__name__)


def _admin_emails(db: Session, tenant_id: str) -> list[str]:
    """Return distinct admin emails for a tenant, or [] on any failure."""
    try:
        from app.infra.models import User
    except Exception:
        return []
    try:
        users = db.execute(
            select(User.email).where(User.tenant_id == tenant_id).limit(20)
        ).all()
    except Exception:
        return []
    return list({u[0] for u in users if u and u[0]})


def _billing_url() -> str:
    return os.environ.get("BILLING_URL", "http://localhost:3000/admin/billing")


def _send_safe(template: str, *, to: str, ctx: dict) -> None:
    try:
        from app.domains.email import send_template
        outcome = send_template(template, to=to, ctx=ctx)
        if not outcome.delivered:
            logger.info(
                "email[%s] not delivered to=%s reason=%s",
                template,
                to,
                outcome.error,
            )
    except Exception as exc:
        logger.warning("email send raised for %s to=%s: %s", template, to, exc)


def notify_plan_changed(
    db: Session, tenant_id: str, plan_code: str, period_start: Optional[str]
) -> None:
    emails = _admin_emails(db, tenant_id)
    if not emails:
        return
    plan = get_plan(plan_code)
    for addr in emails:
        _send_safe(
            "plan_changed",
            to=addr,
            ctx={
                "plan_label": plan.label,
                "monthly_price": f"{plan.monthly_price_usd:.2f}",
                "period_start": period_start or "—",
                "billing_url": _billing_url(),
            },
        )


def notify_payment_failed(db: Session, tenant_id: str, *, grace_days: int = 7) -> None:
    for addr in _admin_emails(db, tenant_id):
        _send_safe(
            "payment_failed",
            to=addr,
            ctx={"grace_days": grace_days, "billing_url": _billing_url()},
        )


def notify_subscription_canceled(
    db: Session, tenant_id: str, period_end: Optional[str]
) -> None:
    for addr in _admin_emails(db, tenant_id):
        _send_safe(
            "subscription_canceled",
            to=addr,
            ctx={"period_end": period_end or "—", "billing_url": _billing_url()},
        )


def notify_welcome(*, to: str, full_name: str) -> None:
    """Standalone — used by signup flow, not tied to a DB session."""
    _send_safe(
        "welcome",
        to=to,
        ctx={
            "full_name": full_name or "kullanıcı",
            "dashboard_url": os.environ.get(
                "DASHBOARD_URL", "http://localhost:3000/dashboard"
            ),
        },
    )
