"""Defect router — /api/v1/defects.

CI entegrasyonu için tüm write endpoint'ler authentication gerektirir.
CI pipeline'ları service-account JWT token kullanmalıdır.
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import _user_permissions, get_current_user
from app.infra.database import get_db
from app.infra.models import User
from app.domains.defects import service as svc


def _require_project_access(project_id: str, db: Session, user: User) -> None:
    from app.domains.tspm.models import TspmProject, TspmProjectMember
    if db.get(TspmProject, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadı")
    if "admin.*" in _user_permissions(user):
        return
    is_member = db.scalar(
        select(func.count()).where(
            TspmProjectMember.project_id == project_id,
            TspmProjectMember.user_id == user.id,
        )
    )
    if not is_member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu projeye erişim yetkiniz yok")

router = APIRouter(prefix="/defects", tags=["defects"])


class OpenDefectIn(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=10_000)
    scenario_id: Optional[str] = None
    execution_id: Optional[str] = None
    severity: str = "major"
    error_class: str = "AssertionError"
    locator: str = ""
    auto_jira: bool = False


class MarkFixIn(BaseModel):
    commit_sha: str = Field(min_length=1, max_length=100)
    actor: str = "ci"


class VerifyIn(BaseModel):
    rerun_id: str = Field(min_length=1, max_length=100)
    rerun_passed: bool
    actor: str = "system"


@router.post("", status_code=status.HTTP_201_CREATED)
def open_defect(body: OpenDefectIn, user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> dict:
    _require_project_access(body.project_id, db, user)
    d = svc.open_defect_from_execution(
        project_id=body.project_id,
        title=body.title,
        description=body.description,
        scenario_id=body.scenario_id,
        execution_id=body.execution_id,
        severity=body.severity,  # type: ignore[arg-type]
        error_class=body.error_class,
        locator=body.locator,
        auto_jira=body.auto_jira,
    )
    return d.to_dict()


@router.get("")
def list_defects_endpoint(
    user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> list[dict]:
    if project_id:
        _require_project_access(project_id, db, user)
    return [d.to_dict() for d in svc.list_defects(project_id=project_id, status=status)]  # type: ignore[arg-type]


@router.get("/{defect_id}")
def get_defect_endpoint(defect_id: str, user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> dict:
    d = svc.get_defect(defect_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Defect bulunamadı")
    if d.project_id:
        _require_project_access(d.project_id, db, user)
    return d.to_dict()


@router.post("/{defect_id}/fix")
def mark_fix(defect_id: str, body: MarkFixIn, user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> dict:
    d = svc.get_defect(defect_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Defect bulunamadı")
    if d.project_id:
        _require_project_access(d.project_id, db, user)
    try:
        d = svc.mark_fix_merged(defect_id, body.commit_sha, actor=body.actor)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return d.to_dict()


@router.post("/{defect_id}/verify")
def verify_defect(defect_id: str, body: VerifyIn, user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)) -> dict:
    d_pre = svc.get_defect(defect_id)
    if d_pre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Defect bulunamadı")
    if d_pre.project_id:
        _require_project_access(d_pre.project_id, db, user)
    try:
        d = svc.verify_and_close(
            defect_id,
            rerun_id=body.rerun_id,
            rerun_passed=body.rerun_passed,
            actor=body.actor,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return d.to_dict()
