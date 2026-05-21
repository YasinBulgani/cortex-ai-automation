"""RQ worker görevleri — sentetik örnek CSV üretimi (MVP)."""

from __future__ import annotations

import csv
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from faker import Faker

from app.config import settings
from app.infra.database import SessionLocal
from app.infra.models import Artifact, DatasetVersion, GenerationJob, JobEvent, utcnow

_fake = Faker("tr_TR")


def _emit(
    db,
    job_id: str,
    message: str,
    level: str = "info",
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    db.add(
        JobEvent(
            job_id=job_id,
            message=message,
            level=level,
            payload=payload,
            ts=utcnow(),
        )
    )
    db.commit()


def run_generation_job(job_id: str) -> None:
    db = SessionLocal()
    job = db.get(GenerationJob, job_id)
    if job is None:
        db.close()
        return
    try:
        job.status = "running"
        job.updated_at = utcnow()
        db.commit()
        _emit(db, job_id, "İş çalışıyor")

        ver = db.get(DatasetVersion, job.dataset_version_id)
        if ver is None:
            raise RuntimeError("dataset_version bulunamadı")

        out_dir = Path(settings.artifacts_dir) / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "output.csv"
        row_count = 25
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["full_name", "email", "city"])
            for _ in range(row_count):
                w.writerow([_fake.name(), _fake.email(), _fake.city()])

        size = csv_path.stat().st_size
        rel = str(csv_path.resolve())
        art = Artifact(
            job_id=job_id,
            storage_path=rel,
            mime_type="text/csv",
            size_bytes=size,
        )
        db.add(art)
        _emit(db, job_id, f"CSV oluşturuldu ({row_count} satır)", payload={"path": rel})
        job.status = "succeeded"
        job.error_message = None
        job.updated_at = utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        job = db.get(GenerationJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.updated_at = utcnow()
            db.add(
                JobEvent(
                    job_id=job_id,
                    level="error",
                    message=str(e),
                    payload={"traceback": traceback.format_exc()},
                    ts=utcnow(),
                )
            )
            db.commit()
    finally:
        db.close()
