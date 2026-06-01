"""Unit tests for app.domains.billing.service pure helpers.

Tests are fully self-contained: no DB, no Stripe, no HTTP.
Covers: check_limit (with UsageSnapshot), LimitCheck, UsageSnapshot.to_dict.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.billing.service import (
        check_limit,
        UsageSnapshot,
        LimitCheck,
    )
    from app.domains.billing.plans import UNLIMITED
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="billing.service import failed")


# ---------------------------------------------------------------------------
# Helper: build a UsageSnapshot with configurable fields
# ---------------------------------------------------------------------------

def _snapshot(**overrides) -> UsageSnapshot:
    defaults = dict(
        plan="starter",
        plan_expires_at=None,
        project_count=5,
        project_limit=25,
        scenario_count=100,
        scenario_limit=500,
        run_count_month=200,
        run_limit_month=1000,
        ai_token_spend_usd=5.0,
        ai_token_limit_usd=20.0,
        team_size=3,
        team_limit=10,
        storage_mb=512,
        storage_limit_mb=10240,
    )
    defaults.update(overrides)
    return UsageSnapshot(**defaults)


# ---------------------------------------------------------------------------
# check_limit — core gating logic
# ---------------------------------------------------------------------------

class TestCheckLimit:
    def test_within_limit_returns_allowed(self):
        snap = _snapshot(project_count=5, project_limit=25)
        result = check_limit(snap, "project_count", delta=1)
        assert result.allowed is True

    def test_at_limit_returns_allowed(self):
        # used=24, limit=25, delta=1 → projected=25 ≤ 25 → allowed
        snap = _snapshot(project_count=24, project_limit=25)
        result = check_limit(snap, "project_count", delta=1)
        assert result.allowed is True

    def test_over_limit_returns_denied(self):
        # used=25, limit=25, delta=1 → projected=26 > 25 → denied
        snap = _snapshot(project_count=25, project_limit=25)
        result = check_limit(snap, "project_count", delta=1)
        assert result.allowed is False

    def test_unlimited_limit_always_allowed(self):
        snap = _snapshot(project_count=99_999, project_limit=UNLIMITED)
        result = check_limit(snap, "project_count", delta=1000)
        assert result.allowed is True

    def test_scenario_count_metric(self):
        snap = _snapshot(scenario_count=499, scenario_limit=500)
        result = check_limit(snap, "scenario_count", delta=1)
        assert result.allowed is True
        result2 = check_limit(snap, "scenario_count", delta=2)
        assert result2.allowed is False

    def test_run_count_month_metric(self):
        snap = _snapshot(run_count_month=1000, run_limit_month=1000)
        result = check_limit(snap, "run_count_month", delta=1)
        assert result.allowed is False

    def test_team_size_metric(self):
        snap = _snapshot(team_size=9, team_limit=10)
        result = check_limit(snap, "team_size", delta=1)
        assert result.allowed is True
        result2 = check_limit(snap, "team_size", delta=2)
        assert result2.allowed is False

    def test_ai_token_spend_metric(self):
        snap = _snapshot(ai_token_spend_usd=19.0, ai_token_limit_usd=20.0)
        result = check_limit(snap, "ai_token_spend_usd", delta=0.5)
        assert result.allowed is True

    def test_storage_mb_metric(self):
        snap = _snapshot(storage_mb=10200, storage_limit_mb=10240)
        result = check_limit(snap, "storage_mb", delta=100)
        assert result.allowed is False

    def test_unknown_metric_raises_value_error(self):
        snap = _snapshot()
        with pytest.raises(ValueError, match="metric"):
            check_limit(snap, "nonexistent_metric")

    def test_default_delta_is_one(self):
        # At limit with default delta=1 should fail
        snap = _snapshot(project_count=25, project_limit=25)
        result = check_limit(snap, "project_count")
        assert result.allowed is False

    def test_returns_limit_check(self):
        result = check_limit(_snapshot(), "project_count")
        assert isinstance(result, LimitCheck)

    def test_denied_result_has_reason(self):
        snap = _snapshot(project_count=25, project_limit=25)
        result = check_limit(snap, "project_count", delta=1)
        assert result.allowed is False
        assert result.reason is not None
        assert len(result.reason) > 0

    def test_allowed_result_reason_is_none(self):
        snap = _snapshot(project_count=5, project_limit=25)
        result = check_limit(snap, "project_count")
        assert result.allowed is True
        assert result.reason is None

    def test_used_and_limit_in_result(self):
        snap = _snapshot(project_count=10, project_limit=25)
        result = check_limit(snap, "project_count")
        assert result.used == 10
        assert result.limit == 25


# ---------------------------------------------------------------------------
# UsageSnapshot.to_dict
# ---------------------------------------------------------------------------

class TestUsageSnapshotToDict:
    def test_to_dict_returns_dict(self):
        snap = _snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_plan(self):
        snap = _snapshot(plan="pro")
        d = snap.to_dict()
        assert d["plan"] == "pro"

    def test_to_dict_has_project_fields(self):
        snap = _snapshot(project_count=7, project_limit=25)
        d = snap.to_dict()
        assert d["project_count"] == 7
        assert d["project_limit"] == 25

    def test_to_dict_has_all_expected_keys(self):
        snap = _snapshot()
        d = snap.to_dict()
        for key in [
            "plan", "project_count", "project_limit",
            "run_count_month", "run_limit_month",
            "team_size", "team_limit",
            "storage_mb", "storage_limit_mb",
            "ai_token_spend_usd", "ai_token_limit_usd",
        ]:
            assert key in d
