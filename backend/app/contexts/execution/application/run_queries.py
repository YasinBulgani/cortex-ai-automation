"""Execution context — CQRS read side."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.contexts.execution.domain.test_run import TestRun, TestRunId
from .run_commands import RunRepository


@dataclass(frozen=True, slots=True)
class GetRunQuery:
    run_id: UUID


@dataclass(frozen=True, slots=True)
class ListRunsQuery:
    project_id: UUID
    limit: int = 50


@dataclass(slots=True)
class StepResultDTO:
    index: int
    text: str
    passed: bool
    duration_ms: int
    error: str | None
    screenshot_url: str | None


@dataclass(slots=True)
class RunDTO:
    id: str
    project_id: str
    scenario_id: str | None
    status: str
    trigger: str
    duration_ms: int
    pass_rate: float
    step_results: list[StepResultDTO] = field(default_factory=list)

    @classmethod
    def from_aggregate(cls, r: TestRun) -> "RunDTO":
        return cls(
            id=str(r.id.value),
            project_id=str(r.project_id),
            scenario_id=str(r.scenario_id) if r.scenario_id else None,
            status=r.status.value,
            trigger=r.trigger.value,
            duration_ms=r.duration_ms,
            pass_rate=r.pass_rate,
            step_results=[
                StepResultDTO(
                    index=s.index,
                    text=s.text,
                    passed=s.passed,
                    duration_ms=s.duration_ms,
                    error=s.error,
                    screenshot_url=s.screenshot_url,
                )
                for s in r.step_results
            ],
        )


class GetRunHandler:
    def __init__(self, runs: RunRepository) -> None:
        self.runs = runs

    async def handle(self, query: GetRunQuery) -> RunDTO | None:
        run = await self.runs.get(TestRunId(query.run_id))
        if run is None:
            return None
        return RunDTO.from_aggregate(run)


class ListRunsHandler:
    def __init__(self, runs: RunRepository) -> None:
        self.runs = runs

    async def handle(self, query: ListRunsQuery) -> list[RunDTO]:
        runs = await self.runs.list_by_project(query.project_id, limit=query.limit)
        return [RunDTO.from_aggregate(r) for r in runs]
