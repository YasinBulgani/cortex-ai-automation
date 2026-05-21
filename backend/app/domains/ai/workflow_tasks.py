"""RQ tasks for canonical AI workflows."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from rq import get_current_job

from app.config import settings
from app.domains.agents.v2.run_store import get_run_store
from app.domains.agents.v2.router import _execute_pipeline

logger = logging.getLogger(__name__)


def run_ai_workflow(run_id: str) -> None:
    """Execute a persisted AI workflow from an RQ worker."""
    job = get_current_job()
    retry_count = int((job.meta or {}).get("retry_count", 0)) if job else 0
    try:
        asyncio.run(_run(run_id))
    except Exception as exc:
        get_run_store().record_dead_letter(
            run_id=run_id,
            queue_name=settings.ai_rq_queue_name,
            reason="worker_exception",
            payload={"job_id": job.id if job else None},
            retry_count=retry_count,
            last_error=str(exc),
        )
        raise


async def _run(run_id: str) -> None:
    store = get_run_store()
    rec = store.get(run_id)
    if rec is None:
        store.record_dead_letter(
            run_id=run_id,
            queue_name=settings.ai_rq_queue_name,
            reason="run_not_found",
            payload={"run_id": run_id},
        )
        return
    if rec.status == "cancelled":
        logger.info("AI workflow %s is cancelled; worker skips execution", run_id)
        return
    await _execute_pipeline(run_id, rec.state)


def record_enqueue_dead_letter(
    *,
    run_id: str | None,
    reason: str,
    payload: dict[str, Any],
    error: Exception,
) -> None:
    get_run_store().record_dead_letter(
        run_id=run_id,
        queue_name=settings.ai_rq_queue_name,
        reason=reason,
        payload=payload,
        last_error=str(error),
    )
