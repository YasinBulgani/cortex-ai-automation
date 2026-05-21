"""Budget guard + cancellation unit testleri (Dalga 3)."""
from __future__ import annotations

import asyncio

import pytest

from app.domains.agents.v2.budget_guard import (
    BudgetExceededError,
    budget_snapshot,
    check_budget,
    clear_cancel,
    deduct_usage,
    init_budget,
    is_cancelled,
    raise_if_cancelled,
    request_cancel,
)
from app.domains.agents.v2.config import get_config
from app.domains.agents.v2.state import AgentState, create_initial_state


def _state(**overrides):
    st = create_initial_state(
        project_id="p", user_id="u", tenant_id="t", run_id="r1",
        input_source="url", input_payload={"url": "https://x"},
    )
    init_budget(st)
    for k, v in overrides.items():
        st[k] = v  # type: ignore[typeddict-item]
    return st


class TestInitBudget:
    def test_sets_remaining_fields(self):
        cfg = get_config()
        st = _state()
        assert st["token_budget_remaining"] == cfg.max_tokens_per_run  # type: ignore
        assert st["cost_budget_remaining"] == cfg.max_cost_usd_per_run  # type: ignore
        assert st["tokens_used"] == 0
        assert st["cost_usd"] == 0.0

    def test_idempotent(self):
        st = _state()
        # Budget already consumed; re-init bozamamalı
        st["token_budget_remaining"] = 50_000  # type: ignore
        init_budget(st)
        assert st["token_budget_remaining"] == 50_000  # type: ignore


class TestCheckBudget:
    def test_fresh_state_passes(self):
        st = _state()
        check_budget(st, estimated_tokens=1000, estimated_cost_usd=0.01)

    def test_token_exhaustion_raises(self):
        st = _state(token_budget_remaining=100)
        with pytest.raises(BudgetExceededError) as exc:
            check_budget(st, estimated_tokens=5000)
        assert exc.value.kind == "tokens"

    def test_cost_exhaustion_raises(self):
        st = _state(cost_budget_remaining=0.01)
        with pytest.raises(BudgetExceededError) as exc:
            check_budget(st, estimated_cost_usd=1.0)
        assert exc.value.kind == "cost"

    def test_agent_name_in_exception(self):
        st = _state(cost_budget_remaining=0.0)
        with pytest.raises(BudgetExceededError) as exc:
            check_budget(st, estimated_cost_usd=0.5, agent_name="coder")
        assert exc.value.agent_name == "coder"

    def test_soft_warn_logged(self, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        cfg = get_config()
        # %90 tüketildi
        st = _state(
            token_budget_remaining=int(cfg.max_tokens_per_run * 0.1),
            cost_budget_remaining=cfg.max_cost_usd_per_run * 0.1,
        )
        check_budget(st, estimated_tokens=100, agent_name="analyst")
        assert any("soft-limit" in r.message for r in caplog.records)


class TestDeductUsage:
    def test_deducts_tokens_and_cost(self):
        st = _state()
        cfg = get_config()
        deduct_usage(st, tokens=500, cost_usd=0.05, agent_name="analyst")
        assert st["tokens_used"] == 500
        assert st["cost_usd"] == pytest.approx(0.05)
        assert st["llm_calls_count"] == 1
        assert st["token_budget_remaining"] == cfg.max_tokens_per_run - 500  # type: ignore
        assert st["cost_budget_remaining"] == pytest.approx(  # type: ignore
            cfg.max_cost_usd_per_run - 0.05
        )

    def test_multiple_deductions_accumulate(self):
        st = _state()
        deduct_usage(st, tokens=100, cost_usd=0.01)
        deduct_usage(st, tokens=200, cost_usd=0.02)
        assert st["tokens_used"] == 300
        assert st["cost_usd"] == pytest.approx(0.03)
        assert st["llm_calls_count"] == 2

    def test_never_negative_remaining(self):
        st = _state(token_budget_remaining=10, cost_budget_remaining=0.01)
        deduct_usage(st, tokens=1_000_000, cost_usd=100.0)
        assert st["token_budget_remaining"] == 0  # type: ignore
        assert st["cost_budget_remaining"] == 0.0  # type: ignore

    def test_trace_appended(self):
        st = _state()
        deduct_usage(st, tokens=500, cost_usd=0.05, agent_name="coder")
        assert len(st["agent_traces"]) == 1
        assert st["agent_traces"][0]["agent"] == "coder"
        assert st["agent_traces"][0]["tokens"] == 500


class TestCancellation:
    def test_request_and_check(self):
        request_cancel("r-xyz")
        assert is_cancelled("r-xyz") is True
        clear_cancel("r-xyz")
        assert is_cancelled("r-xyz") is False

    def test_raise_if_cancelled_via_state_flag(self):
        st = _state()
        st["cancelled"] = True  # type: ignore
        with pytest.raises(asyncio.CancelledError):
            raise_if_cancelled(st, agent_name="runner")

    def test_raise_if_cancelled_via_registry(self):
        st = _state()
        request_cancel("r1")
        try:
            with pytest.raises(asyncio.CancelledError):
                raise_if_cancelled(st, agent_name="runner")
        finally:
            clear_cancel("r1")
        assert st["status"] == "cancelled"
        assert st.get("cancelled") is True  # type: ignore

    def test_not_cancelled_passes(self):
        st = _state()
        raise_if_cancelled(st)  # no raise


class TestSnapshot:
    def test_snapshot_shape(self):
        st = _state()
        deduct_usage(st, tokens=1000, cost_usd=0.10)
        snap = budget_snapshot(st)
        assert snap["tokens_used"] == 1000
        assert snap["cost_used_usd"] == pytest.approx(0.10)
        assert "tokens_consumed_pct" in snap
        assert 0 <= snap["tokens_consumed_pct"] < 100
