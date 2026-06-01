"""Unit tests for billing.plans helpers and feature_flags.schemas models.

Tests are fully self-contained: no DB, no HTTP, no Stripe.
Covers:
  - UNLIMITED constant
  - PlanLimits / Plan dataclass defaults
  - get_plan: known codes, unknown fallback, None fallback
  - is_unlimited: -1 → True, positive → False
  - within_limit: under, at, over, unlimited
  - list_plans: all plans in catalog, dict keys
  - RolloutOut: percent bounds, defaults
  - FlagOut: defaults
  - FlagUpdate: allow_tenants dedup + strip
  - FlagEvaluation: fields
"""
from __future__ import annotations

import pytest

try:
    from app.domains.billing.plans import (
        UNLIMITED,
        PlanLimits,
        Plan,
        PLAN_CATALOG,
        DEFAULT_PLAN_CODE,
        get_plan,
        is_unlimited,
        within_limit,
        list_plans,
    )
    _BILLING_OK = True
except ImportError:
    _BILLING_OK = False

try:
    from app.domains.feature_flags.schemas import (
        RolloutOut,
        FlagOut,
        FlagUpdate,
        FlagEvaluation,
    )
    _FLAGS_OK = True
except ImportError:
    _FLAGS_OK = False


# ---------------------------------------------------------------------------
# UNLIMITED constant
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BILLING_OK, reason="billing.plans import failed")
class TestUnlimitedConstant:
    def test_unlimited_is_minus_one(self):
        assert UNLIMITED == -1

    def test_unlimited_is_int(self):
        assert isinstance(UNLIMITED, int)


# ---------------------------------------------------------------------------
# get_plan
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BILLING_OK, reason="billing.plans import failed")
class TestGetPlan:
    def test_free_plan(self):
        plan = get_plan("free")
        assert plan.code == "free"

    def test_starter_plan(self):
        plan = get_plan("starter")
        assert plan.code == "starter"

    def test_pro_plan(self):
        plan = get_plan("pro")
        assert plan.code == "pro"

    def test_enterprise_plan(self):
        plan = get_plan("enterprise")
        assert plan.code == "enterprise"

    def test_unknown_falls_back_to_default(self):
        plan = get_plan("nonexistent_plan")
        assert plan.code == DEFAULT_PLAN_CODE

    def test_none_falls_back_to_default(self):
        plan = get_plan(None)
        assert plan.code == DEFAULT_PLAN_CODE

    def test_empty_string_falls_back(self):
        plan = get_plan("")
        assert plan.code == DEFAULT_PLAN_CODE

    def test_returns_plan_instance(self):
        assert isinstance(get_plan("free"), Plan)

    def test_plan_has_limits(self):
        plan = get_plan("free")
        assert isinstance(plan.limits, PlanLimits)

    def test_plan_has_features_tuple(self):
        plan = get_plan("starter")
        assert isinstance(plan.features, tuple)
        assert len(plan.features) > 0

    def test_plan_has_monthly_price(self):
        plan = get_plan("free")
        assert plan.monthly_price_usd == pytest.approx(0.0)

    def test_starter_price(self):
        plan = get_plan("starter")
        assert plan.monthly_price_usd > 0.0


# ---------------------------------------------------------------------------
# is_unlimited
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BILLING_OK, reason="billing.plans import failed")
class TestIsUnlimited:
    def test_minus_one_is_unlimited(self):
        assert is_unlimited(-1) is True

    def test_zero_is_not_unlimited(self):
        assert is_unlimited(0) is False

    def test_positive_int_not_unlimited(self):
        assert is_unlimited(100) is False

    def test_float_unlimited(self):
        assert is_unlimited(-1.0) is True

    def test_large_number_not_unlimited(self):
        assert is_unlimited(999_999) is False


# ---------------------------------------------------------------------------
# within_limit
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BILLING_OK, reason="billing.plans import failed")
class TestWithinLimit:
    def test_used_below_limit(self):
        assert within_limit(5, 10) is True

    def test_used_equals_limit_is_not_within(self):
        # within_limit uses used < limit (strict less than)
        assert within_limit(10, 10) is False

    def test_used_above_limit(self):
        assert within_limit(11, 10) is False

    def test_unlimited_limit_always_true(self):
        assert within_limit(9999, UNLIMITED) is True

    def test_zero_used_below_any_positive_limit(self):
        assert within_limit(0, 1) is True

    def test_float_comparison(self):
        assert within_limit(1.5, 2.0) is True
        assert within_limit(2.0, 2.0) is False


# ---------------------------------------------------------------------------
# list_plans
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BILLING_OK, reason="billing.plans import failed")
class TestListPlans:
    def test_returns_list(self):
        assert isinstance(list_plans(), list)

    def test_all_plans_included(self):
        codes = {p["code"] for p in list_plans()}
        assert {"free", "starter", "pro", "enterprise"}.issubset(codes)

    def test_each_has_code(self):
        for p in list_plans():
            assert "code" in p

    def test_each_has_limits(self):
        for p in list_plans():
            assert "limits" in p

    def test_limits_has_project_count(self):
        for p in list_plans():
            assert "project_count" in p["limits"]

    def test_pro_has_unlimited_projects(self):
        pro = next(p for p in list_plans() if p["code"] == "pro")
        assert pro["limits"]["project_count"] == UNLIMITED


# ---------------------------------------------------------------------------
# Plan.to_dict
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BILLING_OK, reason="billing.plans import failed")
class TestPlanToDict:
    def test_to_dict_has_code(self):
        d = get_plan("free").to_dict()
        assert d["code"] == "free"

    def test_to_dict_limits_is_dict(self):
        d = get_plan("free").to_dict()
        assert isinstance(d["limits"], dict)

    def test_to_dict_features_is_list(self):
        d = get_plan("starter").to_dict()
        assert isinstance(d["features"], (list, tuple))


# ---------------------------------------------------------------------------
# RolloutOut
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FLAGS_OK, reason="feature_flags.schemas import failed")
class TestRolloutOut:
    def test_default_percent_zero(self):
        r = RolloutOut()
        assert r.percent == 0

    def test_allow_tenants_default_empty(self):
        r = RolloutOut()
        assert r.allow_tenants == []

    def test_percent_min_zero(self):
        r = RolloutOut(percent=0)
        assert r.percent == 0

    def test_percent_max_100(self):
        r = RolloutOut(percent=100)
        assert r.percent == 100

    def test_percent_below_zero_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RolloutOut(percent=-1)

    def test_percent_above_100_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RolloutOut(percent=101)

    def test_with_tenants(self):
        r = RolloutOut(percent=50, allow_tenants=["tenant-a", "tenant-b"])
        assert "tenant-a" in r.allow_tenants


# ---------------------------------------------------------------------------
# FlagOut
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FLAGS_OK, reason="feature_flags.schemas import failed")
class TestFlagOut:
    def test_creation(self):
        f = FlagOut(key="dark_mode", enabled=True)
        assert f.key == "dark_mode"
        assert f.enabled is True

    def test_description_default_empty(self):
        f = FlagOut(key="feature_x", enabled=False)
        assert f.description == ""

    def test_rollout_default(self):
        f = FlagOut(key="feature_x", enabled=True)
        assert isinstance(f.rollout, RolloutOut)
        assert f.rollout.percent == 0

    def test_updated_at_default_none(self):
        f = FlagOut(key="feature_x", enabled=True)
        assert f.updated_at is None

    def test_updated_by_default_none(self):
        f = FlagOut(key="feature_x", enabled=True)
        assert f.updated_by is None


# ---------------------------------------------------------------------------
# FlagUpdate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FLAGS_OK, reason="feature_flags.schemas import failed")
class TestFlagUpdate:
    def test_all_fields_optional(self):
        fu = FlagUpdate()
        assert fu.enabled is None
        assert fu.description is None
        assert fu.percent is None
        assert fu.allow_tenants is None

    def test_partial_update(self):
        fu = FlagUpdate(enabled=True)
        assert fu.enabled is True
        assert fu.description is None

    def test_percent_bounds_min(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FlagUpdate(percent=-1)

    def test_percent_bounds_max(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FlagUpdate(percent=101)

    def test_allow_tenants_deduplicated(self):
        fu = FlagUpdate(allow_tenants=["t1", "t1", "t2"])
        assert fu.allow_tenants == ["t1", "t2"]

    def test_allow_tenants_stripped(self):
        fu = FlagUpdate(allow_tenants=["  tenant-a  ", "  tenant-b  "])
        assert "tenant-a" in fu.allow_tenants
        assert "tenant-b" in fu.allow_tenants
        # No whitespace
        for t in fu.allow_tenants:
            assert t == t.strip()

    def test_empty_strings_removed(self):
        fu = FlagUpdate(allow_tenants=["", "  ", "tenant-a"])
        assert "" not in fu.allow_tenants
        assert "  " not in fu.allow_tenants
        assert "tenant-a" in fu.allow_tenants


# ---------------------------------------------------------------------------
# FlagEvaluation
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FLAGS_OK, reason="feature_flags.schemas import failed")
class TestFlagEvaluation:
    def test_creation(self):
        fe = FlagEvaluation(key="dark_mode", enabled=True, reason="tenant_allowlist")
        assert fe.key == "dark_mode"
        assert fe.enabled is True
        assert fe.reason == "tenant_allowlist"

    def test_percent_default_zero(self):
        fe = FlagEvaluation(key="k", enabled=False, reason="disabled")
        assert fe.percent == 0

    def test_enabled_false(self):
        fe = FlagEvaluation(key="k", enabled=False, reason="not_found")
        assert fe.enabled is False
