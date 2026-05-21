"""
Execution context — FastAPI router.

Mounts at: /api/v2/runs
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.contexts._shared.outbox import InMemoryOutboxRepository
from app.contexts.execution.application.run_commands import (
    CancelRunCommand,
    CancelRunHandler,
    CompleteRunCommand,
    CompleteRunHandler,
    FailRunCommand,
    FailRunHandler,
    QueueRunCommand,
    QueueRunHandler,
    RecordStepCommand,
    RecordStepHandler,
    StartRunCommand,
    StartRunHandler,
)
from app.contexts.execution.application.run_queries import (
    GetRunHandler,
    GetRunQuery,
    ListRunsHandler,
    ListRunsQuery,
    RunDTO,
)
from app.contexts.execution.infrastructure.run_repository import InMemoryRunRepository

router = APIRouter(prefix="/api/v2/runs", tags=["execution-v2"])

_repo = InMemoryRunRepository()
_outbox = InMemoryOutboxRepository()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class QueueRunRequest(BaseModel):
    project_id: UUID
    scenario_id: UUID | None = None
    trigger: str = Field(default="manual", pattern=r"^(manual|ci|scheduled)$")


class RecordStepRequest(BaseModel):
    index: int = Field(..., ge=0)
    text: str
    passed: bool
    duration_ms: int = 0
    error: str | None = None
    screenshot_url: str | None = None


class FailRunRequest(BaseModel):
    error: str
    step_index: int = -1


class CancelRunRequest(BaseModel):
    reason: str = ""


class StepResultResponse(BaseModel):
    index: int
    text: str
    passed: bool
    duration_ms: int
    error: str | None
    screenshot_url: str | None


class RunResponse(BaseModel):
    id: str
    project_id: str
    scenario_id: str | None
    status: str
    trigger: str
    duration_ms: int
    pass_rate: float
    step_results: list[StepResultResponse]

    @classmethod
    def from_dto(cls, dto: RunDTO) -> "RunResponse":
        return cls(
            id=dto.id,
            project_id=dto.project_id,
            scenario_id=dto.scenario_id,
            status=dto.status,
            trigger=dto.trigger,
            duration_ms=dto.duration_ms,
            pass_rate=dto.pass_rate,
            step_results=[
                StepResultResponse(
                    index=s.index,
                    text=s.text,
                    passed=s.passed,
                    duration_ms=s.duration_ms,
                    error=s.error,
                    screenshot_url=s.screenshot_url,
                )
                for s in dto.step_results
            ],
        )


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=list[RunResponse])
async def list_runs(project_id: UUID, limit: int = 50) -> list[RunResponse]:
    dtos = await ListRunsHandler(_repo).handle(ListRunsQuery(project_id=project_id, limit=limit))
    return [RunResponse.from_dto(d) for d in dtos]


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def queue_run(body: QueueRunRequest) -> RunResponse:
    run_id = await QueueRunHandler(_repo, _outbox).handle(
        QueueRunCommand(
            project_id=body.project_id,
            scenario_id=body.scenario_id,
            trigger=body.trigger,
        )
    )
    dto = await GetRunHandler(_repo).handle(GetRunQuery(run_id=run_id))
    return RunResponse.from_dto(dto)  # type: ignore[arg-type]


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: UUID) -> RunResponse:
    dto = await GetRunHandler(_repo).handle(GetRunQuery(run_id=run_id))
    if dto is None:
        raise HTTPException(status_code=404, detail="Run bulunamadı")
    return RunResponse.from_dto(dto)


@router.post("/{run_id}/start", status_code=status.HTTP_204_NO_CONTENT)
async def start_run(run_id: UUID) -> None:
    try:
        await StartRunHandler(_repo, _outbox).handle(StartRunCommand(run_id=run_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{run_id}/steps", status_code=status.HTTP_201_CREATED)
async def record_step(run_id: UUID, body: RecordStepRequest) -> dict:
    try:
        await RecordStepHandler(_repo, _outbox).handle(
            RecordStepCommand(
                run_id=run_id,
                index=body.index,
                text=body.text,
                passed=body.passed,
                duration_ms=body.duration_ms,
                error=body.error,
                screenshot_url=body.screenshot_url,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{run_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
async def complete_run(run_id: UUID) -> None:
    try:
        await CompleteRunHandler(_repo, _outbox).handle(CompleteRunCommand(run_id=run_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{run_id}/fail", status_code=status.HTTP_204_NO_CONTENT)
async def fail_run(run_id: UUID, body: FailRunRequest) -> None:
    try:
        await FailRunHandler(_repo, _outbox).handle(
            FailRunCommand(run_id=run_id, error=body.error, step_index=body.step_index)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{run_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_run(run_id: UUID, body: CancelRunRequest) -> None:
    try:
        await CancelRunHandler(_repo, _outbox).handle(
            CancelRunCommand(run_id=run_id, reason=body.reason)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
