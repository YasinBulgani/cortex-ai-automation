"""Webhook → subscription state application — DB-isolated unit tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.domains.billing.models import ProcessedWebhook, Subscription, UsageEvent
from app.domains.billing.stripe_sync import apply_event
from app.infra.database import Base


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Subscription.__table__,
            UsageEvent.__table__,
            ProcessedWebhook.__table__,
        ],
    )
    with Session(engine) as session:
        yield session


def _sub_event(
    event_type: str,
    *,
    tenant_id: str,
    plan_code: str = "starter",
    status: str = "active",
    sub_id: str = "sub_123",
    customer_id: str = "cus_123",
    period_start: int = 1_700_000_000,
    period_end: int = 1_702_000_000,
    cancel_at_period_end: bool = False,
) -> dict:
    return {
        "id": "evt_test",
        "type": event_type,
        "data": {
            "object": {
                "id": sub_id,
                "customer": customer_id,
                "status": status,
                "current_period_start": period_start,
                "current_period_end": period_end,
                "cancel_at_period_end": cancel_at_period_end,
                "metadata": {"tenant_id": tenant_id, "plan_code": plan_code},
            }
        },
    }


def test_subscription_created_upserts_row(db: Session) -> None:
    status = apply_event(
        db, _sub_event("customer.subscription.created", tenant_id="tenant-A")
    )
    db.commit()
    assert status == "sub-created"

    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == "tenant-A")
    ).scalar_one()
    assert sub.plan_code == "starter"
    assert sub.status == "active"
    assert sub.external_subscription_id == "sub_123"
    assert sub.external_customer_id == "cus_123"
    assert sub.current_period_end is not None
    assert sub.cancel_at_period_end is False


def test_subscription_updated_changes_status(db: Session) -> None:
    apply_event(db, _sub_event("customer.subscription.created", tenant_id="tenant-A"))
    apply_event(
        db,
        _sub_event(
            "customer.subscription.updated",
            tenant_id="tenant-A",
            status="past_due",
        ),
    )
    db.commit()
    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == "tenant-A")
    ).scalar_one()
    assert sub.status == "past_due"


def test_subscription_deleted_marks_canceled(db: Session) -> None:
    apply_event(db, _sub_event("customer.subscription.created", tenant_id="tenant-A"))
    apply_event(
        db,
        _sub_event(
            "customer.subscription.deleted",
            tenant_id="tenant-A",
            status="canceled",
        ),
    )
    db.commit()
    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == "tenant-A")
    ).scalar_one()
    assert sub.status == "canceled"


def test_checkout_completed_links_customer(db: Session) -> None:
    event = {
        "id": "evt_co_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test",
                "customer": "cus_999",
                "subscription": "sub_pending",
                "metadata": {"tenant_id": "tenant-B", "plan_code": "pro"},
            }
        },
    }
    status = apply_event(db, event)
    db.commit()
    assert status == "checkout-linked"

    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == "tenant-B")
    ).scalar_one()
    assert sub.external_customer_id == "cus_999"
    assert sub.external_subscription_id == "sub_pending"
    assert sub.plan_code == "pro"


def test_payment_failed_marks_past_due_via_customer(db: Session) -> None:
    apply_event(
        db,
        _sub_event(
            "customer.subscription.created",
            tenant_id="tenant-C",
            customer_id="cus_pf",
        ),
    )
    db.commit()
    status = apply_event(
        db,
        {
            "id": "evt_pf",
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_pf"}},
        },
    )
    db.commit()
    assert status == "marked-past-due"

    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == "tenant-C")
    ).scalar_one()
    assert sub.status == "past_due"


def test_event_without_tenant_metadata_is_skipped(db: Session) -> None:
    event = {
        "id": "evt_x",
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_x", "customer": "cus_x", "status": "active"}},
    }
    status = apply_event(db, event)
    db.commit()
    assert status == "no-tenant"
    assert db.query(Subscription).count() == 0


def test_unhandled_event_type_returns_ignored(db: Session) -> None:
    event = {
        "id": "evt_z",
        "type": "charge.refunded",
        "data": {"object": {}},
    }
    assert apply_event(db, event) == "ignored"


def test_period_timestamps_are_converted_to_datetime(db: Session) -> None:
    apply_event(
        db,
        _sub_event(
            "customer.subscription.created",
            tenant_id="tenant-D",
            period_start=1_700_000_000,
            period_end=1_705_000_000,
        ),
    )
    db.commit()
    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == "tenant-D")
    ).scalar_one()
    # SQLite drops tzinfo, so compare naive seconds-since-epoch.
    expected_start = datetime.fromtimestamp(1_700_000_000, tz=timezone.utc).replace(tzinfo=None)
    expected_end = datetime.fromtimestamp(1_705_000_000, tz=timezone.utc).replace(tzinfo=None)
    assert sub.current_period_start.replace(tzinfo=None) == expected_start
    assert sub.current_period_end.replace(tzinfo=None) == expected_end


def test_unknown_plan_code_falls_back_to_existing(db: Session) -> None:
    apply_event(
        db,
        _sub_event(
            "customer.subscription.created",
            tenant_id="tenant-E",
            plan_code="starter",
        ),
    )
    apply_event(
        db,
        _sub_event(
            "customer.subscription.updated",
            tenant_id="tenant-E",
            plan_code="nonexistent",
        ),
    )
    db.commit()
    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == "tenant-E")
    ).scalar_one()
    # Unknown plan_code should NOT overwrite the existing valid one
    assert sub.plan_code == "starter"
