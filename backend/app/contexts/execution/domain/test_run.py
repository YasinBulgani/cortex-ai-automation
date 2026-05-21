"""
TestRun aggregate — test execution lifecycle.

State machine:
    QUEUED → RUNNING → PASSED
                    ↘ FAILED
          → CANCELLED (from QUEUED or RUNNING)

Business rules:
- Steps can only be recorded while RUNNING
- Completed run is immutable
- Duration is calculated from start → finish
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.contexts._shared.kernel import AggregateRoot, EntityId, ValueObject

from .events import (
    RunCancelled,
    RunCompleted,
    RunFailed,
    RunStarted,
    StepRecorded,
)


@dataclass(frozen=True, slots=True)
class TestRunId(EntityId):
    """Strongly-typed test run ID."""
    pass


class RunStatus(str, Enum):
    QUEUED    = "queued"
    RUNNING   = "running"
    PASSED    = "passed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class RunTrigger(str, Enum):
    MANUAL    = "manual"
    CI        = "ci"
    SCHEDULED = "scheduled"


@dataclass(slots=True)
class StepResult:
    index: int
    text: str
    passed: bool
    duration_ms: int
    error: str | None = None
    screenshot_url: str | None = None


class TestRun(AggregateRoot[TestRunId]):
    """Test run aggregate root."""

    _TERMINAL: frozenset[RunStatus] = frozenset({
        RunStatus.PASSED, RunStatus.FAILED, RunStatus.CANCELLED
    })

    def __init__(
        self,
        id: TestRunId,
        project_id: UUID,
        scenario_id: UUID | None = None,
        status: RunStatus = RunStatus.QUEUED,
        trigger: RunTrigger = RunTrigger.MANUAL,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        step_results: list[StepResult] | None = None,
    ):
        super().__init__(id)
        self.project_id = project_id
        self.scenario_id = scenario_id
        self.status = status
        self.trigger = trigger
        self.started_at = started_at
        self.finished_at = finished_at
        self.step_results: list[StepResult] = step_results or []

    # ─── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def queue(
        cls,
        project_id: UUID,
        scenario_id: UUID | None = None,
        trigger: RunTrigger = RunTrigger.MANUAL,
    ) -> "TestRun":
        run = cls(
            id=TestRunId.new(),
            project_id=project_id,
            scenario_id=scenario_id,
            trigger=trigger,
            status=RunStatus.QUEUED,
        )
        run._record_event(RunStarted(
            aggregate_id=run.id.value,
            project_id=str(project_id),
            scenario_id=str(scenario_id) if scenario_id else None,
            trigger=trigger.value,
        ))
        return run

    # ─── Behavior ───────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.status != RunStatus.QUEUED:
            raise ValueError(f"Sadece QUEUED run başlatılabilir, mevcut: {self.status.value}")
        self.status = RunStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def record_step(
        self,
        index: int,
        text: str,
        passed: bool,
        duration_ms: int = 0,
        error: str | None = None,
        screenshot_url: str | None = None,
    ) -> None:
        if self.status != RunStatus.RUNNING:
            raise ValueError("Step sadece RUNNING state'de kaydedilebilir")
        step = StepResult(
            index=index,
            text=text,
            passed=passed,
            duration_ms=duration_ms,
            error=error,
            screenshot_url=screenshot_url,
        )
        self.step_results.append(step)
        self._record_event(StepRecorded(
            aggregate_id=self.id.value,
            step_index=index,
            step_text=text,
            passed=passed,
            duration_ms=duration_ms,
            error=error,
            screenshot_url=screenshot_url,
        ))

    def complete(self) -> None:
        if self.status != RunStatus.RUNNING:
            raise ValueError("Sadece RUNNING run tamamlanabilir")
        self.status = RunStatus.PASSED
        self.finished_at = datetime.now(timezone.utc)
        duration = self._elapsed_ms()
        passed = sum(1 for s in self.step_results if s.passed)
        failed = sum(1 for s in self.step_results if not s.passed)
        self._record_event(RunCompleted(
            aggregate_id=self.id.value,
            duration_ms=duration,
            passed=passed,
            failed=failed,
            skipped=0,
        ))

    def fail(self, error: str, step_index: int = -1) -> None:
        if self.status != RunStatus.RUNNING:
            raise ValueError("Sadece RUNNING run fail edilebilir")
        self.status = RunStatus.FAILED
        self.finished_at = datetime.now(timezone.utc)
        self._record_event(RunFailed(
            aggregate_id=self.id.value,
            error=error,
            step_index=step_index,
        ))

    def cancel(self, reason: str = "") -> None:
        if self.status in self._TERMINAL:
            return  # No-op for terminal states
        self.status = RunStatus.CANCELLED
        self.finished_at = datetime.now(timezone.utc)
        self._record_event(RunCancelled(
            aggregate_id=self.id.value,
            reason=reason,
        ))

    # ─── Computed ────────────────────────────────────────────────────────────

    @property
    def duration_ms(self) -> int:
        return self._elapsed_ms()

    @property
    def pass_rate(self) -> float:
        if not self.step_results:
            return 0.0
        return sum(1 for s in self.step_results if s.passed) / len(self.step_results)

    def _elapsed_ms(self) -> int:
        if self.started_at is None:
            return 0
        end = self.finished_at or datetime.now(timezone.utc)
        return int((end - self.started_at).total_seconds() * 1000)
