"""
Use case: Submit a draft scenario for review.

Domain'de step sayısı 0 ise hata fırlatılır.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.outbox import OutboxRepository, OutboxEntry
from app.contexts.scenarios.domain import ScenarioId

from .repositories import ScenarioRepository


@dataclass(frozen=True, slots=True)
class SubmitForReviewCommand:
    scenario_id: ScenarioId


class ScenarioNotFoundError(Exception):
    pass


class SubmitForReviewHandler:
    def __init__(self, scenarios: ScenarioRepository, outbox: OutboxRepository):
        self.scenarios = scenarios
        self.outbox = outbox

    async def handle(self, cmd: SubmitForReviewCommand) -> None:
        scenario = await self.scenarios.get(cmd.scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(str(cmd.scenario_id))

        scenario.submit_for_review()

        await self.scenarios.save(scenario)
        for event in scenario.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))
