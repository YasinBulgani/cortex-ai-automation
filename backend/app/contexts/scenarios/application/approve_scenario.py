"""
Use case: Approve a scenario currently in review.

Approver UserId tutulur (audit trail). Domain'de state transition guard
çalışır; review olmayan senaryo onaylanamaz.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.outbox import OutboxRepository, OutboxEntry
from app.contexts.scenarios.domain import ScenarioId

from .repositories import ScenarioRepository
from .submit_for_review import ScenarioNotFoundError


@dataclass(frozen=True, slots=True)
class ApproveScenarioCommand:
    scenario_id: ScenarioId
    approver: str


class ApproveScenarioHandler:
    def __init__(self, scenarios: ScenarioRepository, outbox: OutboxRepository):
        self.scenarios = scenarios
        self.outbox = outbox

    async def handle(self, cmd: ApproveScenarioCommand) -> None:
        scenario = await self.scenarios.get(cmd.scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(str(cmd.scenario_id))

        scenario.approve(cmd.approver)

        await self.scenarios.save(scenario)
        for event in scenario.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))
