"""Scenario and requirement service helpers for TSPM."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.audit.service import log_audit
from app.domains.tspm.models import (
    TspmRequirement,
    TspmScenario,
    TspmScenarioRequirement,
    TspmScenarioVersion,
)
from app.domains.tspm.schemas import (
    BulkDeleteRequest,
    CoverageMatrixOut,
    CoverageMatrixRow,
    LinkRequirementRequest,
    RequirementCreate,
    RequirementOut,
    RequirementUpdate,
    ScenarioCreate,
    ScenarioOut,
    ScenarioUpdate,
)


def list_scenarios_for_project(
    db: Session,
    project_id: str,
    *,
    q: str | None = None,
    tag: str | None = None,
    tags: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[TspmScenario]:
    stmt = select(TspmScenario).where(TspmScenario.project_id == project_id)
    if q:
        stmt = stmt.where(TspmScenario.title.ilike(f"%{q}%"))
    if tag:
        stmt = stmt.where(TspmScenario.tags.contains([tag]))
    if tags:
        tag_list = [item.strip() for item in tags.split(",") if item.strip()]
        for item in tag_list:
            stmt = stmt.where(TspmScenario.tags.contains([item]))
    if status_filter:
        stmt = stmt.where(TspmScenario.status == status_filter)
    stmt = stmt.order_by(TspmScenario.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def create_scenario_for_project(
    db: Session,
    project_id: str,
    body: ScenarioCreate,
    *,
    actor_user_id: str,
) -> TspmScenario:
    scenario = TspmScenario(
        project_id=project_id,
        title=body.title,
        description=body.description,
        status=body.status,
        steps=body.steps or [],
        tags=body.tags or [],
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    log_audit(
        db,
        actor_user_id=actor_user_id,
        action="scenario.create",
        resource_type="scenario",
        resource_id=scenario.id,
        payload={"title": scenario.title, "project_id": project_id},
        ip=None,
    )
    db.commit()
    return scenario


def get_scenario_or_404(db: Session, project_id: str, scenario_id: str) -> TspmScenario:
    scenario = db.get(TspmScenario, scenario_id)
    if scenario is None or scenario.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Senaryo bulunamadı")
    return scenario


def update_scenario_for_project(
    db: Session,
    project_id: str,
    scenario_id: str,
    body: ScenarioUpdate,
    *,
    actor_user_id: str,
) -> TspmScenario:
    scenario = get_scenario_or_404(db, project_id, scenario_id)
    db.add(
        TspmScenarioVersion(
            scenario_id=scenario.id,
            version_number=scenario.current_version,
            title=scenario.title,
            description=scenario.description,
            steps=scenario.steps,
            status=scenario.status,
            changed_by=actor_user_id,
        )
    )
    if body.title is not None:
        scenario.title = body.title
    if body.description is not None:
        scenario.description = body.description
    if body.status is not None:
        scenario.status = body.status
    if body.steps is not None:
        scenario.steps = body.steps
    if body.tags is not None:
        scenario.tags = body.tags
    scenario.current_version += 1
    db.commit()
    db.refresh(scenario)
    log_audit(
        db,
        actor_user_id=actor_user_id,
        action="scenario.update",
        resource_type="scenario",
        resource_id=scenario.id,
        payload={
            "title": scenario.title,
            "version": scenario.current_version,
            "project_id": project_id,
        },
        ip=None,
    )
    db.commit()
    return scenario


def clone_scenario_for_project(db: Session, project_id: str, scenario_id: str) -> TspmScenario:
    src = get_scenario_or_404(db, project_id, scenario_id)
    clone = TspmScenario(
        project_id=project_id,
        title=f"{src.title} (kopya)",
        description=src.description,
        status="draft",
        steps=src.steps or [],
        tags=src.tags or [],
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


def bulk_delete_scenarios_for_project(
    db: Session,
    project_id: str,
    body: BulkDeleteRequest,
    *,
    actor_user_id: str,
) -> None:
    deleted_ids: list[str] = []
    for scenario_id in body.ids:
        scenario = db.get(TspmScenario, scenario_id)
        if scenario and scenario.project_id == project_id:
            db.delete(scenario)
            deleted_ids.append(scenario_id)
    db.commit()
    if deleted_ids:
        log_audit(
            db,
            actor_user_id=actor_user_id,
            action="scenario.bulk_delete",
            resource_type="scenario",
            resource_id=None,
            payload={
                "deleted_ids": deleted_ids,
                "project_id": project_id,
                "count": len(deleted_ids),
            },
            ip=None,
        )
        db.commit()


def create_requirement_for_project(
    db: Session,
    project_id: str,
    body: RequirementCreate,
) -> RequirementOut:
    requirement = TspmRequirement(
        project_id=project_id,
        external_id=body.external_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        source=body.source,
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return _requirement_out(requirement, 0)


def list_requirements_for_project(
    db: Session,
    project_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[RequirementOut]:
    requirements = list(
        db.scalars(
            select(TspmRequirement)
            .where(TspmRequirement.project_id == project_id)
            .order_by(TspmRequirement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )
    if not requirements:
        return []

    req_ids = [requirement.id for requirement in requirements]
    sc_rows = db.execute(
        select(TspmScenarioRequirement.requirement_id, func.count().label("cnt"))
        .where(TspmScenarioRequirement.requirement_id.in_(req_ids))
        .group_by(TspmScenarioRequirement.requirement_id)
    ).all()
    sc_by_req = {row.requirement_id: row.cnt for row in sc_rows}
    return [_requirement_out(requirement, sc_by_req.get(requirement.id, 0)) for requirement in requirements]


def update_requirement_for_project(
    db: Session,
    project_id: str,
    requirement_id: str,
    body: RequirementUpdate,
) -> RequirementOut:
    requirement = _get_requirement_or_404(db, project_id, requirement_id)
    if body.external_id is not None:
        requirement.external_id = body.external_id
    if body.title is not None:
        requirement.title = body.title
    if body.description is not None:
        requirement.description = body.description
    if body.priority is not None:
        requirement.priority = body.priority
    if body.source is not None:
        requirement.source = body.source
    db.commit()
    db.refresh(requirement)
    scenario_count = db.scalar(
        select(func.count()).where(TspmScenarioRequirement.requirement_id == requirement.id)
    ) or 0
    return _requirement_out(requirement, scenario_count)


def delete_requirement_for_project(db: Session, project_id: str, requirement_id: str) -> None:
    requirement = _get_requirement_or_404(db, project_id, requirement_id)
    db.delete(requirement)
    db.commit()


def link_scenario_requirements_for_project(
    db: Session,
    project_id: str,
    scenario_id: str,
    body: LinkRequirementRequest,
) -> dict:
    get_scenario_or_404(db, project_id, scenario_id)
    for requirement_id in body.requirement_ids:
        exists = db.scalar(
            select(func.count()).where(
                TspmScenarioRequirement.scenario_id == scenario_id,
                TspmScenarioRequirement.requirement_id == requirement_id,
            )
        )
        if not exists:
            db.add(
                TspmScenarioRequirement(
                    scenario_id=scenario_id,
                    requirement_id=requirement_id,
                )
            )
    db.commit()
    return {"ok": True}


def unlink_scenario_requirement_for_project(
    db: Session,
    scenario_id: str,
    requirement_id: str,
) -> None:
    link = db.scalar(
        select(TspmScenarioRequirement).where(
            TspmScenarioRequirement.scenario_id == scenario_id,
            TspmScenarioRequirement.requirement_id == requirement_id,
        )
    )
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bağlantı bulunamadı")
    db.delete(link)
    db.commit()


def build_coverage_matrix_for_project(db: Session, project_id: str) -> CoverageMatrixOut:
    requirements = list(
        db.scalars(select(TspmRequirement).where(TspmRequirement.project_id == project_id))
    )
    rows: list[CoverageMatrixRow] = []
    covered = 0
    for requirement in requirements:
        linked = list(
            db.scalars(
                select(TspmScenarioRequirement.scenario_id).where(
                    TspmScenarioRequirement.requirement_id == requirement.id
                )
            )
        )
        if linked:
            covered += 1
        rows.append(
            CoverageMatrixRow(
                requirement_id=requirement.id,
                external_id=requirement.external_id,
                title=requirement.title,
                scenario_ids=linked,
            )
        )

    total = len(requirements)
    pct = round(covered / total * 100, 1) if total > 0 else 0.0
    return CoverageMatrixOut(
        rows=rows,
        total_requirements=total,
        covered_count=covered,
        coverage_percent=pct,
    )


def get_coverage_gaps_for_project(db: Session, project_id: str) -> list[RequirementOut]:
    linked_ids = select(TspmScenarioRequirement.requirement_id).distinct()
    requirements = list(
        db.scalars(
            select(TspmRequirement).where(
                TspmRequirement.project_id == project_id,
                ~TspmRequirement.id.in_(linked_ids),
            )
        )
    )
    return [_requirement_out(requirement, 0) for requirement in requirements]


def _get_requirement_or_404(db: Session, project_id: str, requirement_id: str) -> TspmRequirement:
    requirement = db.get(TspmRequirement, requirement_id)
    if requirement is None or requirement.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gereksinim bulunamadı")
    return requirement


def _requirement_out(requirement: TspmRequirement, scenario_count: int) -> RequirementOut:
    return RequirementOut(
        id=requirement.id,
        external_id=requirement.external_id,
        title=requirement.title,
        description=requirement.description,
        priority=requirement.priority,
        source=requirement.source,
        scenario_count=scenario_count,
        created_at=requirement.created_at,
    )
