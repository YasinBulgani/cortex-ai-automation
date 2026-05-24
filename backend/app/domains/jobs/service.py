"""Jobs — thin service facade for background generation jobs.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
Wraps SQLAlchemy GenerationJob model + RQ queue.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.models import GenerationJob

logger = logging.getLogger(__name__)


def _get_queue():
    """Lazy import to avoid Redis connection at import time."""
    from redis import Redis
    from rq import Queue
    from app.config import settings

    return Queue(settings.rq_queue_name, connection=Redis.from_url(settings.redis_url))


def enqueue(
    db: Session,
    dataset_version_id: str,
    rule_set_id: Optional[str] = None,
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Enqueue a new generation job.

    Args:
        db: SQLAlchemy session.
        dataset_version_id: Target DatasetVersion ID.
        rule_set_id: Optional RuleSet to apply.
        created_by: User ID of the requester.

    Returns:
        Dict representation of the created GenerationJob.

    Raises:
        KeyError: dataset_version_id or rule_set_id not found.
        ValueError: RuleSet belongs to a different dataset.
    """
    from app.infra.models import DatasetVersion, RuleSet
    from app.domains.jobs.tasks import run_generation_job

    ver = db.get(DatasetVersion, dataset_version_id)
    if ver is None:
        raise KeyError(f"DatasetVersion '{dataset_version_id}' bulunamadı.")

    if rule_set_id:
        rs = db.get(RuleSet, rule_set_id)
        if rs is None:
            raise KeyError(f"RuleSet '{rule_set_id}' bulunamadı.")
        if rs.dataset_id != ver.dataset_id:
            raise ValueError("Kural seti bu veri setine ait değil.")

    job = GenerationJob(
        dataset_version_id=dataset_version_id,
        rule_set_id=rule_set_id,
        status="queued",
        created_by=created_by,
    )
    db.add(job)
    db.flush()
    rq_job = _get_queue().enqueue(run_generation_job, job.id)
    job.rq_job_id = rq_job.id
    db.commit()
    db.refresh(job)
    logger.info("Job kuyruğa eklendi: %s (rq=%s)", job.id, rq_job.id)
    return {c.key: getattr(job, c.key) for c in job.__table__.columns}


def get_job(db: Session, job_id: str) -> Dict[str, Any]:
    """Fetch a single job by ID.

    Raises:
        KeyError: Job not found.
    """
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise KeyError(f"Job '{job_id}' bulunamadı.")
    return {c.key: getattr(job, c.key) for c in job.__table__.columns}


def list_jobs(db: Session, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """List jobs ordered by creation time, newest first.

    Args:
        db: SQLAlchemy session.
        status: Optional status filter ('queued', 'running', 'done', 'failed').
        limit: Max rows (capped at 200).
    """
    limit = min(int(limit), 200)
    q = select(GenerationJob).order_by(GenerationJob.created_at.desc()).limit(limit)
    if status:
        q = q.where(GenerationJob.status == status)
    jobs = list(db.scalars(q).all())
    return [{c.key: getattr(j, c.key) for c in j.__table__.columns} for j in jobs]


def cancel_job(db: Session, job_id: str) -> Dict[str, Any]:
    """Mark a queued or running job as cancelled.

    Raises:
        KeyError: Job not found.
        ValueError: Job is already in a terminal state.
    """
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise KeyError(f"Job '{job_id}' bulunamadı.")
    if job.status in ("done", "failed", "cancelled"):
        raise ValueError(f"Job zaten terminal durumda: '{job.status}'.")
    job.status = "cancelled"
    db.commit()
    db.refresh(job)
    logger.info("Job iptal edildi: %s", job_id)
    return {c.key: getattr(job, c.key) for c in job.__table__.columns}
