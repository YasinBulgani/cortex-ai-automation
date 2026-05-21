"""
Scenarios context — application layer tests.
"""

import uuid
import pytest

from app.contexts._shared.outbox import InMemoryOutboxRepository
from app.contexts.scenarios.application.create_scenario import (
    CreateScenarioCommand,
    CreateScenarioHandler,
)
from app.contexts.scenarios.application.scenario_workflow import (
    AddStepCommand,
    AddStepHandler,
    ApproveScenarioCommand,
    ApproveScenarioHandler,
    ArchiveScenarioCommand,
    ArchiveScenarioHandler,
    PublishScenarioCommand,
    PublishScenarioHandler,
    RejectScenarioCommand,
    RejectScenarioHandler,
    SubmitForReviewCommand,
    SubmitForReviewHandler,
)
from app.contexts.scenarios.application.queries import (
    GetScenarioHandler,
    GetScenarioQuery,
    ListScenariosHandler,
    ListScenariosQuery,
)
from app.contexts.scenarios.domain.scenario import ScenarioStatus
from app.contexts.scenarios.infrastructure.scenario_repository import (
    InMemoryScenarioRepository,
)


@pytest.fixture()
def repo() -> InMemoryScenarioRepository:
    return InMemoryScenarioRepository()


@pytest.fixture()
def outbox() -> InMemoryOutboxRepository:
    return InMemoryOutboxRepository()


@pytest.fixture()
def project_id() -> uuid.UUID:
    return uuid.uuid4()


class TestCreateScenario:
    @pytest.mark.asyncio
    async def test_create_draft(self, repo, outbox, project_id):
        handler = CreateScenarioHandler(repo, outbox)
        sid = await handler.handle(CreateScenarioCommand(project_id=project_id, title="Login flow"))

        dto = await GetScenarioHandler(repo).handle(GetScenarioQuery(scenario_id=sid))
        assert dto is not None
        assert dto.title == "Login flow"
        assert dto.status == ScenarioStatus.DRAFT.value

    @pytest.mark.asyncio
    async def test_empty_title_raises(self, repo, outbox, project_id):
        handler = CreateScenarioHandler(repo, outbox)
        with pytest.raises(ValueError, match="boş"):
            await handler.handle(CreateScenarioCommand(project_id=project_id, title=""))

    @pytest.mark.asyncio
    async def test_outbox_has_created_event(self, repo, outbox, project_id):
        handler = CreateScenarioHandler(repo, outbox)
        await handler.handle(CreateScenarioCommand(project_id=project_id, title="X"))
        pending = await outbox.fetch_pending()
        assert any(e.event_type == "scenario.created" for e in pending)


class TestScenarioWorkflow:
    async def _make_draft(self, repo, outbox, project_id, title="Test") -> uuid.UUID:
        return await CreateScenarioHandler(repo, outbox).handle(
            CreateScenarioCommand(project_id=project_id, title=title)
        )

    @pytest.mark.asyncio
    async def test_add_step(self, repo, outbox, project_id):
        sid = await self._make_draft(repo, outbox, project_id)
        await AddStepHandler(repo, outbox).handle(
            AddStepCommand(scenario_id=sid, step_type="given", text="I am on login page", order=0)
        )
        dto = await GetScenarioHandler(repo).handle(GetScenarioQuery(scenario_id=sid))
        assert len(dto.steps) == 1
        assert dto.steps[0].text == "I am on login page"

    @pytest.mark.asyncio
    async def test_full_happy_path(self, repo, outbox, project_id):
        sid = await self._make_draft(repo, outbox, project_id)

        # Add required step
        await AddStepHandler(repo, outbox).handle(
            AddStepCommand(scenario_id=sid, step_type="when", text="I click login", order=0)
        )

        await SubmitForReviewHandler(repo, outbox).handle(SubmitForReviewCommand(scenario_id=sid))
        dto = await GetScenarioHandler(repo).handle(GetScenarioQuery(scenario_id=sid))
        assert dto.status == ScenarioStatus.REVIEW.value

        await ApproveScenarioHandler(repo, outbox).handle(
            ApproveScenarioCommand(scenario_id=sid, approver="lead@test.com")
        )

        await PublishScenarioHandler(repo, outbox).handle(PublishScenarioCommand(scenario_id=sid))
        dto = await GetScenarioHandler(repo).handle(GetScenarioQuery(scenario_id=sid))
        assert dto.status == ScenarioStatus.PUBLISHED.value

    @pytest.mark.asyncio
    async def test_reject_returns_to_draft(self, repo, outbox, project_id):
        sid = await self._make_draft(repo, outbox, project_id)
        await AddStepHandler(repo, outbox).handle(
            AddStepCommand(scenario_id=sid, step_type="then", text="I see dashboard", order=0)
        )
        await SubmitForReviewHandler(repo, outbox).handle(SubmitForReviewCommand(scenario_id=sid))
        await RejectScenarioHandler(repo, outbox).handle(
            RejectScenarioCommand(scenario_id=sid, reviewer="qa@test.com", reason="unclear step")
        )

        dto = await GetScenarioHandler(repo).handle(GetScenarioQuery(scenario_id=sid))
        assert dto.status == ScenarioStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_cannot_submit_without_steps(self, repo, outbox, project_id):
        sid = await self._make_draft(repo, outbox, project_id)
        with pytest.raises(ValueError, match="Step"):
            await SubmitForReviewHandler(repo, outbox).handle(SubmitForReviewCommand(scenario_id=sid))

    @pytest.mark.asyncio
    async def test_archive(self, repo, outbox, project_id):
        sid = await self._make_draft(repo, outbox, project_id)
        await ArchiveScenarioHandler(repo, outbox).handle(ArchiveScenarioCommand(scenario_id=sid))
        dto = await GetScenarioHandler(repo).handle(GetScenarioQuery(scenario_id=sid))
        assert dto.status == ScenarioStatus.ARCHIVED.value


class TestListScenarios:
    @pytest.mark.asyncio
    async def test_list_by_project(self, repo, outbox):
        p1 = uuid.uuid4()
        p2 = uuid.uuid4()
        create = CreateScenarioHandler(repo, outbox)
        await create.handle(CreateScenarioCommand(project_id=p1, title="S1"))
        await create.handle(CreateScenarioCommand(project_id=p1, title="S2"))
        await create.handle(CreateScenarioCommand(project_id=p2, title="S3"))

        dtos = await ListScenariosHandler(repo).handle(ListScenariosQuery(project_id=p1))
        assert len(dtos) == 2

    @pytest.mark.asyncio
    async def test_filter_by_status(self, repo, outbox):
        p = uuid.uuid4()
        create = CreateScenarioHandler(repo, outbox)
        s1 = await create.handle(CreateScenarioCommand(project_id=p, title="Draft"))
        s2 = await create.handle(CreateScenarioCommand(project_id=p, title="ToArchive"))

        await ArchiveScenarioHandler(repo, outbox).handle(ArchiveScenarioCommand(scenario_id=s2))

        dtos = await ListScenariosHandler(repo).handle(
            ListScenariosQuery(project_id=p, status="draft")
        )
        assert len(dtos) == 1
        assert dtos[0].title == "Draft"
