"""Kiwi TCMS integration API under /api/v1/kiwi-tcms/*."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.deps import require_permission, get_current_user
from app.domains.kiwi_tcms import service
from app.domains.kiwi_tcms.schemas import (
    KiwiConnectionIn,
    KiwiConnectionOut,
    KiwiPreviewOut,
    KiwiSyncJobOut,
    KiwiSyncStartIn,
    KiwiTestConnectionResult,
)
from app.infra.database import get_db
from app.infra.models import User

router = APIRouter(prefix="/kiwi-tcms", tags=["kiwi-tcms"])

DB = Annotated[Session, Depends(get_db)]
ReadUser = Annotated[User, Depends(require_permission("test_management.read"))]
WriteUser = Annotated[User, Depends(require_permission("test_management.write"))]
AdminUser = Annotated[User, Depends(require_permission("test_management.admin"))]


@router.get("/projects/{project_id}/connection", response_model=Optional[KiwiConnectionOut])
def get_connection(project_id: str, db: DB, _user: ReadUser) -> Optional[KiwiConnectionOut]:
    conn = service.get_connection(db, project_id)
    return service.connection_out(conn) if conn is not None else None  # type: ignore[return-value]


@router.put("/projects/{project_id}/connection", response_model=KiwiConnectionOut)
def put_connection(project_id: str, payload: KiwiConnectionIn, db: DB, user: AdminUser) -> KiwiConnectionOut:
    try:
        conn = service.upsert_connection(db, project_id, payload, user)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return service.connection_out(conn)  # type: ignore[return-value]


@router.post("/projects/{project_id}/connection/test", response_model=KiwiTestConnectionResult)
async def test_connection(project_id: str, db: DB, user: WriteUser) -> KiwiTestConnectionResult:
    try:
        result = await service.test_connection(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result  # type: ignore[return-value]


@router.get("/projects/{project_id}/preview", response_model=KiwiPreviewOut)
async def preview(project_id: str, db: DB, _user: ReadUser) -> KiwiPreviewOut:
    try:
        result = await service.preview_sync(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result  # type: ignore[return-value]


@router.post("/projects/{project_id}/sync", response_model=KiwiSyncJobOut, status_code=status.HTTP_202_ACCEPTED)
def start_sync(project_id: str, payload: KiwiSyncStartIn, db: DB, user: WriteUser) -> KiwiSyncJobOut:
    try:
        job = service.enqueue_sync(db, project_id, payload.dry_run, user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return job  # type: ignore[return-value]


@router.get("/projects/{project_id}/sync-jobs", response_model=list[KiwiSyncJobOut])
def list_sync_jobs(
    project_id: str,
    db: DB,
    _user: ReadUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[KiwiSyncJobOut]:
    return service.list_sync_jobs(db, project_id, limit=limit)  # type: ignore[return-value]


@router.get("/projects/{project_id}/sync-jobs/{job_id}", response_model=KiwiSyncJobOut)
def get_sync_job(project_id: str, job_id: str, db: DB, _user: ReadUser) -> KiwiSyncJobOut:
    try:
        return service.get_sync_job(db, project_id, job_id)  # type: ignore[return-value]
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
