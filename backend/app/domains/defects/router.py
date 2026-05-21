"""Defect router — /api/v1/defects."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.domains.defects import service as svc

router = APIRouter(prefix="/defects", tags=["defects"])


class OpenDefectIn(BaseModel):
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1)
    scenario_id: Optional[str] = None
    execution_id: Optional[str] = None
    severity: str = "major"
    error_class: str = "AssertionError"
    locator: str = ""
    auto_jira: bool = False


class MarkFixIn(BaseModel):
    commit_sha: str = Field(min_length=1)
    actor: str = "ci"


class VerifyIn(BaseModel):
    rerun_id: str = Field(min_length=1)
    rerun_passed: bool
    actor: str = "system"


@router.post("", status_code=status.HTTP_201_CREATED)
def open_defect(body: OpenDefectIn) -> dict:
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
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
) -> list[dict]:
    return [d.to_dict() for d in svc.list_defects(project_id=project_id, status=status)]  # type: ignore[arg-type]


@router.get("/{defect_id}")
def get_defect_endpoint(defect_id: str) -> dict:
    d = svc.get_defect(defect_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Defect bulunamadı")
    return d.to_dict()


@router.post("/{defect_id}/fix")
def mark_fix(defect_id: str, body: MarkFixIn) -> dict:
    try:
        d = svc.mark_fix_merged(defect_id, body.commit_sha, actor=body.actor)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return d.to_dict()


@router.post("/{defect_id}/verify")
def verify_defect(defect_id: str, body: VerifyIn) -> dict:
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
