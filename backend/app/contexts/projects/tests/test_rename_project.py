"""Unit tests for RenameProjectHandler."""

from __future__ import annotations

import pytest

from app.contexts.projects.application import (
    CreateProjectCommand,
    CreateProjectHandler,
    RenameProjectCommand,
    RenameProjectHandler,
)
from app.contexts.projects.application.rename_project import (
    ProjectNameConflictError,
    ProjectNotFoundError,
)
from app.contexts.projects.domain import ProjectId

from .test_create_project import InMemoryOutbox, InMemoryProjectRepo


@pytest.mark.asyncio
async def test_renames_project():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    create = CreateProjectHandler(projects=repo, outbox=outbox)
    rename = RenameProjectHandler(projects=repo, outbox=outbox)

    pid = await create.handle(CreateProjectCommand(name="Eski"))
    await rename.handle(RenameProjectCommand(project_id=pid, new_name="Yeni"))

    project = await repo.get(pid)
    assert str(project.name) == "Yeni"


@pytest.mark.asyncio
async def test_rename_to_same_name_is_noop():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    create = CreateProjectHandler(projects=repo, outbox=outbox)
    rename = RenameProjectHandler(projects=repo, outbox=outbox)

    pid = await create.handle(CreateProjectCommand(name="X"))
    before = len(outbox.entries)
    await rename.handle(RenameProjectCommand(project_id=pid, new_name="X"))
    assert len(outbox.entries) == before


@pytest.mark.asyncio
async def test_rename_to_conflicting_name_rejected():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    create = CreateProjectHandler(projects=repo, outbox=outbox)
    rename = RenameProjectHandler(projects=repo, outbox=outbox)

    pid1 = await create.handle(CreateProjectCommand(name="A"))
    await create.handle(CreateProjectCommand(name="B"))

    with pytest.raises(ProjectNameConflictError):
        await rename.handle(RenameProjectCommand(project_id=pid1, new_name="B"))


@pytest.mark.asyncio
async def test_rename_unknown_project_raises_not_found():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    rename = RenameProjectHandler(projects=repo, outbox=outbox)

    with pytest.raises(ProjectNotFoundError):
        await rename.handle(RenameProjectCommand(project_id=ProjectId.new(), new_name="Z"))
