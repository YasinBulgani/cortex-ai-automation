"""Plan-gating guard — verifies enforce_capacity behavior in isolation."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domains.billing.gating import enforce_capacity
from app.domains.billing.models import ProcessedWebhook, Subscription, UsageEvent
from app.domains.billing.service import set_plan
from app.infra.database import Base


@pytest.fixture
def db(monkeypatch) -> Session:
    # Patch User model resolution to avoid loading the full app schema.
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


def test_enforce_capacity_allows_when_within_free_limit(db: Session) -> None:
    # Fresh tenant on free plan with no projects → allowed
    enforce_capacity(db, "tenant-fresh", "project_count")  # should not raise


def test_enforce_capacity_blocks_when_at_limit(db: Session, monkeypatch) -> None:
    """Force the snapshot to report at-limit and confirm 402 is raised."""
    from app.domains.billing import gating, service

    class _FakeSnapshot:
        def __init__(self):
            self.project_count = 5
            self.project_limit = 5
            self.scenario_count = 0
            self.scenario_limit = 50
            self.run_count_month = 0
            self.run_limit_month = 100
            self.team_size = 0
            self.team_limit = 2
            self.storage_mb = 0
            self.storage_limit_mb = 1024
            self.ai_token_spend_usd = 0.0
            self.ai_token_limit_usd = 2.0
            self.plan = "free"
            self.plan_expires_at = None

    def _fake_snapshot(_db, _tenant):
        return _FakeSnapshot()

    monkeypatch.setattr(gating, "compute_usage_snapshot", _fake_snapshot)

    with pytest.raises(HTTPException) as exc:
        gating.enforce_capacity(db, "t", "project_count")
    assert exc.value.status_code == 402
    body = exc.value.detail
    assert isinstance(body, dict)
    assert body["code"] == "billing.limit_exceeded"
    assert body["metric"] == "project_count"
    assert body["upgrade_url"] == "/admin/billing"


def test_enforce_capacity_allows_unlimited_enterprise(db: Session, monkeypatch) -> None:
    from app.domains.billing import gating

    class _FakeSnapshot:
        def __init__(self):
            self.project_count = 1_000_000
            self.project_limit = -1
            self.scenario_count = 0
            self.scenario_limit = -1
            self.run_count_month = 0
            self.run_limit_month = -1
            self.team_size = 0
            self.team_limit = -1
            self.storage_mb = 0
            self.storage_limit_mb = -1
            self.ai_token_spend_usd = 0.0
            self.ai_token_limit_usd = -1
            self.plan = "enterprise"
            self.plan_expires_at = None

    monkeypatch.setattr(gating, "compute_usage_snapshot", lambda *_: _FakeSnapshot())

    for metric in ("project_count", "team_size", "scenario_count", "run_count_month"):
        gating.enforce_capacity(db, "tenant-ent", metric)


def test_enforce_capacity_with_delta(db: Session, monkeypatch) -> None:
    """A delta>1 (e.g. bulk import) should also be respected."""
    from app.domains.billing import gating

    class _FakeSnapshot:
        def __init__(self):
            self.project_count = 0
            self.project_limit = 5
            self.scenario_count = 48
            self.scenario_limit = 50
            self.run_count_month = 0
            self.run_limit_month = 100
            self.team_size = 0
            self.team_limit = 2
            self.storage_mb = 0
            self.storage_limit_mb = 1024
            self.ai_token_spend_usd = 0.0
            self.ai_token_limit_usd = 2.0
            self.plan = "free"
            self.plan_expires_at = None

    monkeypatch.setattr(gating, "compute_usage_snapshot", lambda *_: _FakeSnapshot())

    # delta=2 → 48+2 = 50, which equals the limit → still allowed
    gating.enforce_capacity(db, "t", "scenario_count", delta=2)
    # delta=3 → 48+3 = 51, exceeds 50 → 402
    with pytest.raises(HTTPException) as exc:
        gating.enforce_capacity(db, "t", "scenario_count", delta=3)
    assert exc.value.status_code == 402


def test_enforce_capacity_respects_paid_plan_limits(db: Session) -> None:
    """End-to-end: switch tenant to starter plan, check limits widen."""
    set_plan(db, "tenant-paid", "starter")
    db.commit()
    # starter allows 25 projects — fresh tenant has 0 projects → allowed
    enforce_capacity(db, "tenant-paid", "project_count")
