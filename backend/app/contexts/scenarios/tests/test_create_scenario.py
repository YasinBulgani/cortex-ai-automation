"""Unit tests for CreateScenarioHandler."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.contexts.scenarios.application import (
    CreateScenarioCommand,
    CreateScenarioHandler,
)
from app.contexts.scenarios.application.create_scenario import (
    ProjectNotActiveError,
)
from app.contexts.scenarios.domain import Scenario, ScenarioId


class InMemoryScenarioRepo:
    def __init__(self):
        self.by_id: dict[ScenarioId, Scenario] = {}

    async def get(self, scenario_id: ScenarioId) -> Scenario | None:
        return self.by_id.get(scenario_id)

    async def list_for_project(self, project_id: UUID, *, limit: int = 50) -> list[Scenario]:
        return [s for s in self.by_id.values() if s.project_id == project_id][:limit]

    async def save(self, scenario: Scenario) -> None:
        self.by_id[scenario.id] = scenario


class InMemoryOutbox:
    def __init__(self):
        self.entries = []

    async def append(self, entry) -> None:
        self.entries.append(entry)


class AlwaysActive:
    async def is_active(self, project_id: UUID) -> bool:
        return True


class NeverActive:
    async def is_active(self, project_id: UUID) -> bool:
        return False


@pytest.mark.asyncio
async def test_creates_scenario_for_active_project():
    repo = InMemoryScenarioRepo()
    outbox = InMemoryOutbox()
    handler = CreateScenarioHandler(
        scenarios=repo, outbox=outbox, project_check=AlwaysActive(),
    )
    project_id = uuid4()

    scenario_id = await handler.handle(
        CreateScenarioCommand(project_id=project_id, title="Login akışı"),
    )

    assert scenario_id in repo.by_id
    assert repo.by_id[scenario_id].project_id == project_id
    assert len(outbox.entries) == 1


@pytest.mark.asyncio
async def test_rejects_when_project_not_active():
    repo = InMemoryScenarioRepo()
    outbox = InMemoryOutbox()
    handler = CreateScenarioHandler(
        scenarios=repo, outbox=outbox, project_check=NeverActive(),
    )
    with pytest.raises(ProjectNotActiveError):
        await handler.handle(CreateScenarioCommand(project_id=uuid4(), title="x"))


@pytest.mark.asyncio
async def test_empty_title_raises():
    repo = InMemoryScenarioRepo()
    outbox = InMemoryOutbox()
    handler = CreateScenarioHandler(
        scenarios=repo, outbox=outbox, project_check=AlwaysActive(),
    )
    with pytest.raises(ValueError, match="boş olamaz"):
        await handler.handle(CreateScenarioCommand(project_id=uuid4(), title=""))
