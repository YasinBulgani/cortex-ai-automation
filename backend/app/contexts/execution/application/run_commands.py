"""Execution context — CQRS write side."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.contexts._shared.outbox import OutboxEntry, OutboxRepository
from app.contexts.execution.domain.test_run import RunTrigger, TestRun, TestRunId


@dataclass(frozen=True, slots=True)
class QueueRunCommand:
    project_id: UUID
    scenario_id: UUID | None = None
    trigger: str = "manual"


@dataclass(frozen=True, slots=True)
class StartRunCommand:
    run_id: UUID


@dataclass(frozen=True, slots=True)
class RecordStepCommand:
    run_id: UUID
    index: int
    text: str
    passed: bool
    duration_ms: int = 0
    error: str | None = None
    screenshot_url: str | None = None


@dataclass(frozen=True, slots=True)
class CompleteRunCommand:
    run_id: UUID


@dataclass(frozen=True, slots=True)
class FailRunCommand:
    run_id: UUID
    error: str
    step_index: int = -1


@dataclass(frozen=True, slots=True)
class CancelRunCommand:
    run_id: UUID
    reason: str = ""


class RunRepository(Protocol):
    async def get(self, run_id: TestRunId) -> TestRun | None: ...
    async def list_by_project(self, project_id: UUID, limit: int = 50) -> list[TestRun]: ...
    async def save(self, run: TestRun) -> None: ...


class _BaseRunHandler:
    def __init__(self, runs: RunRepository, outbox: OutboxRepository) -> None:
        self.runs = runs
        self.outbox = outbox

    async def _load(self, run_id: UUID) -> TestRun:
        run = await self.runs.get(TestRunId(run_id))
        if run is None:
            raise ValueError(f"Run bulunamadı: {run_id}")
        return run

    async def _save(self, run: TestRun) -> None:
        await self.runs.save(run)
        for event in run.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))


class QueueRunHandler(_BaseRunHandler):
    async def handle(self, cmd: QueueRunCommand) -> UUID:
        try:
            trigger = RunTrigger(cmd.trigger)
        except ValueError:
            trigger = RunTrigger.MANUAL

        run = TestRun.queue(
            project_id=cmd.project_id,
            scenario_id=cmd.scenario_id,
            trigger=trigger,
        )
        await self._save(run)
        return run.id.value


class StartRunHandler(_BaseRunHandler):
    async def handle(self, cmd: StartRunCommand) -> None:
        run = await self._load(cmd.run_id)
        run.start()
        await self._save(run)


class RecordStepHandler(_BaseRunHandler):
    async def handle(self, cmd: RecordStepCommand) -> None:
        run = await self._load(cmd.run_id)
        run.record_step(
            index=cmd.index,
            text=cmd.text,
            passed=cmd.passed,
            duration_ms=cmd.duration_ms,
            error=cmd.error,
            screenshot_url=cmd.screenshot_url,
        )
        await self._save(run)


class CompleteRunHandler(_BaseRunHandler):
    async def handle(self, cmd: CompleteRunCommand) -> None:
        run = await self._load(cmd.run_id)
        run.complete()
        await self._save(run)


class FailRunHandler(_BaseRunHandler):
    async def handle(self, cmd: FailRunCommand) -> None:
        run = await self._load(cmd.run_id)
        run.fail(error=cmd.error, step_index=cmd.step_index)
        await self._save(run)


class CancelRunHandler(_BaseRunHandler):
    async def handle(self, cmd: CancelRunCommand) -> None:
        run = await self._load(cmd.run_id)
        run.cancel(reason=cmd.reason)
        await self._save(run)
