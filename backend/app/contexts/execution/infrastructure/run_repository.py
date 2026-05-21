"""In-memory TestRun repository — for tests and dev mode."""

from __future__ import annotations

from uuid import UUID

from app.contexts.execution.domain.test_run import TestRun, TestRunId


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, TestRun] = {}

    async def get(self, run_id: TestRunId) -> TestRun | None:
        return self._store.get(run_id.value)

    async def list_by_project(self, project_id: UUID, limit: int = 50) -> list[TestRun]:
        runs = [r for r in self._store.values() if r.project_id == project_id]
        # Most recent first
        runs.sort(key=lambda r: r.started_at or r.id.value, reverse=True)
        return runs[:limit]

    async def save(self, run: TestRun) -> None:
        self._store[run.id.value] = run
