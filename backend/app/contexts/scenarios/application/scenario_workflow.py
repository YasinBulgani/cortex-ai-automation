"""
Scenario state-machine use cases:
  - AddStep / RemoveStep
  - SubmitForReview → Approve / Reject → Publish
  - Archive
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.contexts._shared.outbox import OutboxEntry, OutboxRepository
from app.contexts.scenarios.domain.scenario import ScenarioId, ScenarioStep, StepType
from .create_scenario import ScenarioRepository


# ─── Commands ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class AddStepCommand:
    scenario_id: UUID
    step_type: str  # given|when|then|and|but
    text: str
    order: int


@dataclass(frozen=True, slots=True)
class RemoveStepCommand:
    scenario_id: UUID
    order: int


@dataclass(frozen=True, slots=True)
class SubmitForReviewCommand:
    scenario_id: UUID


@dataclass(frozen=True, slots=True)
class ApproveScenarioCommand:
    scenario_id: UUID
    approver: str


@dataclass(frozen=True, slots=True)
class RejectScenarioCommand:
    scenario_id: UUID
    reviewer: str
    reason: str


@dataclass(frozen=True, slots=True)
class PublishScenarioCommand:
    scenario_id: UUID


@dataclass(frozen=True, slots=True)
class ArchiveScenarioCommand:
    scenario_id: UUID


# ─── Base handler ─────────────────────────────────────────────────────────

class _BaseScenarioHandler:
    def __init__(self, scenarios: ScenarioRepository, outbox: OutboxRepository) -> None:
        self.scenarios = scenarios
        self.outbox = outbox

    async def _load(self, scenario_id: UUID):
        s = await self.scenarios.get(ScenarioId(scenario_id))
        if s is None:
            raise ValueError(f"Senaryo bulunamadı: {scenario_id}")
        return s

    async def _save_with_events(self, scenario) -> None:
        await self.scenarios.save(scenario)
        for event in scenario.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))


# ─── Handlers ─────────────────────────────────────────────────────────────

class AddStepHandler(_BaseScenarioHandler):
    async def handle(self, cmd: AddStepCommand) -> None:
        s = await self._load(cmd.scenario_id)
        step = ScenarioStep(
            type=StepType(cmd.step_type),
            text=cmd.text,
            order=cmd.order,
        )
        s.add_step(step)
        await self._save_with_events(s)


class RemoveStepHandler(_BaseScenarioHandler):
    async def handle(self, cmd: RemoveStepCommand) -> None:
        s = await self._load(cmd.scenario_id)
        s.remove_step(cmd.order)
        await self._save_with_events(s)


class SubmitForReviewHandler(_BaseScenarioHandler):
    async def handle(self, cmd: SubmitForReviewCommand) -> None:
        s = await self._load(cmd.scenario_id)
        s.submit_for_review()
        await self._save_with_events(s)


class ApproveScenarioHandler(_BaseScenarioHandler):
    async def handle(self, cmd: ApproveScenarioCommand) -> None:
        s = await self._load(cmd.scenario_id)
        s.approve(approver=cmd.approver)
        await self._save_with_events(s)


class RejectScenarioHandler(_BaseScenarioHandler):
    async def handle(self, cmd: RejectScenarioCommand) -> None:
        s = await self._load(cmd.scenario_id)
        s.reject(reviewer=cmd.reviewer, reason=cmd.reason)
        await self._save_with_events(s)


class PublishScenarioHandler(_BaseScenarioHandler):
    async def handle(self, cmd: PublishScenarioCommand) -> None:
        s = await self._load(cmd.scenario_id)
        s.publish()
        await self._save_with_events(s)


class ArchiveScenarioHandler(_BaseScenarioHandler):
    async def handle(self, cmd: ArchiveScenarioCommand) -> None:
        s = await self._load(cmd.scenario_id)
        s.archive()
        await self._save_with_events(s)
