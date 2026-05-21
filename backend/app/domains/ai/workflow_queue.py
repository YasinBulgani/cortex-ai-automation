"""Queue adapter for canonical AI workflows."""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import BackgroundTasks
from redis import Redis
from rq import Queue, Retry

from app.config import settings
from app.domains.agents.v2.run_store import get_run_store
from app.domains.agents.v2.router import _execute_pipeline
from app.domains.agents.v2.state import AgentState
from app.domains.ai.workflow_tasks import record_enqueue_dead_letter, run_ai_workflow

logger = logging.getLogger(__name__)


def enqueue_ai_workflow(
    *,
    run_id: str,
    state: AgentState,
    background: BackgroundTasks,
) -> dict[str, Any]:
    """Enqueue a workflow to RQ, falling back to FastAPI background in auto mode."""
    backend = (settings.agents_v2_queue_backend or "auto").strip().lower()
    env = (os.environ.get("ENV") or os.environ.get("APP_ENV") or "").strip().lower()
    production_like_env = env in {"production", "prod", "staging"}
    if backend == "auto" and (settings.is_production_like or production_like_env):
        backend = "rq"
    if backend in {"auto", "rq"}:
        try:
            redis = Redis.from_url(settings.redis_url)
            redis.ping()
            queue = Queue(settings.ai_rq_queue_name, connection=redis)
            job = queue.enqueue(
                run_ai_workflow,
                run_id,
                job_id=f"ai-workflow-{run_id}",
                retry=Retry(max=3, interval=[15, 60, 300]),
                failure_ttl=7 * 24 * 60 * 60,
                result_ttl=24 * 60 * 60,
                ttl=60 * 60,
            )
            _set_queue_depth(settings.ai_rq_queue_name, queue.count)
            get_run_store().publish(
                run_id,
                {
                    "event_type": "queue_enqueued",
                    "run_id": run_id,
                    "workflow_id": run_id,
                    "data": {
                        "backend": "rq",
                        "queue_name": settings.ai_rq_queue_name,
                        "rq_job_id": job.id,
                    },
                },
            )
            return {"backend": "rq", "queue_name": settings.ai_rq_queue_name, "job_id": job.id}
        except Exception as exc:
            record_enqueue_dead_letter(
                run_id=run_id,
                reason="enqueue_failed",
                payload={"backend": backend, "queue_name": settings.ai_rq_queue_name},
                error=exc,
            )
            if backend == "rq":
                raise
            logger.warning("AI workflow queue unavailable; falling back to background task: %s", exc)

    background.add_task(_execute_pipeline, run_id, state)
    get_run_store().publish(
        run_id,
        {
            "event_type": "queue_enqueued",
            "run_id": run_id,
            "workflow_id": run_id,
            "data": {"backend": "background", "queue_name": None, "rq_job_id": None},
        },
    )
    return {"backend": "background", "queue_name": None, "job_id": None}


def _set_queue_depth(queue_name: str, depth: int) -> None:
    try:
        from app.domains.ai.metrics import set_workflow_queue_depth

        set_workflow_queue_depth(queue_name=queue_name, depth=depth)
    except Exception as exc:
        logger.debug("AI workflow queue depth metric skipped: %s", exc)
