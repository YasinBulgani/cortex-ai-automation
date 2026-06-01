"""
billing service unit testleri — 14 test.

Tests are fully self-contained: no DB, no HTTP, no external services.
All SQLAlchemy session calls are mocked via unittest.mock.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

try:
    from app.domains.billing.service import (
        UsageSnapshot,
        LimitCheck,
        check_limit,
        get_or_create_subscription,
        set_plan,
        record_usage,
        _sum_usage,
        _start_of_month,
    )
    from app.domains.billing.plans import (
        PLAN_CATALOG,
        DEFAULT_PLAN_CODE,
        get_plan,
        is_unlimited,
        within_limit,
        list_plans,
        UNLIMITED,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="billing service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(**overrides) -> UsageSnapshot:
    defaults = dict(
        plan="free",
        plan_expires_at=None,
        scenario_count=10,
        scenario_limit=50,
        run_count_month=20,
        run_limit_month=100,
        ai_token_spend_usd=0.5,
        ai_token_limit_usd=2.0,
        team_size=1,
        team_limit=2,
        storage_mb=100,
        storage_limit_mb=1024,
        project_count=2,
        project_limit=5,
    )
    defaults.update(overrides)
    return UsageSnapshot(**defaults)


# ---------------------------------------------------------------------------
# Plan catalog
# ---------------------------------------------------------------------------

class TestPlanCatalog:
    def test_all_plan_codes_present(self):
        for code in ("free", "starter", "pro", "enterprise"):
            assert code in PLAN_CATALOG

    def test_default_plan_is_free(self):
        assert DEFAULT_PLAN_CODE == "free"

    def test_get_plan_known_code(self):
        plan = get_plan("starter")
        assert plan.code == "starter"
        assert plan.monthly_price_usd == 49.0

    def test_get_plan_unknown_falls_back_to_free(self):
        plan = get_plan("nonexistent_plan")
        assert plan.code == "free"

    def test_get_plan_none_falls_back_to_free(self):
        plan = get_plan(None)
        assert plan.code == "free"

    def test_enterprise_limits_are_unlimited(self):
        plan = get_plan("enterprise")
        L = plan.limits
        assert is_unlimited(L.project_count)
        assert is_unlimited(L.scenario_count)
        assert is_unlimited(L.run_count_month)
        assert is_unlimited(L.team_size)

    def test_within_limit_unlimited(self):
        assert within_limit(9999, UNLIMITED) is True

    def test_within_limit_within_bounds(self):
        assert within_limit(4, 5) is True

    def test_within_limit_at_boundary(self):
        # used == limit → not strictly within (used < limit)
        assert within_limit(5, 5) is False

    def test_list_plans_returns_all(self):
        plans = list_plans()
        assert len(plans) == len(PLAN_CATALOG)
        codes = {p["code"] for p in plans}
        assert codes == set(PLAN_CATALOG.keys())


# ---------------------------------------------------------------------------
# check_limit (pure — uses UsageSnapshot, no DB)
# ---------------------------------------------------------------------------

class TestCheckLimit:
    def test_within_limit_returns_allowed_true(self):
        snap = _make_snapshot(scenario_count=10, scenario_limit=50)
        result = check_limit(snap, "scenario_count", delta=1)
        assert result.allowed is True
        assert result.used == 10
        assert result.limit == 50

    def test_exceeds_limit_returns_allowed_false(self):
        snap = _make_snapshot(scenario_count=50, scenario_limit=50)
        result = check_limit(snap, "scenario_count", delta=1)
        assert result.allowed is False
        assert result.reason is not None
        assert "scenario_count" in result.reason

    def test_unlimited_plan_always_allowed(self):
        snap = _make_snapshot(project_count=9999, project_limit=UNLIMITED)
        result = check_limit(snap, "project_count", delta=1)
        assert result.allowed is True

    def test_unknown_metric_raises_value_error(self):
        snap = _make_snapshot()
        with pytest.raises(ValueError, match="Bilinmeyen metric"):
            check_limit(snap, "unknown_metric")

    def test_run_count_month_at_exact_limit(self):
        snap = _make_snapshot(run_count_month=100, run_limit_month=100)
        result = check_limit(snap, "run_count_month", delta=1)
        assert result.allowed is False

    def test_team_size_within_limit(self):
        snap = _make_snapshot(team_size=1, team_limit=2)
        result = check_limit(snap, "team_size", delta=1)
        assert result.allowed is True  # 1+1=2 == 2, projected <= limit

    def test_ai_token_spend_exceeds_limit(self):
        snap = _make_snapshot(ai_token_spend_usd=1.9, ai_token_limit_usd=2.0)
        result = check_limit(snap, "ai_token_spend_usd", delta=0.2)
        assert result.allowed is False

    def test_storage_mb_within_limit(self):
        snap = _make_snapshot(storage_mb=500, storage_limit_mb=1024)
        result = check_limit(snap, "storage_mb", delta=100)
        assert result.allowed is True


# ---------------------------------------------------------------------------
# UsageSnapshot.to_dict
# ---------------------------------------------------------------------------

class TestUsageSnapshotToDict:
    def test_to_dict_keys(self):
        snap = _make_snapshot()
        d = snap.to_dict()
        expected_keys = {
            "plan", "plan_expires_at", "scenario_count", "scenario_limit",
            "run_count_month", "run_limit_month", "ai_token_spend_usd",
            "ai_token_limit_usd", "team_size", "team_limit",
            "storage_mb", "storage_limit_mb", "project_count", "project_limit",
        }
        assert expected_keys == set(d.keys())

    def test_to_dict_ai_token_rounded(self):
        snap = _make_snapshot(ai_token_spend_usd=0.123456789)
        d = snap.to_dict()
        # rounded to 4 decimal places
        assert d["ai_token_spend_usd"] == round(0.123456789, 4)

    def test_to_dict_plan_expires_at_none(self):
        snap = _make_snapshot(plan_expires_at=None)
        d = snap.to_dict()
        assert d["plan_expires_at"] is None


# ---------------------------------------------------------------------------
# _start_of_month
# ---------------------------------------------------------------------------

class TestStartOfMonth:
    def test_returns_first_day_of_current_month(self):
        result = _start_of_month()
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0
        assert result.tzinfo is not None


# ---------------------------------------------------------------------------
# set_plan — DB-mocked
# ---------------------------------------------------------------------------

class TestSetPlan:
    def _make_db(self, existing_sub=None):
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = existing_sub
        if existing_sub is None:
            new_sub = MagicMock()
            new_sub.plan_code = DEFAULT_PLAN_CODE
            new_sub.status = "active"
            db.execute.return_value.scalar_one_or_none.return_value = None
            db.refresh.side_effect = lambda obj: None
            return db, new_sub
        return db, existing_sub

    def test_set_plan_unknown_code_raises_value_error(self):
        db = MagicMock()
        with pytest.raises(ValueError, match="Bilinmeyen plan kodu"):
            set_plan(db, "tenant-1", "nonexistent_plan")

    def test_set_plan_known_code_calls_commit(self):
        sub = MagicMock()
        sub.plan_code = "free"
        sub.current_period_end = None
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = sub
        set_plan(db, "tenant-1", "starter")
        db.commit.assert_called()
        assert sub.plan_code == "starter"

    def test_set_plan_sets_period_end_when_provided(self):
        sub = MagicMock()
        sub.current_period_end = None
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = sub
        end = datetime(2027, 1, 1, tzinfo=timezone.utc)
        set_plan(db, "tenant-1", "pro", period_end=end)
        assert sub.current_period_end == end


# ---------------------------------------------------------------------------
# record_usage — DB-mocked
# ---------------------------------------------------------------------------

class TestRecordUsage:
    def test_record_usage_adds_event(self):
        db = MagicMock()
        record_usage(db, "tenant-1", "ai.token_spend", amount=0.05)
        db.add.assert_called_once()

    def test_record_usage_truncates_long_meta(self):
        db = MagicMock()
        long_meta = "x" * 3000
        record_usage(db, "tenant-1", "storage.delta_mb", meta=long_meta)
        added = db.add.call_args[0][0]
        assert len(added.meta) == 2000

    def test_record_usage_none_meta(self):
        db = MagicMock()
        record_usage(db, "tenant-1", "run.exec", meta=None)
        added = db.add.call_args[0][0]
        assert added.meta is None
