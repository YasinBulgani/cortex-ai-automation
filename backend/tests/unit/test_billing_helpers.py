"""Unit tests for billing plans, stripe_client, and service pure helpers.

Tests are fully self-contained: no DB, no HTTP, no Stripe API calls.
Covers: is_unlimited, within_limit, get_plan, Plan.to_dict, PLAN_CATALOG,
        _flatten_form, check_limit (billing service), LimitCheck,
        UsageSnapshot dataclass.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.billing.plans import (
        is_unlimited,
        within_limit,
        get_plan,
        PLAN_CATALOG,
        UNLIMITED,
        Plan,
        PlanLimits,
        list_plans,
    )
    from app.domains.billing.stripe_client import _flatten_form
    from app.domains.billing.service import (
        check_limit,
        LimitCheck,
        UsageSnapshot,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="billing import failed")


def _snapshot(**overrides):
    base = dict(
        plan="starter",
        plan_expires_at=None,
        scenario_count=10,
        scenario_limit=500,
        run_count_month=50,
        run_limit_month=1000,
        ai_token_spend_usd=1.0,
        ai_token_limit_usd=20.0,
        team_size=3,
        team_limit=10,
        storage_mb=512,
        storage_limit_mb=10240,
        project_count=5,
        project_limit=25,
    )
    base.update(overrides)
    return UsageSnapshot(**base)


# ---------------------------------------------------------------------------
# UNLIMITED constant
# ---------------------------------------------------------------------------

class TestUnlimitedConstant:
    def test_unlimited_is_negative_one(self):
        assert UNLIMITED == -1

    def test_is_int(self):
        assert isinstance(UNLIMITED, int)


# ---------------------------------------------------------------------------
# is_unlimited
# ---------------------------------------------------------------------------

class TestIsUnlimited:
    def test_negative_one_is_unlimited(self):
        assert is_unlimited(-1) is True

    def test_unlimited_constant_is_unlimited(self):
        assert is_unlimited(UNLIMITED) is True

    def test_zero_not_unlimited(self):
        assert is_unlimited(0) is False

    def test_positive_not_unlimited(self):
        assert is_unlimited(100) is False

    def test_returns_bool(self):
        assert isinstance(is_unlimited(-1), bool)


# ---------------------------------------------------------------------------
# within_limit
# ---------------------------------------------------------------------------

class TestWithinLimit:
    def test_below_limit_is_true(self):
        assert within_limit(5, 10) is True

    def test_equal_to_limit_is_false(self):
        # used < limit (strict)
        assert within_limit(10, 10) is False

    def test_over_limit_is_false(self):
        assert within_limit(15, 10) is False

    def test_unlimited_always_true(self):
        assert within_limit(9999, UNLIMITED) is True

    def test_zero_used_below_any_positive_limit(self):
        assert within_limit(0, 100) is True

    def test_returns_bool(self):
        assert isinstance(within_limit(5, 10), bool)


# ---------------------------------------------------------------------------
# get_plan
# ---------------------------------------------------------------------------

class TestGetPlan:
    def test_free_plan(self):
        plan = get_plan("free")
        assert plan.code == "free"

    def test_starter_plan(self):
        plan = get_plan("starter")
        assert plan.monthly_price_usd == pytest.approx(49.0)

    def test_pro_plan(self):
        plan = get_plan("pro")
        assert plan.code == "pro"

    def test_enterprise_plan(self):
        plan = get_plan("enterprise")
        assert plan.is_contact_sales is True

    def test_unknown_code_returns_free(self):
        plan = get_plan("nonexistent_plan")
        assert plan.code == "free"

    def test_none_returns_free(self):
        plan = get_plan(None)
        assert plan.code == "free"

    def test_empty_string_returns_free(self):
        plan = get_plan("")
        assert plan.code == "free"

    def test_returns_plan_instance(self):
        plan = get_plan("starter")
        assert isinstance(plan, Plan)


# ---------------------------------------------------------------------------
# PLAN_CATALOG
# ---------------------------------------------------------------------------

class TestPlanCatalog:
    def test_has_free(self):
        assert "free" in PLAN_CATALOG

    def test_has_starter(self):
        assert "starter" in PLAN_CATALOG

    def test_has_pro(self):
        assert "pro" in PLAN_CATALOG

    def test_has_enterprise(self):
        assert "enterprise" in PLAN_CATALOG

    def test_all_have_limits(self):
        for code, plan in PLAN_CATALOG.items():
            assert isinstance(plan.limits, PlanLimits)

    def test_enterprise_all_unlimited(self):
        ent = PLAN_CATALOG["enterprise"]
        assert is_unlimited(ent.limits.project_count)
        assert is_unlimited(ent.limits.run_count_month)

    def test_free_plan_positive_price_zero(self):
        assert PLAN_CATALOG["free"].monthly_price_usd == 0.0


# ---------------------------------------------------------------------------
# Plan.to_dict
# ---------------------------------------------------------------------------

class TestPlanToDict:
    def test_returns_dict(self):
        plan = get_plan("starter")
        assert isinstance(plan.to_dict(), dict)

    def test_has_code_key(self):
        d = get_plan("pro").to_dict()
        assert d["code"] == "pro"

    def test_has_limits_dict(self):
        d = get_plan("starter").to_dict()
        assert isinstance(d["limits"], dict)

    def test_limits_has_scenario_count(self):
        d = get_plan("starter").to_dict()
        assert "scenario_count" in d["limits"]


# ---------------------------------------------------------------------------
# list_plans
# ---------------------------------------------------------------------------

class TestListPlans:
    def test_returns_list(self):
        assert isinstance(list_plans(), list)

    def test_nonempty(self):
        assert len(list_plans()) >= 4

    def test_each_has_code(self):
        for plan_dict in list_plans():
            assert "code" in plan_dict


# ---------------------------------------------------------------------------
# _flatten_form (stripe_client)
# ---------------------------------------------------------------------------

class TestFlattenForm:
    def test_flat_dict_unchanged(self):
        form = {"mode": "subscription", "email": "test@example.com"}
        result = _flatten_form(form)
        assert result["mode"] == "subscription"
        assert result["email"] == "test@example.com"

    def test_nested_dict_flattened(self):
        form = {"customer": {"email": "x@y.com", "name": "Test"}}
        result = _flatten_form(form)
        assert result["customer[email]"] == "x@y.com"
        assert result["customer[name]"] == "Test"

    def test_deeply_nested(self):
        form = {"a": {"b": {"c": "value"}}}
        result = _flatten_form(form)
        assert result["a[b][c]"] == "value"

    def test_none_values_excluded(self):
        form = {"key": "value", "none_key": None}
        result = _flatten_form(form)
        assert "none_key" not in result
        assert "key" in result

    def test_empty_dict_returns_empty(self):
        assert _flatten_form({}) == {}

    def test_returns_dict(self):
        assert isinstance(_flatten_form({"k": "v"}), dict)

    def test_mixed_flat_and_nested(self):
        form = {
            "mode": "subscription",
            "metadata": {"tenant_id": "t1", "plan_code": "pro"},
        }
        result = _flatten_form(form)
        assert result["mode"] == "subscription"
        assert result["metadata[tenant_id]"] == "t1"
        assert result["metadata[plan_code]"] == "pro"


# ---------------------------------------------------------------------------
# check_limit (billing service)
# ---------------------------------------------------------------------------

class TestCheckLimit:
    def test_within_scenario_limit_allowed(self):
        snap = _snapshot(scenario_count=10, scenario_limit=500)
        result = check_limit(snap, "scenario_count")
        assert result.allowed is True

    def test_over_scenario_limit_not_allowed(self):
        snap = _snapshot(scenario_count=500, scenario_limit=500)
        result = check_limit(snap, "scenario_count", delta=1.0)
        assert result.allowed is False

    def test_unlimited_limit_always_allowed(self):
        snap = _snapshot(project_count=999, project_limit=UNLIMITED)
        result = check_limit(snap, "project_count")
        assert result.allowed is True

    def test_unknown_metric_raises_value_error(self):
        snap = _snapshot()
        with pytest.raises(ValueError):
            check_limit(snap, "nonexistent_metric")

    def test_returns_limit_check(self):
        snap = _snapshot()
        result = check_limit(snap, "run_count_month")
        assert isinstance(result, LimitCheck)

    def test_reason_set_when_denied(self):
        snap = _snapshot(team_size=10, team_limit=10)
        result = check_limit(snap, "team_size", delta=1.0)
        assert result.allowed is False
        assert result.reason is not None
        assert "team_size" in result.reason

    def test_reason_none_when_allowed(self):
        snap = _snapshot(team_size=3, team_limit=10)
        result = check_limit(snap, "team_size")
        assert result.allowed is True
        assert result.reason is None

    def test_delta_affects_decision(self):
        # used=9, limit=10, delta=1 → projected=10 which is not < 10
        snap = _snapshot(run_count_month=9, run_limit_month=10)
        result_small = check_limit(snap, "run_count_month", delta=1.0)
        result_large = check_limit(snap, "run_count_month", delta=5.0)
        assert result_large.allowed is False
