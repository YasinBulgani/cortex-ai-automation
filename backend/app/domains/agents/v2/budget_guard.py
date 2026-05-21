"""Agent run için budget & cancellation koruması — Dalga 3.

Kullanım (agent node içinde):

    from app.domains.agents.v2.budget_guard import (
        check_budget,
        deduct_usage,
        raise_if_cancelled,
        BudgetExceededError,
    )

    async def my_agent_node(state):
        raise_if_cancelled(state)
        check_budget(state, estimated_tokens=3000, estimated_cost_usd=0.02)
        # ... LLM çağrısı
        deduct_usage(state, tokens=actual_tokens, cost_usd=actual_cost)
        return state

Tasarım:
    * State-level budget tracking: ``state["token_budget_remaining"]`` ve
      ``state["cost_budget_remaining"]`` agent'lar arası propagate edilir.
    * Soft limit → warning; hard limit → ``BudgetExceededError``. Caller
      (orchestrator) bunu yakalayıp state["status"]="failed" set etmeli.
    * Cancellation: ``state["cancelled"] = True`` veya external registry
      üzerinden. ``raise_if_cancelled`` ``asyncio.CancelledError`` fırlatır.
    * Zero-copy: state'i mutate etmez, yeni alanları okuma/yazma pattern'i.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from .config import get_config
from .state import AgentState

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    """Run bütçesi aşıldı — orchestrator yakalasın."""

    def __init__(
        self,
        *,
        kind: str,      # "tokens" | "cost" | "duration"
        used: float,
        limit: float,
        agent_name: Optional[str] = None,
    ):
        self.kind = kind
        self.used = used
        self.limit = limit
        self.agent_name = agent_name
        super().__init__(
            f"Budget exceeded ({kind}): {used:.2f} >= {limit:.2f}"
            + (f" [agent={agent_name}]" if agent_name else "")
        )


# ─────────────────────────────────────────────────────────────────────────
# Initialization — orchestrator run_pipeline'ın başında çağırır
# ─────────────────────────────────────────────────────────────────────────
def init_budget(state: AgentState) -> AgentState:
    """Run başında budget alanlarını initialize eder."""
    cfg = get_config()
    # mevcut tokens_used/cost_usd/llm_calls_count zaten var; remaining'i
    # sadece yoksa kur.
    state.setdefault("tokens_used", 0)  # type: ignore[typeddict-item]
    state.setdefault("cost_usd", 0.0)  # type: ignore[typeddict-item]
    state.setdefault("llm_calls_count", 0)  # type: ignore[typeddict-item]

    # Budget remaining alanları (TypedDict total=False → dinamik key güvenli)
    if "token_budget_remaining" not in state:  # type: ignore[operator]
        state["token_budget_remaining"] = cfg.max_tokens_per_run  # type: ignore[typeddict-unknown-key]
    if "cost_budget_remaining" not in state:  # type: ignore[operator]
        state["cost_budget_remaining"] = cfg.max_cost_usd_per_run  # type: ignore[typeddict-unknown-key]
    return state


# ─────────────────────────────────────────────────────────────────────────
# Pre-flight check
# ─────────────────────────────────────────────────────────────────────────
def check_budget(
    state: AgentState,
    *,
    estimated_tokens: int = 0,
    estimated_cost_usd: float = 0.0,
    agent_name: Optional[str] = None,
    soft_warn_ratio: float = 0.8,
) -> None:
    """Çağrı öncesi bütçe kontrolü. Yetersizse ``BudgetExceededError``.

    Soft-limit (>= %80 tüketildi) → logger.warning. Hard-limit → exception.
    """
    cfg = get_config()
    tokens_remaining = int(
        state.get("token_budget_remaining", cfg.max_tokens_per_run) or 0  # type: ignore[call-arg]
    )
    cost_remaining = float(
        state.get("cost_budget_remaining", cfg.max_cost_usd_per_run) or 0.0  # type: ignore[call-arg]
    )

    if tokens_remaining - max(0, estimated_tokens) < 0:
        raise BudgetExceededError(
            kind="tokens",
            used=cfg.max_tokens_per_run - tokens_remaining + max(0, estimated_tokens),
            limit=float(cfg.max_tokens_per_run),
            agent_name=agent_name,
        )

    if cost_remaining - max(0.0, estimated_cost_usd) < 0.0:
        raise BudgetExceededError(
            kind="cost",
            used=cfg.max_cost_usd_per_run - cost_remaining + max(0.0, estimated_cost_usd),
            limit=cfg.max_cost_usd_per_run,
            agent_name=agent_name,
        )

    # Soft warning
    total_tok_budget = float(cfg.max_tokens_per_run) or 1.0
    total_cost_budget = float(cfg.max_cost_usd_per_run) or 1.0
    tok_consumed_ratio = 1.0 - (tokens_remaining / total_tok_budget)
    cost_consumed_ratio = 1.0 - (cost_remaining / total_cost_budget)

    if tok_consumed_ratio >= soft_warn_ratio or cost_consumed_ratio >= soft_warn_ratio:
        logger.warning(
            "Budget soft-limit agent=%s tokens=%.1f%% cost=%.1f%%",
            agent_name or "?",
            tok_consumed_ratio * 100,
            cost_consumed_ratio * 100,
        )


# ─────────────────────────────────────────────────────────────────────────
# Post-call deduction
# ─────────────────────────────────────────────────────────────────────────
def deduct_usage(
    state: AgentState,
    *,
    tokens: int,
    cost_usd: float,
    agent_name: Optional[str] = None,
) -> None:
    """LLM çağrısı sonrası kullanımı state'e işle."""
    tokens = max(0, int(tokens or 0))
    cost_usd = max(0.0, float(cost_usd or 0.0))

    state["tokens_used"] = int(state.get("tokens_used", 0) or 0) + tokens  # type: ignore[typeddict-item]
    state["cost_usd"] = round(  # type: ignore[typeddict-item]
        float(state.get("cost_usd", 0.0) or 0.0) + cost_usd, 6
    )
    state["llm_calls_count"] = int(state.get("llm_calls_count", 0) or 0) + 1  # type: ignore[typeddict-item]

    tok_rem = int(
        state.get("token_budget_remaining", 0) or 0  # type: ignore[call-arg]
    ) - tokens
    cost_rem = float(
        state.get("cost_budget_remaining", 0.0) or 0.0  # type: ignore[call-arg]
    ) - cost_usd

    state["token_budget_remaining"] = max(0, tok_rem)  # type: ignore[typeddict-unknown-key]
    state["cost_budget_remaining"] = max(0.0, round(cost_rem, 6))  # type: ignore[typeddict-unknown-key]

    # Trace kaydı
    traces = list(state.get("agent_traces") or [])
    traces.append({
        "agent": agent_name or "unknown",
        "tokens": tokens,
        "cost_usd": cost_usd,
        "tokens_remaining": state["token_budget_remaining"],  # type: ignore[typeddict-item]
        "cost_remaining": state["cost_budget_remaining"],  # type: ignore[typeddict-item]
    })
    state["agent_traces"] = traces  # type: ignore[typeddict-item]


# ─────────────────────────────────────────────────────────────────────────
# Cancellation
# ─────────────────────────────────────────────────────────────────────────
_cancel_registry: Dict[str, bool] = {}


def request_cancel(run_id: str) -> None:
    """External process (UI, admin API) run'ı iptal eder."""
    _cancel_registry[run_id] = True


def is_cancelled(run_id: str) -> bool:
    return _cancel_registry.get(run_id, False)


def clear_cancel(run_id: str) -> None:
    _cancel_registry.pop(run_id, None)


def raise_if_cancelled(state: AgentState, *, agent_name: Optional[str] = None) -> None:
    """Agent node başında çağır — iptal edilmişse CancelledError."""
    # Flag state üzerinde veya global registry'de olabilir
    if bool(state.get("cancelled", False)):  # type: ignore[call-arg]
        raise asyncio.CancelledError(
            f"Run cancelled via state [agent={agent_name or '?'}]"
        )
    run_id = str(state.get("run_id") or "")
    if run_id and is_cancelled(run_id):
        state["status"] = "cancelled"  # type: ignore[typeddict-item]
        state["cancelled"] = True  # type: ignore[typeddict-unknown-key]
        raise asyncio.CancelledError(
            f"Run cancelled via registry [run_id={run_id}]"
        )


# ─────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────
def budget_snapshot(state: AgentState) -> Dict[str, Any]:
    """Dashboard / trace için okunaklı bütçe özeti."""
    cfg = get_config()
    tok_rem = int(state.get("token_budget_remaining", cfg.max_tokens_per_run) or 0)  # type: ignore[call-arg]
    cost_rem = float(state.get("cost_budget_remaining", cfg.max_cost_usd_per_run) or 0.0)  # type: ignore[call-arg]
    return {
        "tokens_used": int(state.get("tokens_used", 0) or 0),
        "tokens_limit": cfg.max_tokens_per_run,
        "tokens_remaining": tok_rem,
        "tokens_consumed_pct": round(
            (1 - tok_rem / cfg.max_tokens_per_run) * 100, 2
        ),
        "cost_used_usd": float(state.get("cost_usd", 0.0) or 0.0),
        "cost_limit_usd": cfg.max_cost_usd_per_run,
        "cost_remaining_usd": cost_rem,
        "cost_consumed_pct": round(
            (1 - cost_rem / cfg.max_cost_usd_per_run) * 100, 2
        ),
        "llm_calls": int(state.get("llm_calls_count", 0) or 0),
    }
