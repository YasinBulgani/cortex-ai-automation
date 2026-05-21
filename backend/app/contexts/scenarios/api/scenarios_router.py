"""
Scenarios context — FastAPI router.

Mounts at: /api/v2/projects/{project_id}/scenarios
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.contexts._shared.outbox import InMemoryOutboxRepository
from app.contexts.scenarios.application.create_scenario import (
    CreateScenarioCommand,
    CreateScenarioHandler,
)
from app.contexts.scenarios.application.queries import (
    GetScenarioHandler,
    GetScenarioQuery,
    ListScenariosHandler,
    ListScenariosQuery,
    ScenarioDTO,
)
from app.contexts.scenarios.application.scenario_workflow import (
    AddStepCommand,
    AddStepHandler,
    ApproveScenarioCommand,
    ApproveScenarioHandler,
    ArchiveScenarioCommand,
    ArchiveScenarioHandler,
    PublishScenarioCommand,
    PublishScenarioHandler,
    RejectScenarioCommand,
    RejectScenarioHandler,
    SubmitForReviewCommand,
    SubmitForReviewHandler,
)
from app.contexts.scenarios.infrastructure.scenario_repository import (
    InMemoryScenarioRepository,
)

router = APIRouter(prefix="/api/v2/projects/{project_id}/scenarios", tags=["scenarios-v2"])

_repo = InMemoryScenarioRepository()
_outbox = InMemoryOutboxRepository()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CreateScenarioRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


class AddStepRequest(BaseModel):
    step_type: str = Field(..., pattern=r"^(given|when|then|and|but)$")
    text: str = Field(..., min_length=1)
    order: int = Field(..., ge=0)


class ApproveRequest(BaseModel):
    approver: str


class RejectRequest(BaseModel):
    reviewer: str
    reason: str


class StepResponse(BaseModel):
    type: str
    text: str
    order: int


class ScenarioResponse(BaseModel):
    id: str
    project_id: str
    title: str
    status: str
    steps: list[StepResponse]

    @classmethod
    def from_dto(cls, dto: ScenarioDTO) -> "ScenarioResponse":
        return cls(
            id=dto.id,
            project_id=dto.project_id,
            title=dto.title,
            status=dto.status,
            steps=[StepResponse(type=s.type, text=s.text, order=s.order) for s in dto.steps],
        )


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(project_id: UUID, status: str | None = None) -> list[ScenarioResponse]:
    handler = ListScenariosHandler(_repo)
    dtos = await handler.handle(ListScenariosQuery(project_id=project_id, status=status))
    return [ScenarioResponse.from_dto(d) for d in dtos]


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(project_id: UUID, body: CreateScenarioRequest) -> ScenarioResponse:
    handler = CreateScenarioHandler(_repo, _outbox)
    try:
        sid = await handler.handle(CreateScenarioCommand(project_id=project_id, title=body.title))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    dto = await GetScenarioHandler(_repo).handle(GetScenarioQuery(scenario_id=sid))
    return ScenarioResponse.from_dto(dto)  # type: ignore[arg-type]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(project_id: UUID, scenario_id: UUID) -> ScenarioResponse:
    dto = await GetScenarioHandler(_repo).handle(GetScenarioQuery(scenario_id=scenario_id))
    if dto is None or dto.project_id != str(project_id):
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")
    return ScenarioResponse.from_dto(dto)


@router.post("/{scenario_id}/steps", status_code=status.HTTP_201_CREATED)
async def add_step(project_id: UUID, scenario_id: UUID, body: AddStepRequest) -> dict:
    handler = AddStepHandler(_repo, _outbox)
    try:
        await handler.handle(AddStepCommand(
            scenario_id=scenario_id,
            step_type=body.step_type,
            text=body.text,
            order=body.order,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{scenario_id}/submit-review", status_code=status.HTTP_204_NO_CONTENT)
async def submit_for_review(project_id: UUID, scenario_id: UUID) -> None:
    try:
        await SubmitForReviewHandler(_repo, _outbox).handle(SubmitForReviewCommand(scenario_id=scenario_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{scenario_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
async def approve_scenario(project_id: UUID, scenario_id: UUID, body: ApproveRequest) -> None:
    try:
        await ApproveScenarioHandler(_repo, _outbox).handle(
            ApproveScenarioCommand(scenario_id=scenario_id, approver=body.approver)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{scenario_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_scenario(project_id: UUID, scenario_id: UUID, body: RejectRequest) -> None:
    try:
        await RejectScenarioHandler(_repo, _outbox).handle(
            RejectScenarioCommand(scenario_id=scenario_id, reviewer=body.reviewer, reason=body.reason)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{scenario_id}/publish", status_code=status.HTTP_204_NO_CONTENT)
async def publish_scenario(project_id: UUID, scenario_id: UUID) -> None:
    try:
        await PublishScenarioHandler(_repo, _outbox).handle(PublishScenarioCommand(scenario_id=scenario_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{scenario_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_scenario(project_id: UUID, scenario_id: UUID) -> None:
    try:
        await ArchiveScenarioHandler(_repo, _outbox).handle(ArchiveScenarioCommand(scenario_id=scenario_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
