"""Unit tests for app.domains.billing.plans — plan catalog pure helpers.

Tests are fully self-contained: no DB, no Stripe, no HTTP.
Covers: PLAN_CATALOG, get_plan, is_unlimited, within_limit, list_plans,
Plan.to_dict, PlanLimits, UNLIMITED constant.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.billing.plans import (
        get_plan,
        is_unlimited,
        within_limit,
        list_plans,
        PLAN_CATALOG,
        UNLIMITED,
        Plan,
        PlanLimits,
        DEFAULT_PLAN_CODE,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="billing.plans import failed")


# ---------------------------------------------------------------------------
# PLAN_CATALOG structure
# ---------------------------------------------------------------------------

class TestPlanCatalog:
    def test_catalog_has_expected_plans(self):
        for code in ("free", "starter", "pro", "enterprise"):
            assert code in PLAN_CATALOG

    def test_each_plan_has_code(self):
        for code, plan in PLAN_CATALOG.items():
            assert plan.code == code

    def test_each_plan_has_limits(self):
        for plan in PLAN_CATALOG.values():
            assert isinstance(plan.limits, PlanLimits)

    def test_free_plan_has_zero_price(self):
        assert PLAN_CATALOG["free"].monthly_price_usd == 0.0

    def test_enterprise_is_contact_sales(self):
        assert PLAN_CATALOG["enterprise"].is_contact_sales is True

    def test_other_plans_not_contact_sales(self):
        for code in ("free", "starter", "pro"):
            assert PLAN_CATALOG[code].is_contact_sales is False

    def test_enterprise_has_unlimited_projects(self):
        assert PLAN_CATALOG["enterprise"].limits.project_count == UNLIMITED

    def test_free_plan_has_finite_limits(self):
        free = PLAN_CATALOG["free"]
        assert free.limits.project_count > 0
        assert free.limits.run_count_month > 0


# ---------------------------------------------------------------------------
# get_plan
# ---------------------------------------------------------------------------

class TestGetPlan:
    def test_known_code_returns_plan(self):
        plan = get_plan("pro")
        assert plan.code == "pro"

    def test_none_returns_default_plan(self):
        plan = get_plan(None)
        assert plan.code == DEFAULT_PLAN_CODE

    def test_empty_string_returns_default_plan(self):
        plan = get_plan("")
        assert plan.code == DEFAULT_PLAN_CODE

    def test_unknown_code_falls_back_to_free(self):
        plan = get_plan("nonexistent_plan")
        assert plan.code == "free"

    def test_returns_plan_instance(self):
        assert isinstance(get_plan("starter"), Plan)


# ---------------------------------------------------------------------------
# is_unlimited
# ---------------------------------------------------------------------------

class TestIsUnlimited:
    def test_unlimited_constant_returns_true(self):
        assert is_unlimited(UNLIMITED) is True

    def test_positive_value_returns_false(self):
        assert is_unlimited(100) is False

    def test_zero_returns_false(self):
        assert is_unlimited(0) is False

    def test_returns_bool(self):
        assert isinstance(is_unlimited(UNLIMITED), bool)
        assert isinstance(is_unlimited(10), bool)


# ---------------------------------------------------------------------------
# within_limit
# ---------------------------------------------------------------------------

class TestWithinLimit:
    def test_unlimited_limit_always_true(self):
        assert within_limit(1_000_000, UNLIMITED) is True

    def test_below_limit_returns_true(self):
        assert within_limit(5, 10) is True

    def test_at_limit_returns_false(self):
        # "used < limit" → at limit is False
        assert within_limit(10, 10) is False

    def test_above_limit_returns_false(self):
        assert within_limit(15, 10) is False

    def test_zero_used_always_within(self):
        assert within_limit(0, 1) is True

    def test_float_limits_work(self):
        assert within_limit(1.5, 2.0) is True
        assert within_limit(2.0, 2.0) is False


# ---------------------------------------------------------------------------
# Plan.to_dict
# ---------------------------------------------------------------------------

class TestPlanToDict:
    def test_to_dict_returns_dict(self):
        plan = get_plan("starter")
        d = plan.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_code(self):
        d = get_plan("pro").to_dict()
        assert d["code"] == "pro"

    def test_to_dict_has_limits_as_dict(self):
        d = get_plan("free").to_dict()
        assert isinstance(d["limits"], dict)
        assert "project_count" in d["limits"]

    def test_to_dict_has_features(self):
        d = get_plan("starter").to_dict()
        assert "features" in d


# ---------------------------------------------------------------------------
# list_plans
# ---------------------------------------------------------------------------

class TestListPlans:
    def test_returns_list(self):
        result = list_plans()
        assert isinstance(result, list)

    def test_returns_all_plans(self):
        result = list_plans()
        codes = {p["code"] for p in result}
        assert {"free", "starter", "pro", "enterprise"} <= codes

    def test_each_entry_is_dict(self):
        for entry in list_plans():
            assert isinstance(entry, dict)
            assert "code" in entry
            assert "limits" in entry
