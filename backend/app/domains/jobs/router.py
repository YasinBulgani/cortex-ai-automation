import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.error_messages import AppError
from app.core.utils import client_ip
from app.deps import get_current_user
from app.domains.audit.service import log_audit
from app.domains.jobs.schemas import (
    ArtifactOut,
    GenerationJobCreate,
    GenerationJobOut,
    JobEventOut,
)
from app.domains.jobs.tasks import run_generation_job
from app.infra.database import get_db
from app.infra.models import Artifact, DatasetVersion, GenerationJob, JobEvent, RuleSet, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _queue() -> Queue:
    return Queue(settings.rq_queue_name, connection=Redis.from_url(settings.redis_url))


@router.get("", response_model=list[GenerationJobOut])
def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
) -> list[GenerationJob]:
    """Arka plan islerini listeler."""
    try:
        q = (
            select(GenerationJob).order_by(GenerationJob.created_at.desc()).limit(min(limit, 200))
        )
        return list(db.scalars(q).all())
    except Exception as e:
        logger.error("list_jobs failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=GenerationJobOut, status_code=status.HTTP_202_ACCEPTED)
def enqueue_job(
    body: GenerationJobCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> GenerationJob:
    """Yeni arka plan isini kuyruga ekler."""
    try:
        ver = db.get(DatasetVersion, body.dataset_version_id)
        if ver is None:
            raise AppError("job.dataset_version_not_found")
        if body.rule_set_id:
            rs = db.get(RuleSet, body.rule_set_id)
            if rs is None or rs.dataset_id != ver.dataset_id:
                raise AppError("job.rule_set_mismatch")
        job = GenerationJob(
            dataset_version_id=body.dataset_version_id,
            rule_set_id=body.rule_set_id,
            status="queued",
            created_by=user.id,
        )
        db.add(job)
        db.flush()
        rq_job = _queue().enqueue(run_generation_job, job.id)
        job.rq_job_id = rq_job.id
        log_audit(
            db,
            actor_user_id=user.id,
            action="job.enqueue",
            resource_type="generation_job",
            resource_id=job.id,
            payload={"rq_job_id": job.rq_job_id},
            ip=client_ip(request),
        )
        db.commit()
        db.refresh(job)
        return job
    except (AppError, HTTPException):
        raise
    except Exception as e:
        logger.error("enqueue_job failed: %s", e, exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=GenerationJobOut)
def get_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> GenerationJob:
    """Is detayini ve durumunu getirir."""
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            raise AppError("job.not_found")
        return job
    except (AppError, HTTPException):
        raise
    except Exception as e:
        logger.error("get_job(%s) failed: %s", job_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/events", response_model=list[JobEventOut])
def list_events(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[JobEvent]:
    """Ise ait olay kayitlarini listeler."""
    try:
        if db.get(GenerationJob, job_id) is None:
            raise AppError("job.not_found")
        return list(
            db.scalars(
                select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.ts.asc())
            ).all()
        )
    except (AppError, HTTPException):
        raise
    except Exception as e:
        logger.error("list_events(%s) failed: %s", job_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/artifacts", response_model=list[ArtifactOut])
def list_job_artifacts(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """Ise bagli artifact dosyalarini listeler."""
    try:
        if db.get(GenerationJob, job_id) is None:
            raise AppError("job.not_found")
        arts = db.scalars(select(Artifact).where(Artifact.job_id == job_id)).all()
        return [
            ArtifactOut(
                id=a.id,
                job_id=a.job_id,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes,
                created_at=a.created_at,
            )
            for a in arts
        ]
    except (AppError, HTTPException):
        raise
    except Exception as e:
        logger.error("list_job_artifacts(%s) failed: %s", job_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
