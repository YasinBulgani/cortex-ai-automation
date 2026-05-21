from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
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

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _queue() -> Queue:
    return Queue(settings.rq_queue_name, connection=Redis.from_url(settings.redis_url))


def _client_ip(request: Request) -> Optional[str]:
    if request.client:
        return request.client.host
    return None


@router.get("", response_model=list[GenerationJobOut])
def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
) -> list[GenerationJob]:
    """Arka plan islerini listeler."""
    q = (
        select(GenerationJob).order_by(GenerationJob.created_at.desc()).limit(min(limit, 200))
    )
    return list(db.scalars(q).all())


@router.post("", response_model=GenerationJobOut, status_code=status.HTTP_202_ACCEPTED)
def enqueue_job(
    body: GenerationJobCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> GenerationJob:
    """Yeni arka plan isini kuyruga ekler."""
    ver = db.get(DatasetVersion, body.dataset_version_id)
    if ver is None:
        raise HTTPException(status_code=404, detail="Veri seti sürümü bulunamadı")
    if body.rule_set_id:
        rs = db.get(RuleSet, body.rule_set_id)
        if rs is None or rs.dataset_id != ver.dataset_id:
            raise HTTPException(status_code=400, detail="Kural seti bu veri setine ait değil")
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
        ip=_client_ip(request),
    )
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=GenerationJobOut)
def get_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> GenerationJob:
    """Is detayini ve durumunu getirir."""
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    return job


@router.get("/{job_id}/events", response_model=list[JobEventOut])
def list_events(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[JobEvent]:
    """Ise ait olay kayitlarini listeler."""
    if db.get(GenerationJob, job_id) is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    return list(
        db.scalars(
            select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.ts.asc())
        ).all()
    )


@router.get("/{job_id}/artifacts", response_model=list[ArtifactOut])
def list_job_artifacts(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """Ise bagli artifact dosyalarini listeler."""
    if db.get(GenerationJob, job_id) is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
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
