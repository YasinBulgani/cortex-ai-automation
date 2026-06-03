"""RQ worker task for Kiwi TCMS import-sync."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domains.kiwi_tcms import service
from app.domains.kiwi_tcms.models import KiwiSyncJob
from app.infra.database import SessionLocal

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_kiwi_sync_job(job_id: str) -> None:
    """Execute a queued Kiwi sync job. Mirrors jobs/tasks.py lifecycle handling."""
    db = SessionLocal()
    job = db.get(KiwiSyncJob, job_id)
    if job is None:
        db.close()
        return
    try:
        job.status = "running"
        job.started_at = _utcnow()
        db.commit()

        totals = service.execute_sync(db, job)

        job = db.get(KiwiSyncJob, job_id)
        if job is not None:
            job.status = "succeeded"
            job.totals = totals
            job.error = None
            job.finished_at = _utcnow()
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Kiwi sync job başarısız: %s", job_id)
        db.rollback()
        job = db.get(KiwiSyncJob, job_id)
        if job is not None:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = _utcnow()
            db.commit()
    finally:
        db.close()
