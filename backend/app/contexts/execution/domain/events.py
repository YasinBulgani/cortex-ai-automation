"""Execution context domain events."""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class RunStarted(DomainEvent):
    project_id: str = ""
    scenario_id: str | None = None
    trigger: str = "manual"  # manual | ci | scheduled


@dataclass(frozen=True, slots=True)
class RunCompleted(DomainEvent):
    duration_ms: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0


@dataclass(frozen=True, slots=True)
class RunFailed(DomainEvent):
    error: str = ""
    step_index: int = -1


@dataclass(frozen=True, slots=True)
class RunCancelled(DomainEvent):
    reason: str = ""


@dataclass(frozen=True, slots=True)
class StepRecorded(DomainEvent):
    step_index: int = 0
    step_text: str = ""
    passed: bool = True
    duration_ms: int = 0
    error: str | None = None
    screenshot_url: str | None = None
