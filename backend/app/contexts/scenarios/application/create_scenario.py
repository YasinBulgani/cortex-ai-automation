"""
Use case: Create a new draft scenario under a project.

Project'in var olduğunu (ve aktif olduğunu) burada validate ediyoruz.
Cross-context: ProjectExistsCheck protocol — ihtiyaç durumunda
projects/infrastructure tarafından implement edilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.contexts._shared.outbox import OutboxRepository, OutboxEntry
from app.contexts.scenarios.domain import Scenario, ScenarioId, ScenarioTitle

from .repositories import ScenarioRepository


@dataclass(frozen=True, slots=True)
class CreateScenarioCommand:
    project_id: UUID
    title: str


class ProjectNotActiveError(Exception):
    """Hedef proje yok ya da arşivli."""


class ProjectExistsCheck(Protocol):
    """Cross-context guard — projects context tarafı sağlar."""

    async def is_active(self, project_id: UUID) -> bool: ...


class AllowAllProjectCheck:
    async def is_active(self, project_id: UUID) -> bool:
        return True


class CreateScenarioHandler:
    def __init__(
        self,
        scenarios: ScenarioRepository,
        outbox: OutboxRepository,
        project_check: ProjectExistsCheck | None = None,
    ):
        self.scenarios = scenarios
        self.outbox = outbox
        self.project_check = project_check or AllowAllProjectCheck()

    async def handle(self, cmd: CreateScenarioCommand) -> ScenarioId:
        if not await self.project_check.is_active(cmd.project_id):
            raise ProjectNotActiveError(str(cmd.project_id))

        scenario = Scenario.create(
            project_id=cmd.project_id,
            title=ScenarioTitle(cmd.title),
        )

        await self.scenarios.save(scenario)
        for event in scenario.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))

        return scenario.id
