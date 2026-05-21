"""CQRS read side — scenario queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.contexts.scenarios.domain.scenario import Scenario, ScenarioId
from .create_scenario import ScenarioRepository


@dataclass(frozen=True, slots=True)
class GetScenarioQuery:
    scenario_id: UUID


@dataclass(frozen=True, slots=True)
class ListScenariosQuery:
    project_id: UUID
    status: str | None = None


@dataclass(slots=True)
class StepDTO:
    type: str
    text: str
    order: int


@dataclass(slots=True)
class ScenarioDTO:
    id: str
    project_id: str
    title: str
    status: str
    steps: list[StepDTO] = field(default_factory=list)

    @classmethod
    def from_aggregate(cls, s: Scenario) -> "ScenarioDTO":
        return cls(
            id=str(s.id.value),
            project_id=str(s.project_id),
            title=str(s.title),
            status=s.status.value,
            steps=[StepDTO(type=step.type.value, text=step.text, order=step.order) for step in s.steps],
        )


class GetScenarioHandler:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self.scenarios = scenarios

    async def handle(self, query: GetScenarioQuery) -> ScenarioDTO | None:
        s = await self.scenarios.get(ScenarioId(query.scenario_id))
        if s is None:
            return None
        return ScenarioDTO.from_aggregate(s)


class ListScenariosHandler:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self.scenarios = scenarios

    async def handle(self, query: ListScenariosQuery) -> list[ScenarioDTO]:
        scenarios = await self.scenarios.list_by_project(
            project_id=query.project_id,
            status=query.status,
        )
        return [ScenarioDTO.from_aggregate(s) for s in scenarios]
