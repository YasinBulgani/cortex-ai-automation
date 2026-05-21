"""
In-memory scenario repository — testler ve local dev için.

Thread-safe değil, persistence yok. Production'da SqlAlchemyScenarioRepository
kullan.
"""

from __future__ import annotations

from uuid import UUID

from app.contexts.scenarios.application import ScenarioRepository
from app.contexts.scenarios.domain import Scenario, ScenarioId


class InMemoryScenarioRepository(ScenarioRepository):
    """ScenarioRepository in-memory implementasyonu."""

    def __init__(self):
        self._by_id: dict[ScenarioId, Scenario] = {}

    async def get(self, scenario_id: ScenarioId) -> Scenario | None:
        return self._by_id.get(scenario_id)

    async def list_for_project(self, project_id: UUID, *, limit: int = 50) -> list[Scenario]:
        matches = [s for s in self._by_id.values() if s.project_id == project_id]
        return matches[:limit]

    async def save(self, scenario: Scenario) -> None:
        self._by_id[scenario.id] = scenario

    # Yardımcı (test'ler için)
    def clear(self) -> None:
        self._by_id.clear()

    def __len__(self) -> int:
        return len(self._by_id)
