"""Artifacts — thin service facade for job artifact management.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
Wraps SQLAlchemy Artifact model + filesystem storage.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.models import Artifact

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE_DIR = os.environ.get("ARTIFACT_STORAGE_DIR", "reports/artifacts")


def list_artifacts(
    db: Session,
    project_id: Optional[str] = None,
    job_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List artifacts, optionally scoped to a project or job.

    Args:
        db: SQLAlchemy session.
        project_id: Filter by owning project (via job relationship).
        job_id: Filter by parent GenerationJob ID.
        limit: Maximum rows (capped at 500).

    Returns:
        List of artifact dicts.
    """
    limit = min(int(limit), 500)
    q = select(Artifact).order_by(Artifact.created_at.desc()).limit(limit)
    if job_id:
        q = q.where(Artifact.job_id == job_id)
    artifacts = list(db.scalars(q).all())
    return [{c.key: getattr(a, c.key) for c in a.__table__.columns} for a in artifacts]


def get_artifact(db: Session, artifact_id: str) -> Dict[str, Any]:
    """Fetch a single artifact by ID.

    Raises:
        KeyError: Artifact not found.
    """
    art = db.get(Artifact, artifact_id)
    if art is None:
        raise KeyError(f"Artifact '{artifact_id}' bulunamadı.")
    return {c.key: getattr(art, c.key) for c in art.__table__.columns}


def upload(
    db: Session,
    file_data: bytes,
    filename: str,
    mime_type: str = "application/octet-stream",
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist an artifact file and register it in the DB.

    Args:
        db: SQLAlchemy session.
        file_data: Raw bytes of the file to store.
        filename: Original filename (used for storage path).
        mime_type: MIME type of the file.
        job_id: Optional parent GenerationJob ID.

    Returns:
        Created artifact dict.

    Raises:
        ValueError: Empty file_data.
    """
    if not file_data:
        raise ValueError("file_data boş olamaz.")

    storage_dir = Path(_DEFAULT_STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)

    artifact_id = uuid.uuid4().hex
    safe_name = Path(filename).name  # strip directory traversal
    storage_path = str(storage_dir / f"{artifact_id}_{safe_name}")

    Path(storage_path).write_bytes(file_data)

    art = Artifact(
        id=artifact_id,
        job_id=job_id,
        storage_path=storage_path,
        mime_type=mime_type,
        filename=safe_name,
        size=len(file_data),
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    logger.info("Artifact yüklendi: %s (%d bytes, job=%s)", artifact_id, len(file_data), job_id)
    return {c.key: getattr(art, c.key) for c in art.__table__.columns}


def delete_artifact(db: Session, artifact_id: str) -> None:
    """Delete an artifact from the DB and filesystem.

    Raises:
        KeyError: Artifact not found.
    """
    art = db.get(Artifact, artifact_id)
    if art is None:
        raise KeyError(f"Artifact '{artifact_id}' bulunamadı.")

    path = Path(art.storage_path)
    if path.exists():
        path.unlink(missing_ok=True)

    db.delete(art)
    db.commit()
    logger.info("Artifact silindi: %s", artifact_id)
