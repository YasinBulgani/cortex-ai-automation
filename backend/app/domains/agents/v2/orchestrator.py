"""LangGraph Orchestrator — 9 ajanlı state machine."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Literal

from .config import get_config
from .state import AgentState

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END  # type: ignore
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


def after_runner(state: AgentState) -> Literal["healer", "reviewer"]:
    result = state.get("run_result")
    if not result:
        return "reviewer"
    if result.get("failed_count", 0) > 0:
        return "healer"
    return "reviewer"


def after_healer(state: AgentState) -> Literal["runner", "reviewer"]:
    cfg = get_config()
    iteration = state.get("healing_iteration", 0)
    if iteration >= cfg.max_healing_iterations:
        return "reviewer"
    healing = state.get("healing_result")
    if healing and healing.get("successful_fixes", 0) > 0:
        state["healing_iteration"] = iteration + 1  # type: ignore[typeddict-unknown-key]
        return "runner"
    return "reviewer"


def after_analyst(state: AgentState) -> Literal["explorer", "scenario"]:
    src = state.get("input_source")
    payload = state.get("input_payload", {})
    if src == "url" or "url" in payload:
        return "explorer"
    return "scenario"


def build_graph():
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("pip install langgraph langchain-core")

    from .agents import (
        analyst_node, explorer_node, locator_node, scenario_node,
        coder_node, runner_node, healer_node, reviewer_node, reporter_node,
    )

    graph = StateGraph(AgentState)
    graph.add_node("analyst", analyst_node)
    graph.add_node("explorer", explorer_node)
    graph.add_node("locator", locator_node)
    graph.add_node("scenario", scenario_node)
    graph.add_node("coder", coder_node)
    graph.add_node("runner", runner_node)
    graph.add_node("healer", healer_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("reporter", reporter_node)

    graph.set_entry_point("analyst")
    graph.add_conditional_edges("analyst", after_analyst,
                                 {"explorer": "explorer", "scenario": "scenario"})
    graph.add_edge("explorer", "locator")
    graph.add_edge("locator", "scenario")
    graph.add_edge("scenario", "coder")
    graph.add_edge("coder", "runner")
    graph.add_conditional_edges("runner", after_runner,
                                 {"healer": "healer", "reviewer": "reviewer"})
    graph.add_conditional_edges("healer", after_healer,
                                 {"runner": "runner", "reviewer": "reviewer"})
    graph.add_edge("reviewer", "reporter")
    graph.add_edge("reporter", END)
    return graph.compile()


async def run_pipeline(initial_state: AgentState) -> AgentState:
    cfg = get_config()

    # Dalga 3 · budget init — tokens & cost remaining alanları kurulur
    from .budget_guard import BudgetExceededError, clear_cancel, init_budget
    init_budget(initial_state)

    run_id = str(initial_state.get("run_id") or "")

    try:
        workflow = build_graph()
        final_state: AgentState = await asyncio.wait_for(
            workflow.ainvoke(initial_state),
            timeout=cfg.max_duration_seconds,
        )
        # Cancel flag'i içeride set edildiyse "cancelled" bırak
        if bool(final_state.get("cancelled", False)):
            final_state["status"] = "cancelled"
        else:
            final_state["status"] = "completed"
    except ImportError:
        # LangGraph yok — manual fallback
        from .router import _execute_manual  # type: ignore
        final_state = await _execute_manual(run_id, initial_state)
    except asyncio.CancelledError:
        initial_state["status"] = "cancelled"
        initial_state.setdefault("errors", []).append({
            "agent": "orchestrator",
            "error": "Run cancelled",
            "timestamp": datetime.utcnow().isoformat(),
        })
        final_state = initial_state
    except BudgetExceededError as exc:
        logger.warning("Pipeline budget exceeded: %s", exc)
        initial_state["status"] = "failed"
        initial_state.setdefault("errors", []).append({
            "agent": exc.agent_name or "budget_guard",
            "error": str(exc),
            "kind": exc.kind,
            "used": exc.used,
            "limit": exc.limit,
            "timestamp": datetime.utcnow().isoformat(),
        })
        final_state = initial_state
    except asyncio.TimeoutError:
        initial_state["status"] = "failed"
        initial_state.setdefault("errors", []).append({
            "agent": "orchestrator",
            "error": f"Timeout after {cfg.max_duration_seconds}s",
            "timestamp": datetime.utcnow().isoformat(),
        })
        final_state = initial_state
    except Exception as e:
        logger.exception("Pipeline error: %s", e)
        initial_state["status"] = "failed"
        initial_state.setdefault("errors", []).append({
            "agent": "orchestrator",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        final_state = initial_state
    finally:
        if run_id:
            clear_cancel(run_id)

    final_state["completed_at"] = datetime.utcnow()
    return final_state
