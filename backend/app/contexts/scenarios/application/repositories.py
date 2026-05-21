"""Repository protocols for scenarios context."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.contexts.scenarios.domain import Scenario, ScenarioId


class ScenarioRepository(Protocol):
    async def get(self, scenario_id: ScenarioId) -> Scenario | None: ...
    async def list_for_project(self, project_id: UUID, *, limit: int = 50) -> list[Scenario]: ...
    async def save(self, scenario: Scenario) -> None: ...
