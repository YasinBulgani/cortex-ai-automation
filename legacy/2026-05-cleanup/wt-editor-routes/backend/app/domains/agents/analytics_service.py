"""Analytics and observability helpers for agent endpoints."""

from __future__ import annotations

from fastapi import HTTPException

from app.domains.agents.banking_team.heal_schemas import (
    HealHistoryEntry,
    HealHistoryResponse,
    HealStatsResponse,
)
from app.domains.agents.banking_team.locator_schemas import TrendAnalysisResponse


def _require_project_id(project_id: str) -> str:
    project_id = project_id.strip()
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    return project_id


def _load_heal_chunks(project_id: str, *, query: str, top_k: int):
    from app.domains.ai.knowledge_store import KnowledgeStore

    store = KnowledgeStore(project_id=project_id)
    chunks = store.retrieve(
        query,
        top_k=top_k,
        sources=["error_pattern"],
        project_id=project_id,
    )
    return [chunk for chunk in chunks if (chunk.metadata or {}).get("type") == "selector_heal"]


def get_heal_history_data(project_id: str, limit: int = 20) -> HealHistoryResponse:
    """Return recent heal history from the KnowledgeStore."""
    project_id = _require_project_id(project_id)
    entries: list[HealHistoryEntry] = []

    try:
        heal_chunks = _load_heal_chunks(
            project_id,
            query="Selector Heal tamir",
            top_k=limit,
        )
        for chunk in heal_chunks:
            meta = chunk.metadata or {}
            entries.append(
                HealHistoryEntry(
                    id=str(getattr(chunk, "id", "")),
                    timestamp=str(getattr(chunk, "created_at", "")),
                    broken_selector=meta.get("broken", ""),
                    healed_selector=meta.get("healed", ""),
                    strategy=meta.get("strategy", ""),
                    tier=meta.get("tier", ""),
                    confidence=meta.get("confidence", 0.0),
                    verified=meta.get("verified", False),
                    file=meta.get("file", ""),
                    test_name=meta.get("test_name", ""),
                )
            )
    except Exception:
        pass

    return HealHistoryResponse(count=len(entries), entries=entries)


def get_heal_stats_data(project_id: str) -> HealStatsResponse:
    """Return aggregate heal statistics from the KnowledgeStore."""
    project_id = _require_project_id(project_id)
    stats = HealStatsResponse()

    try:
        heal_chunks = _load_heal_chunks(
            project_id,
            query="Selector Heal tamir selector",
            top_k=200,
        )
        total = len(heal_chunks)
        if total == 0:
            return stats

        by_strategy: dict[str, int] = {}
        by_tier: dict[str, int] = {}
        confidences: list[float] = []
        verified_count = 0
        last_ts = ""

        for chunk in heal_chunks:
            meta = chunk.metadata or {}

            strategy = meta.get("strategy", "unknown")
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1

            tier = meta.get("tier", "unknown")
            by_tier[tier] = by_tier.get(tier, 0) + 1

            conf = meta.get("confidence", 0.0)
            if conf:
                confidences.append(conf)

            if meta.get("verified"):
                verified_count += 1

            ts = str(getattr(chunk, "created_at", ""))
            if ts > last_ts:
                last_ts = ts

        stats.total_heals = total
        stats.success_rate = 1.0
        stats.verified_rate = round(verified_count / total, 3) if total else 0.0
        stats.by_strategy = by_strategy
        stats.by_tier = by_tier
        stats.avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
        stats.last_heal_at = last_ts or None
    except Exception:
        pass

    return stats


def get_locator_trend_data(project_id: str) -> TrendAnalysisResponse:
    """Return locator heal trend analysis from the KnowledgeStore."""
    project_id = _require_project_id(project_id)

    try:
        heal_chunks = _load_heal_chunks(
            project_id,
            query="Selector Heal tamir selector locator",
            top_k=200,
        )
        total = len(heal_chunks)
        if total == 0:
            return TrendAnalysisResponse(total_heals=0)

        by_strategy: dict[str, int] = {}
        by_tier: dict[str, int] = {}
        selector_counts: dict[str, int] = {}
        page_counts: dict[str, int] = {}
        confidences: list[float] = []

        for chunk in heal_chunks:
            meta = chunk.metadata or {}

            strategy = meta.get("strategy", "unknown")
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1

            tier = meta.get("tier", "unknown")
            by_tier[tier] = by_tier.get(tier, 0) + 1

            broken = meta.get("broken", "")
            if broken:
                selector_counts[broken] = selector_counts.get(broken, 0) + 1

            page = meta.get("page", meta.get("file", ""))
            if page:
                page_counts[page] = page_counts.get(page, 0) + 1

            conf = meta.get("confidence", 0.0)
            if conf:
                confidences.append(conf)

        most_broken_selectors = sorted(
            [{"selector": selector, "count": count} for selector, count in selector_counts.items()],
            key=lambda item: item["count"],
            reverse=True,
        )[:10]
        most_broken_pages = sorted(
            [{"page": page, "count": count} for page, count in page_counts.items()],
            key=lambda item: item["count"],
            reverse=True,
        )[:10]
        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        trend = "stable"
        if len(confidences) >= 10:
            mid = len(confidences) // 2
            first_half_avg = sum(confidences[:mid]) / mid
            second_half_avg = sum(confidences[mid:]) / (len(confidences) - mid)
            if second_half_avg > first_half_avg + 0.05:
                trend = "improving"
            elif second_half_avg < first_half_avg - 0.05:
                trend = "degrading"

        return TrendAnalysisResponse(
            total_heals=total,
            by_strategy=by_strategy,
            by_tier=by_tier,
            most_broken_selectors=most_broken_selectors,
            most_broken_pages=most_broken_pages,
            avg_confidence=avg_confidence,
            trend=trend,
        )
    except Exception:
        return TrendAnalysisResponse(total_heals=0)


def get_llm_traces_data(
    *,
    project_id: str,
    user_id: str | None = None,
    run_id: str | None = None,
    agent_name: str | None = None,
    limit: int = 50,
) -> dict:
    """Return recent LLM trace rows."""
    from app.domains.ai.llm_trace import get_recent_traces

    traces = get_recent_traces(
        project_id=project_id,
        user_id=user_id,
        run_id=run_id,
        agent_name=agent_name,
        limit=limit,
    )
    return {"count": len(traces), "traces": traces}


def get_llm_trace_stats_data(*, project_id: str, user_id: str | None = None) -> dict:
    """Return aggregate LLM trace stats."""
    from app.domains.ai.llm_trace import get_trace_stats_scoped

    return get_trace_stats_scoped(project_id=project_id, user_id=user_id)
