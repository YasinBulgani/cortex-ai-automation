"""Unit tests for CreateProjectHandler — in-memory repos."""

from __future__ import annotations

import pytest

from app.contexts.projects.application import (
    CreateProjectCommand,
    CreateProjectHandler,
)
from app.contexts.projects.application.create_project import ProjectAlreadyExistsError
from app.contexts.projects.domain import Project, ProjectId, ProjectName


class InMemoryProjectRepo:
    def __init__(self):
        self.by_id: dict[ProjectId, Project] = {}
        self.by_name: dict[str, Project] = {}

    async def get(self, project_id: ProjectId) -> Project | None:
        return self.by_id.get(project_id)

    async def get_by_name(self, name: ProjectName) -> Project | None:
        return self.by_name.get(str(name))

    async def save(self, project: Project) -> None:
        self.by_id[project.id] = project
        self.by_name[str(project.name)] = project


class InMemoryOutbox:
    def __init__(self):
        self.entries = []

    async def append(self, entry) -> None:
        self.entries.append(entry)


@pytest.mark.asyncio
async def test_creates_project_with_unique_name():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    handler = CreateProjectHandler(projects=repo, outbox=outbox)

    project_id = await handler.handle(
        CreateProjectCommand(name="Müşteri Portalı", description="d")
    )

    assert project_id in repo.by_id
    saved = repo.by_id[project_id]
    assert str(saved.name) == "Müşteri Portalı"
    # Event yayımlandı
    assert len(outbox.entries) == 1


@pytest.mark.asyncio
async def test_rejects_duplicate_name():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    handler = CreateProjectHandler(projects=repo, outbox=outbox)

    await handler.handle(CreateProjectCommand(name="X"))
    with pytest.raises(ProjectAlreadyExistsError):
        await handler.handle(CreateProjectCommand(name="X"))

    # Sadece 1 event olmalı (ikinci işlem reject)
    assert len(outbox.entries) == 1


@pytest.mark.asyncio
async def test_rejects_empty_name():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    handler = CreateProjectHandler(projects=repo, outbox=outbox)

    with pytest.raises(ValueError, match="boş olamaz"):
        await handler.handle(CreateProjectCommand(name=""))
