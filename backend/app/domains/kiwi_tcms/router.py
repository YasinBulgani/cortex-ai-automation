"""Kiwi TCMS integration API under /api/v1/kiwi-tcms/*."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
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
from app.domains.tspm.models import TspmProject, TspmProjectMember
from app.infra.database import get_db
from app.infra.models import User

router = APIRouter(prefix="/kiwi-tcms", tags=["kiwi-tcms"])

DB = Annotated[Session, Depends(get_db)]
ReadUser = Annotated[User, Depends(require_permission("test_management.read"))]
WriteUser = Annotated[User, Depends(require_permission("test_management.write"))]
AdminUser = Annotated[User, Depends(require_permission("test_management.admin"))]


def _require_project_access(
    project_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
) -> None:
    if not db.get(TspmProject, project_id):
        raise HTTPException(404, "Proje bulunamadı")
    for role in (user.roles or []):
        for rp in (role.permissions or []):
            if getattr(rp, "permission", "") == "admin.*":
                return
    is_member = db.scalar(
        select(func.count()).where(
            TspmProjectMember.project_id == project_id,
            TspmProjectMember.user_id == user.id,
        )
    )
    if not is_member:
        raise HTTPException(403, "Bu projeye erişim yetkiniz yok")


@router.get("/projects/{project_id}/connection", response_model=Optional[KiwiConnectionOut],
            dependencies=[Depends(_require_project_access)])
def get_connection(project_id: str, db: DB, _user: ReadUser) -> Optional[KiwiConnectionOut]:
    conn = service.get_connection(db, project_id)
    return service.connection_out(conn) if conn is not None else None  # type: ignore[return-value]


@router.put("/projects/{project_id}/connection", response_model=KiwiConnectionOut,
            dependencies=[Depends(_require_project_access)])
def put_connection(project_id: str, payload: KiwiConnectionIn, db: DB, user: AdminUser) -> KiwiConnectionOut:
    try:
        conn = service.upsert_connection(db, project_id, payload, user)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return service.connection_out(conn)  # type: ignore[return-value]


@router.post("/projects/{project_id}/connection/test", response_model=KiwiTestConnectionResult,
             dependencies=[Depends(_require_project_access)])
async def test_connection(project_id: str, db: DB, user: WriteUser) -> KiwiTestConnectionResult:
    try:
        result = await service.test_connection(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result  # type: ignore[return-value]


@router.get("/projects/{project_id}/preview", response_model=KiwiPreviewOut,
            dependencies=[Depends(_require_project_access)])
async def preview(project_id: str, db: DB, _user: ReadUser) -> KiwiPreviewOut:
    try:
        result = await service.preview_sync(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result  # type: ignore[return-value]


@router.post("/projects/{project_id}/sync", response_model=KiwiSyncJobOut, status_code=status.HTTP_202_ACCEPTED,
             dependencies=[Depends(_require_project_access)])
def start_sync(project_id: str, payload: KiwiSyncStartIn, db: DB, user: WriteUser) -> KiwiSyncJobOut:
    try:
        job = service.enqueue_sync(db, project_id, payload.dry_run, user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return job  # type: ignore[return-value]


@router.get("/projects/{project_id}/sync-jobs", response_model=list[KiwiSyncJobOut],
            dependencies=[Depends(_require_project_access)])
def list_sync_jobs(
    project_id: str,
    db: DB,
    _user: ReadUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[KiwiSyncJobOut]:
    return service.list_sync_jobs(db, project_id, limit=limit)  # type: ignore[return-value]


@router.get("/projects/{project_id}/sync-jobs/{job_id}", response_model=KiwiSyncJobOut,
            dependencies=[Depends(_require_project_access)])
def get_sync_job(project_id: str, job_id: str, db: DB, _user: ReadUser) -> KiwiSyncJobOut:
    try:
        return service.get_sync_job(db, project_id, job_id)  # type: ignore[return-value]
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
