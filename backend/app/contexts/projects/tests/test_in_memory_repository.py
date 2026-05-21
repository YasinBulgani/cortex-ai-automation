"""Unit tests for InMemoryProjectRepository + ProjectExistsCheckAdapter."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.contexts.projects.domain import (
    ProductFamily,
    Project,
    ProjectId,
    ProjectName,
)
from app.contexts.projects.infrastructure import (
    InMemoryProjectRepository,
    ProjectExistsCheckAdapter,
)


def _make_project(name: str) -> Project:
    return Project.create(
        name=ProjectName(name),
        description="d",
        product_family=ProductFamily.WEB,
    )


@pytest.mark.asyncio
async def test_save_and_get_by_id():
    repo = InMemoryProjectRepository()
    project = _make_project("X")
    await repo.save(project)
    fetched = await repo.get(project.id)
    assert fetched is not None
    assert str(fetched.name) == "X"


@pytest.mark.asyncio
async def test_get_by_name():
    repo = InMemoryProjectRepository()
    project = _make_project("Y")
    await repo.save(project)
    fetched = await repo.get_by_name(ProjectName("Y"))
    assert fetched is not None
    assert fetched.id == project.id


@pytest.mark.asyncio
async def test_get_unknown_returns_none():
    repo = InMemoryProjectRepository()
    assert await repo.get(ProjectId.new()) is None
    assert await repo.get_by_name(ProjectName("yok")) is None


@pytest.mark.asyncio
async def test_rename_updates_name_index():
    repo = InMemoryProjectRepository()
    project = _make_project("Eski")
    await repo.save(project)
    assert await repo.get_by_name(ProjectName("Eski")) is not None

    project.rename(ProjectName("Yeni"))
    await repo.save(project)

    assert await repo.get_by_name(ProjectName("Eski")) is None
    assert await repo.get_by_name(ProjectName("Yeni")) is not None
    assert len(repo) == 1


@pytest.mark.asyncio
async def test_clear():
    repo = InMemoryProjectRepository()
    await repo.save(_make_project("A"))
    await repo.save(_make_project("B"))
    assert len(repo) == 2
    repo.clear()
    assert len(repo) == 0


@pytest.mark.asyncio
async def test_project_exists_check_adapter_active():
    repo = InMemoryProjectRepository()
    project = _make_project("X")
    await repo.save(project)
    check = ProjectExistsCheckAdapter(projects=repo)
    assert await check.is_active(project.id.value) is True


@pytest.mark.asyncio
async def test_project_exists_check_adapter_missing():
    repo = InMemoryProjectRepository()
    check = ProjectExistsCheckAdapter(projects=repo)
    assert await check.is_active(uuid4()) is False


@pytest.mark.asyncio
async def test_project_exists_check_adapter_archived():
    repo = InMemoryProjectRepository()
    project = _make_project("X")
    project.archive("legacy")
    await repo.save(project)
    check = ProjectExistsCheckAdapter(projects=repo)
    assert await check.is_active(project.id.value) is False
