"""Import-related service helpers for TSPM."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.tspm.models import TspmImport
from app.domains.tspm.schemas import ImportCreate


def create_import_for_project(
    db: Session,
    project_id: str,
    body: ImportCreate,
) -> TspmImport:
    imported = TspmImport(
        project_id=project_id,
        filename=body.filename,
        status="completed",
        scenario_count=0,
        raw_payload={"raw_text": body.raw_text},
    )
    db.add(imported)
    db.commit()
    db.refresh(imported)
    return imported
