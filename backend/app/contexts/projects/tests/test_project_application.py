"""
Projects context — application layer (use case) tests.
"""

import pytest

from app.contexts._shared.outbox import InMemoryOutboxRepository
from app.contexts.projects.application.archive_project import (
    ArchiveProjectCommand,
    ArchiveProjectHandler,
    RestoreProjectCommand,
    RestoreProjectHandler,
)
from app.contexts.projects.application.create_project import (
    CreateProjectCommand,
    CreateProjectHandler,
)
from app.contexts.projects.application.queries import (
    GetProjectHandler,
    GetProjectQuery,
    ListProjectsHandler,
    ListProjectsQuery,
)
from app.contexts.projects.application.rename_project import (
    RenameProjectCommand,
    RenameProjectHandler,
)
from app.contexts.projects.domain.project import ProjectStatus
from app.contexts.projects.infrastructure.project_repository import (
    InMemoryProjectRepository,
)


@pytest.fixture()
def repo() -> InMemoryProjectRepository:
    return InMemoryProjectRepository()


@pytest.fixture()
def outbox() -> InMemoryOutboxRepository:
    return InMemoryOutboxRepository()


class TestCreateProject:
    @pytest.mark.asyncio
    async def test_creates_project(self, repo, outbox):
        handler = CreateProjectHandler(repo, outbox)
        project_id = await handler.handle(
            CreateProjectCommand(name="Neurex QA", description="main project", product_family="web")
        )
        assert project_id is not None
        saved = await repo.get(
            __import__("app.contexts.projects.domain.project", fromlist=["ProjectId"]).ProjectId(project_id)
        )
        assert saved is not None
        assert str(saved.name) == "Neurex QA"

    @pytest.mark.asyncio
    async def test_outbox_receives_event(self, repo, outbox):
        handler = CreateProjectHandler(repo, outbox)
        await handler.handle(CreateProjectCommand(name="Outbox Test"))
        pending = await outbox.fetch_pending()
        assert len(pending) == 1
        assert pending[0].event_type == "project.created"

    @pytest.mark.asyncio
    async def test_invalid_name_raises(self, repo, outbox):
        handler = CreateProjectHandler(repo, outbox)
        with pytest.raises(ValueError, match="boş"):
            await handler.handle(CreateProjectCommand(name=""))


class TestRenameProject:
    @pytest.mark.asyncio
    async def test_rename_succeeds(self, repo, outbox):
        create = CreateProjectHandler(repo, outbox)
        pid = await create.handle(CreateProjectCommand(name="Old"))

        rename = RenameProjectHandler(repo, outbox)
        await rename.handle(RenameProjectCommand(project_id=pid, new_name="New"))

        from app.contexts.projects.domain.project import ProjectId
        saved = await repo.get(ProjectId(pid))
        assert str(saved.name) == "New"

    @pytest.mark.asyncio
    async def test_rename_missing_project_raises(self, repo, outbox):
        import uuid
        rename = RenameProjectHandler(repo, outbox)
        with pytest.raises(ValueError, match="bulunamadı"):
            await rename.handle(RenameProjectCommand(project_id=uuid.uuid4(), new_name="X"))


class TestArchiveRestore:
    @pytest.mark.asyncio
    async def test_archive_and_restore(self, repo, outbox):
        pid = await CreateProjectHandler(repo, outbox).handle(CreateProjectCommand(name="Arc"))

        await ArchiveProjectHandler(repo, outbox).handle(
            ArchiveProjectCommand(project_id=pid, reason="done")
        )

        from app.contexts.projects.domain.project import ProjectId
        saved = await repo.get(ProjectId(pid))
        assert saved.status == ProjectStatus.ARCHIVED

        await RestoreProjectHandler(repo, outbox).handle(RestoreProjectCommand(project_id=pid))
        saved = await repo.get(ProjectId(pid))
        assert saved.status == ProjectStatus.ACTIVE


class TestListProjects:
    @pytest.mark.asyncio
    async def test_list_active_only(self, repo, outbox):
        create = CreateProjectHandler(repo, outbox)
        pid1 = await create.handle(CreateProjectCommand(name="Active"))
        pid2 = await create.handle(CreateProjectCommand(name="ToArchive"))

        await ArchiveProjectHandler(repo, outbox).handle(
            ArchiveProjectCommand(project_id=pid2, reason="cleanup")
        )

        handler = ListProjectsHandler(repo)
        dtos = await handler.handle(ListProjectsQuery(archived=False))
        assert len(dtos) == 1
        assert dtos[0].name == "Active"

    @pytest.mark.asyncio
    async def test_filter_by_product_family(self, repo, outbox):
        create = CreateProjectHandler(repo, outbox)
        await create.handle(CreateProjectCommand(name="Web1", product_family="web"))
        await create.handle(CreateProjectCommand(name="Mob1", product_family="mobile"))

        handler = ListProjectsHandler(repo)
        dtos = await handler.handle(ListProjectsQuery(product_family="mobile"))
        assert len(dtos) == 1
        assert dtos[0].name == "Mob1"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, repo):
        import uuid
        handler = GetProjectHandler(repo)
        result = await handler.handle(GetProjectQuery(project_id=uuid.uuid4()))
        assert result is None
