"""Agents — thin service facade for agent orchestration operations.

HTTP-agnostic: raises ValueError/KeyError instead of HTTPException.
Wraps orchestration_service and analytics_service internals.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.domains.agents.orchestration_service import (
    get_all_agents_status,
    start_all_agents_run,
    get_banking_pipeline_status,
    get_full_pipeline_status,
)
from app.domains.agents.analytics_service import (
    get_heal_stats_data,
    get_llm_trace_stats_data,
)

logger = logging.getLogger(__name__)


def start_run(
    background_tasks: Any,
    project_id: Optional[str] = None,
    pipeline_type: str = "all",
) -> Dict[str, Any]:
    """Start an agent pipeline run.

    Args:
        background_tasks: FastAPI BackgroundTasks or compatible interface.
        project_id: Optional TSPM project scope.
        pipeline_type: One of 'all', 'banking', 'full'.

    Returns:
        Dict with run_id and message.

    Raises:
        ValueError: Unknown pipeline_type.
    """
    if pipeline_type == "all":
        return start_all_agents_run(background_tasks, project_id=project_id)
    raise ValueError(
        f"Bilinmeyen pipeline türü: '{pipeline_type}'. Geçerli: 'all'."
    )


def get_status(run_id: Optional[str] = None) -> Dict[str, Any]:
    """Return current pipeline status snapshot.

    Args:
        run_id: Optional run identifier — used to filter if multiple runs are
                tracked in the future. Currently the orchestrator is single-run.

    Returns:
        Status snapshot dict.
    """
    status = get_all_agents_status()
    if run_id and status.get("run_id") and status["run_id"] != run_id:
        raise KeyError(f"run_id '{run_id}' bulunamadı veya zaten tamamlandı.")
    return status


def get_analytics(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate analytics: heal stats + LLM trace stats.

    Args:
        project_id: Scope analytics to this project (optional).

    Returns:
        Combined analytics dict.
    """
    heal: Dict[str, Any] = {}
    llm: Dict[str, Any] = {}

    if project_id:
        try:
            heal = get_heal_stats_data(project_id)
        except Exception as exc:
            logger.warning("Heal stats alınamadı: %s", exc)
            heal = {"error": str(exc)}

        try:
            llm = get_llm_trace_stats_data(project_id)
        except Exception as exc:
            logger.warning("LLM trace stats alınamadı: %s", exc)
            llm = {"error": str(exc)}

    return {
        "project_id": project_id,
        "heal_stats": heal,
        "llm_trace_stats": llm,
    }
