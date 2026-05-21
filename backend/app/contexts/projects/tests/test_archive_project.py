"""Unit tests for ArchiveProjectHandler."""

from __future__ import annotations

import pytest

from app.contexts.projects.application import (
    ArchiveProjectCommand,
    ArchiveProjectHandler,
    CreateProjectCommand,
    CreateProjectHandler,
)
from app.contexts.projects.application.rename_project import ProjectNotFoundError
from app.contexts.projects.domain import ProjectId, ProjectStatus

from .test_create_project import InMemoryOutbox, InMemoryProjectRepo


@pytest.mark.asyncio
async def test_archives_active_project():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    create = CreateProjectHandler(projects=repo, outbox=outbox)
    archive = ArchiveProjectHandler(projects=repo, outbox=outbox)

    pid = await create.handle(CreateProjectCommand(name="X"))
    before = len(outbox.entries)
    await archive.handle(ArchiveProjectCommand(project_id=pid, reason="legacy"))

    project = await repo.get(pid)
    assert project.status == ProjectStatus.ARCHIVED
    # Event yayımlandı (created + archived → +1)
    assert len(outbox.entries) == before + 1


@pytest.mark.asyncio
async def test_archive_already_archived_is_noop():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    create = CreateProjectHandler(projects=repo, outbox=outbox)
    archive = ArchiveProjectHandler(projects=repo, outbox=outbox)

    pid = await create.handle(CreateProjectCommand(name="X"))
    await archive.handle(ArchiveProjectCommand(project_id=pid))
    before = len(outbox.entries)

    await archive.handle(ArchiveProjectCommand(project_id=pid))
    assert len(outbox.entries) == before


@pytest.mark.asyncio
async def test_archive_unknown_raises():
    repo = InMemoryProjectRepo()
    outbox = InMemoryOutbox()
    archive = ArchiveProjectHandler(projects=repo, outbox=outbox)

    with pytest.raises(ProjectNotFoundError):
        await archive.handle(ArchiveProjectCommand(project_id=ProjectId.new()))
