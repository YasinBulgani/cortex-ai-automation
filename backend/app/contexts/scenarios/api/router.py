"""
Scenarios bounded context — FastAPI HTTP layer.

Endpoints:
  POST /contexts/scenarios                           — CreateScenario
  GET  /contexts/scenarios?project_id={uuid}         — list for project
  GET  /contexts/scenarios/{id}                      — get scenario
  POST /contexts/scenarios/{id}/submit               — SubmitForReview
  POST /contexts/scenarios/{id}/approve              — ApproveScenario

Infrastructure: InMemoryScenarioRepository + cross-context ProjectExistsCheckAdapter
(uses projects repo singleton). Swap to SqlAlchemy repos for prod.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.contexts.projects.infrastructure import InMemoryProjectRepository
from app.contexts.projects.infrastructure.project_check_adapter import ProjectExistsCheckAdapter
from app.contexts.scenarios.application import (
    ApproveScenarioCommand,
    ApproveScenarioHandler,
    CreateScenarioCommand,
    CreateScenarioHandler,
    SubmitForReviewCommand,
    SubmitForReviewHandler,
)
from app.contexts.scenarios.application.create_scenario import ProjectNotActiveError
from app.contexts.scenarios.application.submit_for_review import ScenarioNotFoundError
from app.contexts.scenarios.domain import ScenarioId, ScenarioStep, StepType
from app.contexts.scenarios.infrastructure import InMemoryScenarioRepository

# Import the singleton project repo so cross-context check shares the same store
from app.contexts.projects.api.router import _projects_repo
from app.deps import get_current_user

router = APIRouter(prefix="/contexts/scenarios", tags=["contexts-scenarios"])

# ─── In-memory singletons ────────────────────────────────────────────────────

_scenarios_repo = InMemoryScenarioRepository()
_project_check = ProjectExistsCheckAdapter(_projects_repo)


class _InMemoryOutbox:
    async def append(self, entry) -> None:
        pass


_outbox = _InMemoryOutbox()

# ─── Pydantic schemas ────────────────────────────────────────────────────────


class ScenarioCreateIn(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=500)


class ApproveIn(BaseModel):
    approver: str = Field(..., min_length=1)


class ScenarioStepOut(BaseModel):
    type: str
    text: str
    order: int


class ScenarioOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    status: str
    steps: list[ScenarioStepOut]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _scenario_out(scenario) -> ScenarioOut:
    return ScenarioOut(
        id=scenario.id.value,
        project_id=scenario.project_id,
        title=str(scenario.title),
        status=scenario.status.value,
        steps=[ScenarioStepOut(type=s.type.value, text=s.text, order=s.order) for s in scenario.steps],
    )


async def _get_or_404(scenario_id: UUID):
    sc = await _scenarios_repo.get(ScenarioId(scenario_id))
    if sc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Senaryo bulunamadı")
    return sc


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("", response_model=ScenarioOut, status_code=status.HTTP_201_CREATED)
async def create_scenario(body: ScenarioCreateIn, _user=Depends(get_current_user)):
    handler = CreateScenarioHandler(
        scenarios=_scenarios_repo, outbox=_outbox, project_check=_project_check
    )
    try:
        scenario_id = await handler.handle(
            CreateScenarioCommand(project_id=body.project_id, title=body.title)
        )
    except ProjectNotActiveError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return _scenario_out(await _scenarios_repo.get(scenario_id))


@router.get("", response_model=list[ScenarioOut])
async def list_scenarios(
    project_id: UUID = Query(..., description="Projenin UUID'si"),
    _user=Depends(get_current_user),
):
    scenarios = await _scenarios_repo.list_for_project(project_id)
    return [_scenario_out(s) for s in scenarios]


@router.get("/{scenario_id}", response_model=ScenarioOut)
async def get_scenario(scenario_id: UUID, _user=Depends(get_current_user)):
    return _scenario_out(await _get_or_404(scenario_id))


@router.post("/{scenario_id}/submit", status_code=status.HTTP_204_NO_CONTENT)
async def submit_for_review(scenario_id: UUID, _user=Depends(get_current_user)):
    handler = SubmitForReviewHandler(scenarios=_scenarios_repo, outbox=_outbox)
    try:
        await handler.handle(SubmitForReviewCommand(scenario_id=ScenarioId(scenario_id)))
    except ScenarioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Senaryo bulunamadı")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/{scenario_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
async def approve_scenario(
    scenario_id: UUID, body: ApproveIn, _user=Depends(get_current_user)
):
    handler = ApproveScenarioHandler(scenarios=_scenarios_repo, outbox=_outbox)
    try:
        await handler.handle(
            ApproveScenarioCommand(scenario_id=ScenarioId(scenario_id), approver=body.approver)
        )
    except ScenarioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Senaryo bulunamadı")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
