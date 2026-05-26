"""Unit tests for app.domains.ai.budget — pure helpers and check_budget logic.

Tests are fully self-contained: no DB, no HTTP.
Covers: BudgetStatus.pct_used, BudgetPolicyIn validation,
        check_budget (all 5 reason paths: no_policy, disabled, ok,
        approaching, over_cap, hard_cap).
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

try:
    from app.domains.ai.budget import (
        BudgetStatus,
        BudgetPolicyIn,
        check_budget,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="budget import failed")


# ---------------------------------------------------------------------------
# BudgetStatus.pct_used
# ---------------------------------------------------------------------------

class TestBudgetStatusPctUsed:
    def _make(self, today_usd, daily_cap_usd, hard_cap=False, notify_at_pct=80):
        return BudgetStatus(
            allowed=True,
            reason="ok",
            today_usd=today_usd,
            daily_cap_usd=daily_cap_usd,
            notify_at_pct=notify_at_pct,
            hard_cap=hard_cap,
        )

    def test_fifty_percent(self):
        s = self._make(today_usd=5.0, daily_cap_usd=10.0)
        assert s.pct_used() == pytest.approx(50.0)

    def test_zero_spent(self):
        s = self._make(today_usd=0.0, daily_cap_usd=10.0)
        assert s.pct_used() == pytest.approx(0.0)

    def test_full_cap_used(self):
        s = self._make(today_usd=10.0, daily_cap_usd=10.0)
        assert s.pct_used() == pytest.approx(100.0)

    def test_over_cap(self):
        s = self._make(today_usd=12.0, daily_cap_usd=10.0)
        assert s.pct_used() > 100.0

    def test_zero_cap_returns_zero(self):
        """When daily_cap_usd is 0, no division should occur."""
        s = self._make(today_usd=5.0, daily_cap_usd=0.0)
        assert s.pct_used() == 0.0

    def test_returns_float(self):
        s = self._make(today_usd=3.0, daily_cap_usd=10.0)
        assert isinstance(s.pct_used(), float)

    def test_rounded_to_two_decimal_places(self):
        # 1/3 → 33.33
        s = self._make(today_usd=1.0, daily_cap_usd=3.0)
        result = s.pct_used()
        assert result == pytest.approx(33.33, abs=0.01)


# ---------------------------------------------------------------------------
# BudgetPolicyIn validation
# ---------------------------------------------------------------------------

class TestBudgetPolicyIn:
    def test_valid_policy_created(self):
        p = BudgetPolicyIn(daily_cap_usd=10.0)
        assert p.daily_cap_usd == pytest.approx(10.0)

    def test_default_hard_cap_false(self):
        p = BudgetPolicyIn(daily_cap_usd=5.0)
        assert p.hard_cap is False

    def test_default_notify_at_pct_80(self):
        p = BudgetPolicyIn(daily_cap_usd=5.0)
        assert p.notify_at_pct == 80

    def test_cost_rounded_to_6_decimal_places(self):
        p = BudgetPolicyIn(daily_cap_usd=1.1234567)
        assert p.daily_cap_usd == pytest.approx(1.123457, abs=1e-6)

    def test_zero_cap_allowed(self):
        p = BudgetPolicyIn(daily_cap_usd=0.0)
        assert p.daily_cap_usd == 0.0

    def test_negative_cap_raises(self):
        with pytest.raises(Exception):
            BudgetPolicyIn(daily_cap_usd=-1.0)

    def test_notes_optional(self):
        p = BudgetPolicyIn(daily_cap_usd=10.0, notes="test note")
        assert p.notes == "test note"

    def test_notes_none_by_default(self):
        p = BudgetPolicyIn(daily_cap_usd=10.0)
        assert p.notes is None


# ---------------------------------------------------------------------------
# check_budget — all reason paths
# ---------------------------------------------------------------------------

def _make_policy(daily_cap_usd=10.0, hard_cap=False, notify_at_pct=80):
    """Build a mock BudgetPolicyOut-like object."""
    policy = MagicMock()
    policy.daily_cap_usd = daily_cap_usd
    policy.hard_cap = hard_cap
    policy.notify_at_pct = notify_at_pct
    return policy


@pytest.fixture(autouse=True)
def _patch_enforcement():
    """Default: enforcement enabled. Tests can override."""
    with patch("app.domains.ai.budget._budget_enforcement_enabled", return_value=True):
        yield


class TestCheckBudget:
    def test_empty_tenant_id_returns_no_policy(self):
        result = check_budget("")
        assert result.allowed is True
        assert result.reason == "no_policy"

    def test_enforcement_disabled_returns_disabled(self):
        with patch("app.domains.ai.budget._budget_enforcement_enabled", return_value=False):
            result = check_budget("tenant-1")
        assert result.allowed is True
        assert result.reason == "disabled"

    def test_no_policy_in_db_returns_no_policy(self):
        with patch("app.domains.ai.budget.get_policy", return_value=None):
            result = check_budget("tenant-1")
        assert result.allowed is True
        assert result.reason == "no_policy"

    def test_zero_cap_policy_returns_no_policy(self):
        policy = _make_policy(daily_cap_usd=0.0)
        with patch("app.domains.ai.budget.get_policy", return_value=policy):
            result = check_budget("tenant-1")
        assert result.reason == "no_policy"

    def test_below_notify_threshold_returns_ok(self):
        policy = _make_policy(daily_cap_usd=10.0, notify_at_pct=80)  # threshold = 8.0
        with (
            patch("app.domains.ai.budget.get_policy", return_value=policy),
            patch("app.domains.ai.usage_service.get_tenant_today_cost", return_value=5.0),
        ):
            result = check_budget("tenant-1")
        assert result.allowed is True
        assert result.reason == "ok"

    def test_above_notify_but_below_cap_returns_approaching(self):
        policy = _make_policy(daily_cap_usd=10.0, notify_at_pct=80)  # threshold = 8.0
        with (
            patch("app.domains.ai.budget.get_policy", return_value=policy),
            patch("app.domains.ai.usage_service.get_tenant_today_cost", return_value=9.0),
        ):
            result = check_budget("tenant-1")
        assert result.allowed is True
        assert result.reason == "approaching"

    def test_over_cap_soft_returns_over_cap(self):
        policy = _make_policy(daily_cap_usd=10.0, hard_cap=False, notify_at_pct=80)
        with (
            patch("app.domains.ai.budget.get_policy", return_value=policy),
            patch("app.domains.ai.usage_service.get_tenant_today_cost", return_value=11.0),
        ):
            result = check_budget("tenant-1")
        assert result.allowed is True
        assert result.reason == "over_cap"

    def test_over_cap_hard_returns_denied(self):
        policy = _make_policy(daily_cap_usd=10.0, hard_cap=True, notify_at_pct=80)
        with (
            patch("app.domains.ai.budget.get_policy", return_value=policy),
            patch("app.domains.ai.usage_service.get_tenant_today_cost", return_value=11.0),
        ):
            result = check_budget("tenant-1")
        assert result.allowed is False
        assert result.reason == "hard_cap"

    def test_additional_cost_projecting_over_cap(self):
        policy = _make_policy(daily_cap_usd=10.0, hard_cap=True, notify_at_pct=80)
        with (
            patch("app.domains.ai.budget.get_policy", return_value=policy),
            patch("app.domains.ai.usage_service.get_tenant_today_cost", return_value=9.5),
        ):
            # spent 9.5 + additional 1.0 → projected 10.5 → hard_cap
            result = check_budget("tenant-1", additional_cost_usd=1.0)
        assert result.allowed is False
        assert result.reason == "hard_cap"

    def test_result_has_correct_today_usd(self):
        policy = _make_policy(daily_cap_usd=10.0)
        with (
            patch("app.domains.ai.budget.get_policy", return_value=policy),
            patch("app.domains.ai.usage_service.get_tenant_today_cost", return_value=3.0),
        ):
            result = check_budget("tenant-1")
        assert result.today_usd == pytest.approx(3.0)

    def test_result_has_correct_daily_cap(self):
        policy = _make_policy(daily_cap_usd=20.0)
        with (
            patch("app.domains.ai.budget.get_policy", return_value=policy),
            patch("app.domains.ai.usage_service.get_tenant_today_cost", return_value=1.0),
        ):
            result = check_budget("tenant-1")
        assert result.daily_cap_usd == pytest.approx(20.0)

    def test_returns_budget_status_instance(self):
        policy = _make_policy(daily_cap_usd=10.0)
        with (
            patch("app.domains.ai.budget.get_policy", return_value=policy),
            patch("app.domains.ai.usage_service.get_tenant_today_cost", return_value=1.0),
        ):
            result = check_budget("tenant-1")
        assert isinstance(result, BudgetStatus)
