"""Subscription service tests with isolated in-memory SQLite session.

We don't depend on the app-wide DB. Models are registered against a fresh
metadata bound to ``sqlite:///:memory:`` so the suite runs in any env.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domains.billing.models import Subscription, UsageEvent
from app.domains.billing.plans import PLAN_CATALOG
from app.domains.billing.service import (
    DEFAULT_PLAN_CODE,
    UsageSnapshot,
    check_limit,
    compute_usage_snapshot,
    get_or_create_subscription,
    record_usage,
    set_plan,
)
from app.infra.database import Base


@pytest.fixture
def db() -> Session:
    # Use shared in-memory DB so multiple connections see the same data.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Subscription.__table__, UsageEvent.__table__])
    with Session(engine) as session:
        yield session


def test_get_or_create_creates_free_subscription(db: Session) -> None:
    sub = get_or_create_subscription(db, "tenant-1")
    assert sub.tenant_id == "tenant-1"
    assert sub.plan_code == DEFAULT_PLAN_CODE
    assert sub.status == "active"


def test_get_or_create_is_idempotent(db: Session) -> None:
    s1 = get_or_create_subscription(db, "tenant-1")
    s2 = get_or_create_subscription(db, "tenant-1")
    assert s1.id == s2.id


def test_set_plan_updates_plan_code(db: Session) -> None:
    sub = set_plan(db, "tenant-1", "starter")
    assert sub.plan_code == "starter"
    assert sub.current_period_start is not None


def test_set_plan_rejects_unknown_code(db: Session) -> None:
    with pytest.raises(ValueError, match="Bilinmeyen plan"):
        set_plan(db, "tenant-1", "ultraplatinum")


def test_record_usage_appends_event(db: Session) -> None:
    record_usage(db, "tenant-1", "ai.token_spend", amount=0.42)
    record_usage(db, "tenant-1", "ai.token_spend", amount=1.0)
    db.commit()

    rows = db.query(UsageEvent).filter_by(tenant_id="tenant-1").all()
    assert len(rows) == 2
    assert sum(float(r.amount) for r in rows) == pytest.approx(1.42)


def test_check_limit_allows_when_under(db: Session) -> None:
    snap = UsageSnapshot(
        plan="free",
        plan_expires_at=None,
        scenario_count=10,
        scenario_limit=50,
        run_count_month=20,
        run_limit_month=100,
        ai_token_spend_usd=0,
        ai_token_limit_usd=2.0,
        team_size=1,
        team_limit=2,
        storage_mb=0,
        storage_limit_mb=1024,
        project_count=2,
        project_limit=5,
    )
    assert check_limit(snap, "project_count").allowed is True
    assert check_limit(snap, "team_size").allowed is True


def test_check_limit_blocks_when_at_or_above(db: Session) -> None:
    snap = UsageSnapshot(
        plan="free",
        plan_expires_at=None,
        scenario_count=50,
        scenario_limit=50,
        run_count_month=0,
        run_limit_month=100,
        ai_token_spend_usd=0,
        ai_token_limit_usd=2.0,
        team_size=2,
        team_limit=2,
        storage_mb=0,
        storage_limit_mb=1024,
        project_count=5,
        project_limit=5,
    )
    result = check_limit(snap, "project_count")
    assert result.allowed is False
    assert result.reason is not None
    assert "project_count" in result.reason

    team_result = check_limit(snap, "team_size")
    assert team_result.allowed is False


def test_check_limit_unlimited_always_allows(db: Session) -> None:
    snap = UsageSnapshot(
        plan="enterprise",
        plan_expires_at=None,
        scenario_count=10_000_000,
        scenario_limit=-1,
        run_count_month=10_000_000,
        run_limit_month=-1,
        ai_token_spend_usd=1_000_000.0,
        ai_token_limit_usd=-1,
        team_size=10_000,
        team_limit=-1,
        storage_mb=10_000_000,
        storage_limit_mb=-1,
        project_count=10_000,
        project_limit=-1,
    )
    for metric in (
        "project_count",
        "scenario_count",
        "run_count_month",
        "team_size",
        "storage_mb",
        "ai_token_spend_usd",
    ):
        assert check_limit(snap, metric).allowed is True


def test_check_limit_rejects_unknown_metric(db: Session) -> None:
    snap = UsageSnapshot(
        plan="free",
        plan_expires_at=None,
        scenario_count=0,
        scenario_limit=50,
        run_count_month=0,
        run_limit_month=100,
        ai_token_spend_usd=0,
        ai_token_limit_usd=2.0,
        team_size=0,
        team_limit=2,
        storage_mb=0,
        storage_limit_mb=1024,
        project_count=0,
        project_limit=5,
    )
    with pytest.raises(ValueError, match="Bilinmeyen metric"):
        check_limit(snap, "bogus")


def test_compute_usage_snapshot_uses_default_plan(db: Session) -> None:
    """If no subscription exists, snapshot reflects the free plan."""
    snap = compute_usage_snapshot(db, "tenant-1")
    free = PLAN_CATALOG["free"]
    assert snap.plan == "free"
    assert snap.project_limit == free.limits.project_count
    assert snap.team_limit == free.limits.team_size
    assert snap.run_limit_month == free.limits.run_count_month


def test_compute_usage_aggregates_ai_token_spend(db: Session) -> None:
    record_usage(db, "tenant-1", "ai.token_spend", amount=0.5)
    record_usage(db, "tenant-1", "ai.token_spend", amount=1.25)
    record_usage(db, "tenant-1", "ai.token_spend", amount=0.25)
    # Different tenant — should not bleed.
    record_usage(db, "tenant-2", "ai.token_spend", amount=99.0)
    db.commit()

    snap = compute_usage_snapshot(db, "tenant-1")
    assert snap.ai_token_spend_usd == pytest.approx(2.0)


def test_to_dict_includes_frontend_keys(db: Session) -> None:
    snap = compute_usage_snapshot(db, "tenant-1")
    payload = snap.to_dict()
    for key in (
        "plan",
        "scenario_count",
        "scenario_limit",
        "run_count_month",
        "run_limit_month",
        "team_size",
        "team_limit",
        "storage_mb",
        "storage_limit_mb",
        "ai_token_spend_usd",
        "ai_token_limit_usd",
        "project_count",
        "project_limit",
    ):
        assert key in payload, f"missing key in snapshot dict: {key}"
