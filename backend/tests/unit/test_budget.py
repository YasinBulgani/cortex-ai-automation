"""Budget karar mantığı — feature flag + politika + usage kombinasyonu.

DB'den bağımsız: ``check_budget`` içindeki ``get_policy`` ve
``get_tenant_today_cost`` monkeypatch ile mock'lanır. Unit testler bu
fonksiyonun **karar akışını** doğrular; DB CRUD için ayrı integration test
(gerçek postgres) ileride eklenecek.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

import pytest

from app.domains.ai import budget as budget_mod
from app.domains.ai.budget import BudgetPolicyOut, BudgetStatus, check_budget


def _fake_policy(
    tenant_id: str = "t1",
    daily_cap_usd: float = 10.0,
    hard_cap: bool = False,
    notify_at_pct: int = 80,
) -> BudgetPolicyOut:
    now = datetime.now(timezone.utc)
    return BudgetPolicyOut(
        tenant_id=tenant_id,
        daily_cap_usd=daily_cap_usd,
        hard_cap=hard_cap,
        notify_at_pct=notify_at_pct,
        notes=None,
        created_at=now,
        updated_at=now,
        updated_by=None,
    )


@pytest.fixture(autouse=True)
def _enable_budget_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    # Default olarak budget enforcement açık — her test "disabled" branch'ini
    # istediğinde bu fixture'ı override eder.
    monkeypatch.setattr(budget_mod, "_budget_enforcement_enabled", lambda _tid: True)


def _mock_usage(monkeypatch: pytest.MonkeyPatch, *, today_cost: float) -> None:
    from app.domains.ai import usage_service

    monkeypatch.setattr(usage_service, "get_tenant_today_cost", lambda _t: today_cost)


def _mock_policy(
    monkeypatch: pytest.MonkeyPatch,
    policy: Optional[BudgetPolicyOut],
) -> None:
    monkeypatch.setattr(budget_mod, "get_policy", lambda _t: policy)


# ── Karar akışı ─────────────────────────────────────────────────────────────


def test_no_tenant_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    out = check_budget("")
    assert out.allowed is True
    assert out.reason == "no_policy"


def test_enforcement_disabled_always_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(budget_mod, "_budget_enforcement_enabled", lambda _t: False)
    # Politika/kullanım bile sorulmamalı
    called = {"policy": False}

    def _should_not_call(_t):
        called["policy"] = True
        return _fake_policy()

    monkeypatch.setattr(budget_mod, "get_policy", _should_not_call)

    out = check_budget("t1")
    assert out.allowed is True
    assert out.reason == "disabled"
    assert called["policy"] is False


def test_no_policy_returns_no_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_policy(monkeypatch, None)
    out = check_budget("t1")
    assert out.allowed is True
    assert out.reason == "no_policy"


def test_zero_cap_treated_as_no_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_policy(monkeypatch, _fake_policy(daily_cap_usd=0.0))
    out = check_budget("t1")
    assert out.allowed is True
    assert out.reason == "no_policy"


def test_under_notify_threshold_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    # cap=10, notify=80% → threshold=8. Kullanım 3 < 8.
    _mock_policy(monkeypatch, _fake_policy(daily_cap_usd=10.0, notify_at_pct=80))
    _mock_usage(monkeypatch, today_cost=3.0)
    out = check_budget("t1")
    assert out.allowed is True
    assert out.reason == "ok"
    assert out.today_usd == 3.0
    assert out.pct_used() == 30.0


def test_approaching_soft_alarm(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_policy(monkeypatch, _fake_policy(daily_cap_usd=10.0, notify_at_pct=80))
    _mock_usage(monkeypatch, today_cost=8.5)
    out = check_budget("t1")
    assert out.allowed is True
    assert out.reason == "approaching"
    assert out.pct_used() == 85.0


def test_over_cap_soft_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_policy(monkeypatch, _fake_policy(daily_cap_usd=10.0, hard_cap=False))
    _mock_usage(monkeypatch, today_cost=11.0)
    out = check_budget("t1")
    assert out.allowed is True
    assert out.reason == "over_cap"


def test_over_cap_hard_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_policy(monkeypatch, _fake_policy(daily_cap_usd=10.0, hard_cap=True))
    _mock_usage(monkeypatch, today_cost=12.0)
    out = check_budget("t1")
    assert out.allowed is False
    assert out.reason == "hard_cap"


def test_projected_cost_triggers_hard_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Bugün 9 USD, additional 2 USD → projected 11 > 10 cap, hard
    _mock_policy(monkeypatch, _fake_policy(daily_cap_usd=10.0, hard_cap=True))
    _mock_usage(monkeypatch, today_cost=9.0)
    out = check_budget("t1", additional_cost_usd=2.0)
    assert out.allowed is False
    assert out.reason == "hard_cap"


def test_projected_cost_stays_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_policy(monkeypatch, _fake_policy(daily_cap_usd=10.0, hard_cap=True))
    _mock_usage(monkeypatch, today_cost=3.0)
    out = check_budget("t1", additional_cost_usd=1.0)
    # projected 4 < 8 (80% notify) → ok
    assert out.allowed is True
    assert out.reason == "ok"


def test_pct_used_safe_on_zero_cap() -> None:
    s = BudgetStatus(
        allowed=True,
        reason="no_policy",
        today_usd=5.0,
        daily_cap_usd=0.0,
        notify_at_pct=0,
        hard_cap=False,
    )
    assert s.pct_used() == 0.0
