"""Plan catalog and limit helper unit tests (no DB)."""

from __future__ import annotations

import pytest

from app.domains.billing.plans import (
    DEFAULT_PLAN_CODE,
    PLAN_CATALOG,
    UNLIMITED,
    get_plan,
    is_unlimited,
    list_plans,
    within_limit,
)


def test_plan_catalog_has_expected_codes() -> None:
    assert set(PLAN_CATALOG.keys()) == {"free", "starter", "pro", "enterprise"}


def test_default_plan_is_free() -> None:
    assert DEFAULT_PLAN_CODE == "free"
    assert get_plan(None).code == "free"
    assert get_plan("").code == "free"


def test_unknown_plan_falls_back_to_free() -> None:
    assert get_plan("nonexistent").code == "free"


def test_each_plan_has_limits() -> None:
    for plan in PLAN_CATALOG.values():
        assert plan.limits.project_count != 0
        assert plan.limits.team_size != 0
        assert plan.limits.run_count_month != 0


def test_enterprise_is_unlimited() -> None:
    e = PLAN_CATALOG["enterprise"]
    assert is_unlimited(e.limits.project_count)
    assert is_unlimited(e.limits.team_size)
    assert is_unlimited(e.limits.run_count_month)
    assert e.is_contact_sales is True


def test_free_is_lowest_limits() -> None:
    free = PLAN_CATALOG["free"]
    starter = PLAN_CATALOG["starter"]
    assert free.limits.project_count < starter.limits.project_count
    assert free.limits.team_size < starter.limits.team_size
    assert free.limits.run_count_month < starter.limits.run_count_month


def test_within_limit_unlimited_always_true() -> None:
    assert within_limit(1_000_000_000, UNLIMITED)


@pytest.mark.parametrize(
    "used,limit,expected",
    [
        (0, 10, True),
        (9, 10, True),
        (10, 10, False),
        (11, 10, False),
    ],
)
def test_within_limit_boundary(used: int, limit: int, expected: bool) -> None:
    assert within_limit(used, limit) is expected


def test_list_plans_returns_serializable_dicts() -> None:
    plans = list_plans()
    assert len(plans) == 4
    for p in plans:
        assert {"code", "label", "limits", "features", "monthly_price_usd"}.issubset(p)
        assert isinstance(p["limits"], dict)


def test_plan_to_dict_round_trips() -> None:
    plan = PLAN_CATALOG["pro"]
    d = plan.to_dict()
    assert d["code"] == "pro"
    assert d["limits"]["team_size"] == 25
