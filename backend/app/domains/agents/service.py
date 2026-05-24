"""Public service facade for the agents domain.

Aggregates orchestration, analytics, and pipeline helpers so that callers
outside this domain only need to import from here.
"""
from __future__ import annotations

import logging

from app.domains.agents.analytics_service import (
    get_heal_history_data,
    get_heal_stats_data,
    get_llm_trace_stats_data,
    get_llm_traces_data,
    get_locator_trend_data,
)
from app.domains.agents.orchestration_service import (
    cancel_all_agents_run,
    cancel_banking_team_run,
    cancel_full_pipeline_run,
    get_all_agents_logs,
    get_all_agents_status,
    get_banking_pipeline_logs,
    get_banking_pipeline_report,
    get_banking_pipeline_status,
    get_banking_scheduler_info,
    get_banking_system_health,
    get_full_pipeline_logs,
    get_full_pipeline_report,
    get_full_pipeline_status,
    quick_start_full_pipeline,
    start_all_agents_run,
    start_banking_team_run,
    start_full_pipeline_run,
    trigger_banking_team_now,
)

logger = logging.getLogger(__name__)

__all__ = [
    # orchestration
    "start_all_agents_run",
    "get_all_agents_status",
    "get_all_agents_logs",
    "cancel_all_agents_run",
    "start_banking_team_run",
    "get_banking_pipeline_status",
    "get_banking_pipeline_logs",
    "get_banking_pipeline_report",
    "cancel_banking_team_run",
    "trigger_banking_team_now",
    "get_banking_scheduler_info",
    "get_banking_system_health",
    "start_full_pipeline_run",
    "get_full_pipeline_status",
    "get_full_pipeline_logs",
    "get_full_pipeline_report",
    "cancel_full_pipeline_run",
    "quick_start_full_pipeline",
    # analytics
    "get_heal_history_data",
    "get_heal_stats_data",
    "get_locator_trend_data",
    "get_llm_traces_data",
    "get_llm_trace_stats_data",
    # stubs
    "get_agent_catalog",
]


def get_agent_catalog() -> list[dict]:
    """Return the list of available agent definitions with metadata.

    Raises:
        NotImplementedError: Until the agent registry is implemented.
    """
    raise NotImplementedError(
        "TODO: implement get_agent_catalog — see docs/planning/END_USER_GAPS_PLAN.md"
    )
