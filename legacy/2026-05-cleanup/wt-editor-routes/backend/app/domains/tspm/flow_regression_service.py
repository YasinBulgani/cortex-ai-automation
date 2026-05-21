"""Flow and regression-set service helpers for TSPM."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tspm import regression_suggest as regression_suggest_svc
from app.domains.tspm.models import TspmFlow, TspmRegressionSet, TspmScenario
from app.domains.tspm.schemas import (
    AcceptSuggestedSetsRequest,
    AddScenariosRequest,
    FlowCreate,
    FlowDetailOut,
    FlowGraphUpdate,
    RegressionSetCreate,
    RegressionSetDetailOut,
    RegressionSetOut,
    RegressionSuggestRequest,
    RegressionSuggestResponse,
    ScenarioOut,
)


def list_flows_for_project(
    db: Session,
    project_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[TspmFlow]:
    return list(
        db.scalars(
            select(TspmFlow)
            .where(TspmFlow.project_id == project_id)
            .order_by(TspmFlow.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )


def create_flow_for_project(db: Session, project_id: str, body: FlowCreate) -> TspmFlow:
    flow = TspmFlow(project_id=project_id, name=body.name, description=body.description)
    db.add(flow)
    db.commit()
    db.refresh(flow)
    return flow


def get_flow_or_404(db: Session, project_id: str, flow_id: str) -> TspmFlow:
    flow = db.get(TspmFlow, flow_id)
    if flow is None or flow.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akış bulunamadı")
    return flow


def update_flow_graph_for_project(
    db: Session,
    project_id: str,
    flow_id: str,
    body: FlowGraphUpdate,
) -> TspmFlow:
    flow = get_flow_or_404(db, project_id, flow_id)
    flow.nodes = body.nodes
    flow.edges = body.edges
    db.commit()
    db.refresh(flow)
    return flow


def list_regression_sets_for_project(
    db: Session,
    project_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[RegressionSetOut]:
    sets = list(
        db.scalars(
            select(TspmRegressionSet)
            .where(TspmRegressionSet.project_id == project_id)
            .order_by(TspmRegressionSet.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )
    return [
        RegressionSetOut(
            id=regression_set.id,
            name=regression_set.name,
            description=regression_set.description,
            scenario_count=len(regression_set.scenario_ids or []),
            created_at=regression_set.created_at,
        )
        for regression_set in sets
    ]


def create_regression_set_for_project(
    db: Session,
    project_id: str,
    body: RegressionSetCreate,
) -> RegressionSetOut:
    regression_set = TspmRegressionSet(
        project_id=project_id,
        name=body.name,
        description=body.description,
        scenario_ids=[],
    )
    db.add(regression_set)
    db.commit()
    db.refresh(regression_set)
    return RegressionSetOut(
        id=regression_set.id,
        name=regression_set.name,
        description=regression_set.description,
        scenario_count=0,
        created_at=regression_set.created_at,
    )


def get_regression_set_detail_for_project(
    db: Session,
    project_id: str,
    set_id: str,
) -> RegressionSetDetailOut:
    regression_set = _get_regression_set_or_404(db, project_id, set_id)
    scenarios = []
    for scenario_id in (regression_set.scenario_ids or []):
        scenario = db.get(TspmScenario, scenario_id)
        if scenario:
            scenarios.append(
                ScenarioOut(
                    id=scenario.id,
                    title=scenario.title,
                    status=scenario.status,
                    current_version=scenario.current_version,
                    updated_at=scenario.updated_at,
                )
            )
    return RegressionSetDetailOut(
        id=regression_set.id,
        name=regression_set.name,
        description=regression_set.description,
        scenario_ids=regression_set.scenario_ids or [],
        scenarios=scenarios,
    )


def add_scenarios_to_regression_set(
    db: Session,
    project_id: str,
    set_id: str,
    body: AddScenariosRequest,
) -> dict:
    regression_set = _get_regression_set_or_404(db, project_id, set_id)
    existing = set(regression_set.scenario_ids or [])
    existing.update(body.scenario_ids)
    regression_set.scenario_ids = list(existing)
    db.commit()
    return {"ok": True, "count": len(regression_set.scenario_ids)}


def suggest_regression_sets_for_project(
    db: Session,
    project_id: str,
    body: RegressionSuggestRequest,
) -> RegressionSuggestResponse:
    scenarios = list(
        db.scalars(
            select(TspmScenario)
            .where(TspmScenario.project_id == project_id)
            .order_by(TspmScenario.created_at.desc())
        )
    )
    if not scenarios:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Öneri yapılabilmesi için projede en az bir senaryo olmalı.",
        )
    scenario_dicts = [
        {
            "id": scenario.id,
            "title": scenario.title,
            "status": scenario.status,
            "description": scenario.description,
            "tags": scenario.tags or [],
        }
        for scenario in scenarios
    ]
    raw_sets = regression_suggest_svc.suggest_regression_sets(
        scenario_dicts,
        body.extra_instructions,
    )
    return RegressionSuggestResponse(sets=raw_sets)


def accept_suggested_sets_for_project(
    db: Session,
    project_id: str,
    body: AcceptSuggestedSetsRequest,
) -> list[RegressionSetOut]:
    created = []
    for suggested in body.sets:
        regression_set = TspmRegressionSet(
            project_id=project_id,
            name=suggested.name,
            description=suggested.description,
            scenario_ids=suggested.scenario_ids,
        )
        db.add(regression_set)
        created.append(regression_set)
    db.commit()

    result = []
    for regression_set in created:
        db.refresh(regression_set)
        result.append(
            RegressionSetOut(
                id=regression_set.id,
                name=regression_set.name,
                description=regression_set.description,
                scenario_count=len(regression_set.scenario_ids or []),
                created_at=regression_set.created_at,
            )
        )
    return result


def _get_regression_set_or_404(
    db: Session,
    project_id: str,
    set_id: str,
) -> TspmRegressionSet:
    regression_set = db.get(TspmRegressionSet, set_id)
    if regression_set is None or regression_set.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Set bulunamadı")
    return regression_set
