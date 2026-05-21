"""Approval-related service helpers for TSPM."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tspm.models import TspmApproval, TspmScenario, utcnow
from app.domains.tspm.schemas import ApprovalCreate, DecideRequest


def list_approvals_for_project(
    db: Session,
    project_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[TspmApproval]:
    return list(
        db.scalars(
            select(TspmApproval)
            .where(TspmApproval.project_id == project_id)
            .order_by(TspmApproval.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )


def create_approval_for_project(
    db: Session,
    project_id: str,
    body: ApprovalCreate,
) -> TspmApproval:
    title = (
        body.title
        or (body.draft_payload or {}).get("title")
        or body.source_text[:100]
        or "Onay"
    )
    approval = TspmApproval(
        project_id=project_id,
        title=title,
        status="pending",
        source_text=body.source_text or None,
        draft_payload=body.draft_payload or None,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def decide_approval_for_project(
    db: Session,
    project_id: str,
    approval_id: str,
    body: DecideRequest,
) -> dict:
    approval = db.get(TspmApproval, approval_id)
    if approval is None or approval.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onay bulunamadı")

    approval.status = body.decision
    approval.decided_at = utcnow()

    if body.decision == "approved" and approval.draft_payload and approval.scenario_id is None:
        payload = approval.draft_payload
        scenario = TspmScenario(
            project_id=project_id,
            title=payload.get("title", approval.title),
            description=payload.get("description", ""),
            steps=payload.get("steps", []),
            tags=[],
        )
        db.add(scenario)
        db.flush()
        approval.scenario_id = scenario.id

    db.commit()
    return {"ok": True}
