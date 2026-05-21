"""
Scenario repository implementations.

InMemoryScenarioRepository — for tests.
SqlScenarioRepository      — async SQLAlchemy (DB session required).
"""

from __future__ import annotations

from uuid import UUID

from app.contexts.scenarios.domain.scenario import (
    Scenario,
    ScenarioId,
    ScenarioStatus,
    ScenarioTitle,
    ScenarioStep,
    StepType,
)


class InMemoryScenarioRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Scenario] = {}

    async def get(self, scenario_id: ScenarioId) -> Scenario | None:
        return self._store.get(scenario_id.value)

    async def list_by_project(self, project_id: UUID, status: str | None = None) -> list[Scenario]:
        results = [s for s in self._store.values() if s.project_id == project_id]
        if status:
            try:
                st = ScenarioStatus(status)
                results = [s for s in results if s.status == st]
            except ValueError:
                pass
        return results

    async def save(self, scenario: Scenario) -> None:
        self._store[scenario.id.value] = scenario
