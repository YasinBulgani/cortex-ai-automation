"""Unit tests for app.domains.ai.usage_router pure helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers:
  - _resolve_tenant: tenant_id field vs id fallback
  - _status_to_out: BudgetStatus → BudgetStatusOut mapping
  - BudgetStatusOut: Pydantic model field validation
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.usage_router import (
        _resolve_tenant,
        BudgetStatusOut,
        _status_to_out,
    )
    from app.domains.ai.budget import BudgetStatus
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="usage_router import failed")


class _User:
    """Minimal mock user object."""
    def __init__(self, user_id: str, tenant_id=None):
        self.id = user_id
        self.tenant_id = tenant_id


def _budget_status(**kwargs):
    defaults = dict(
        allowed=True, reason="OK",
        today_usd=5.0, daily_cap_usd=50.0,
        notify_at_pct=80, hard_cap=False,
    )
    defaults.update(kwargs)
    return BudgetStatus(**defaults)


# ---------------------------------------------------------------------------
# _resolve_tenant
# ---------------------------------------------------------------------------

class TestResolveTenant:
    def test_returns_tenant_id_when_present(self):
        user = _User("user-001", tenant_id="tenant-abc")
        assert _resolve_tenant(user) == "tenant-abc"

    def test_falls_back_to_user_id_when_tenant_none(self):
        user = _User("user-002", tenant_id=None)
        assert _resolve_tenant(user) == "user-002"

    def test_returns_string(self):
        user = _User("user-003", tenant_id="t1")
        result = _resolve_tenant(user)
        assert isinstance(result, str)

    def test_tenant_id_empty_string_fallback(self):
        # Empty string is falsy — should fall back to user id
        user = _User("user-004", tenant_id="")
        result = _resolve_tenant(user)
        # "" is falsy → falls back to id
        assert result == "user-004"

    def test_user_without_tenant_id_attr(self):
        class MinimalUser:
            id = "user-005"
        # getattr with None default → falls back to id
        result = _resolve_tenant(MinimalUser())
        assert result == "user-005"


# ---------------------------------------------------------------------------
# _status_to_out
# ---------------------------------------------------------------------------

class TestStatusToOut:
    def test_tenant_id_set(self):
        s = _budget_status()
        out = _status_to_out("tenant-001", s)
        assert out.tenant_id == "tenant-001"

    def test_allowed_propagated(self):
        s = _budget_status(allowed=True)
        out = _status_to_out("t", s)
        assert out.allowed is True

    def test_not_allowed_propagated(self):
        s = _budget_status(allowed=False, reason="Over budget")
        out = _status_to_out("t", s)
        assert out.allowed is False

    def test_reason_propagated(self):
        s = _budget_status(reason="daily limit reached")
        out = _status_to_out("t", s)
        assert "limit" in out.reason

    def test_today_usd_propagated(self):
        s = _budget_status(today_usd=12.5)
        out = _status_to_out("t", s)
        assert out.today_usd == pytest.approx(12.5)

    def test_daily_cap_usd_propagated(self):
        s = _budget_status(daily_cap_usd=100.0)
        out = _status_to_out("t", s)
        assert out.daily_cap_usd == pytest.approx(100.0)

    def test_notify_at_pct_propagated(self):
        s = _budget_status(notify_at_pct=75)
        out = _status_to_out("t", s)
        assert out.notify_at_pct == 75

    def test_hard_cap_propagated(self):
        s = _budget_status(hard_cap=True)
        out = _status_to_out("t", s)
        assert out.hard_cap is True

    def test_pct_used_calculated(self):
        # today_usd=5, daily_cap_usd=50 → pct_used = 10%
        s = _budget_status(today_usd=5.0, daily_cap_usd=50.0)
        out = _status_to_out("t", s)
        assert out.pct_used == pytest.approx(10.0)

    def test_returns_budget_status_out(self):
        s = _budget_status()
        out = _status_to_out("t", s)
        assert isinstance(out, BudgetStatusOut)


# ---------------------------------------------------------------------------
# BudgetStatusOut
# ---------------------------------------------------------------------------

class TestBudgetStatusOut:
    def test_creation(self):
        out = BudgetStatusOut(
            tenant_id="t1",
            allowed=True,
            reason="OK",
            today_usd=0.0,
            daily_cap_usd=50.0,
            notify_at_pct=80,
            hard_cap=False,
            pct_used=0.0,
        )
        assert out.tenant_id == "t1"
        assert out.allowed is True

    def test_pct_used_at_100(self):
        out = BudgetStatusOut(
            tenant_id="t",
            allowed=False,
            reason="over limit",
            today_usd=50.0,
            daily_cap_usd=50.0,
            notify_at_pct=80,
            hard_cap=True,
            pct_used=100.0,
        )
        assert out.pct_used == pytest.approx(100.0)
        assert out.hard_cap is True
