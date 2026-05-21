"""Shared State Schema — LangGraph state graph'ında 9 ajanın ortak okuduğu/yazdığı TypedDict."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """Tüm ajanlar arasında paylaşılan state (total=False → tüm alanlar optional)."""

    # ── Tanımlayıcılar ──────────────────────────────────────────────────
    project_id: str
    user_id: str
    tenant_id: str
    run_id: str
    input_source: str
    input_payload: dict[str, Any]
    created_at: datetime

    # ── Ajan çıktıları (dict olarak saklanır — her biri kendi schema'sına map) ─
    intent_graph: dict[str, Any]
    app_map: dict[str, Any]
    locators: list[dict[str, Any]]
    scenarios: list[dict[str, Any]]
    generated_code: dict[str, Any]
    run_result: dict[str, Any]
    healing_result: dict[str, Any]
    review: dict[str, Any]
    report: dict[str, Any]

    # ── İteratif kontrol ────────────────────────────────────────────────
    healing_iteration: int
    max_iterations: int

    # ── Observability ───────────────────────────────────────────────────
    errors: list[dict[str, Any]]
    agent_traces: list[dict[str, Any]]

    # ── Maliyet ─────────────────────────────────────────────────────────
    tokens_used: int
    cost_usd: float
    llm_calls_count: int

    # ── Durum ───────────────────────────────────────────────────────────
    status: Literal["running", "completed", "failed", "cancelled"]
    completed_at: Optional[datetime]


def create_initial_state(
    *,
    project_id: str,
    user_id: str,
    tenant_id: str,
    run_id: str,
    input_source: str,
    input_payload: dict[str, Any],
) -> AgentState:
    return AgentState(  # type: ignore[typeddict-item]
        project_id=project_id,
        user_id=user_id,
        tenant_id=tenant_id,
        run_id=run_id,
        input_source=input_source,
        input_payload=input_payload,
        created_at=datetime.utcnow(),
        errors=[],
        agent_traces=[],
        tokens_used=0,
        cost_usd=0.0,
        llm_calls_count=0,
        healing_iteration=0,
        max_iterations=3,
        status="running",
        completed_at=None,
    )
