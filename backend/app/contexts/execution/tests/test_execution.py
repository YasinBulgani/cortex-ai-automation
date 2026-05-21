"""
Execution context — domain + application tests.
"""

import uuid
import pytest

from app.contexts._shared.outbox import InMemoryOutboxRepository
from app.contexts.execution.application.run_commands import (
    CancelRunCommand,
    CancelRunHandler,
    CompleteRunCommand,
    CompleteRunHandler,
    FailRunCommand,
    FailRunHandler,
    QueueRunCommand,
    QueueRunHandler,
    RecordStepCommand,
    RecordStepHandler,
    StartRunCommand,
    StartRunHandler,
)
from app.contexts.execution.application.run_queries import (
    GetRunHandler,
    GetRunQuery,
    ListRunsHandler,
    ListRunsQuery,
)
from app.contexts.execution.domain.test_run import RunStatus
from app.contexts.execution.infrastructure.run_repository import InMemoryRunRepository


@pytest.fixture()
def repo():
    return InMemoryRunRepository()


@pytest.fixture()
def outbox():
    return InMemoryOutboxRepository()


@pytest.fixture()
def project_id():
    return uuid.uuid4()


async def _queue(repo, outbox, project_id, **kw) -> uuid.UUID:
    return await QueueRunHandler(repo, outbox).handle(
        QueueRunCommand(project_id=project_id, **kw)
    )


class TestQueueRun:
    @pytest.mark.asyncio
    async def test_creates_queued_run(self, repo, outbox, project_id):
        rid = await _queue(repo, outbox, project_id)
        dto = await GetRunHandler(repo).handle(GetRunQuery(run_id=rid))
        assert dto is not None
        assert dto.status == RunStatus.QUEUED.value

    @pytest.mark.asyncio
    async def test_outbox_has_run_started_event(self, repo, outbox, project_id):
        await _queue(repo, outbox, project_id)
        pending = await outbox.fetch_pending()
        assert any(e.event_type == "run.started" for e in pending)


class TestRunLifecycle:
    @pytest.mark.asyncio
    async def test_queue_start_complete(self, repo, outbox, project_id):
        rid = await _queue(repo, outbox, project_id)
        await StartRunHandler(repo, outbox).handle(StartRunCommand(run_id=rid))

        dto = await GetRunHandler(repo).handle(GetRunQuery(run_id=rid))
        assert dto.status == RunStatus.RUNNING.value

        await RecordStepHandler(repo, outbox).handle(
            RecordStepCommand(run_id=rid, index=0, text="Click login", passed=True, duration_ms=120)
        )

        await CompleteRunHandler(repo, outbox).handle(CompleteRunCommand(run_id=rid))
        dto = await GetRunHandler(repo).handle(GetRunQuery(run_id=rid))
        assert dto.status == RunStatus.PASSED.value
        assert dto.pass_rate == 1.0
        assert len(dto.step_results) == 1

    @pytest.mark.asyncio
    async def test_fail_run(self, repo, outbox, project_id):
        rid = await _queue(repo, outbox, project_id)
        await StartRunHandler(repo, outbox).handle(StartRunCommand(run_id=rid))
        await FailRunHandler(repo, outbox).handle(
            FailRunCommand(run_id=rid, error="Element not found", step_index=2)
        )
        dto = await GetRunHandler(repo).handle(GetRunQuery(run_id=rid))
        assert dto.status == RunStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_cancel_queued(self, repo, outbox, project_id):
        rid = await _queue(repo, outbox, project_id)
        await CancelRunHandler(repo, outbox).handle(CancelRunCommand(run_id=rid, reason="user request"))
        dto = await GetRunHandler(repo).handle(GetRunQuery(run_id=rid))
        assert dto.status == RunStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_cannot_start_completed_run(self, repo, outbox, project_id):
        rid = await _queue(repo, outbox, project_id)
        await StartRunHandler(repo, outbox).handle(StartRunCommand(run_id=rid))
        await CompleteRunHandler(repo, outbox).handle(CompleteRunCommand(run_id=rid))
        with pytest.raises(ValueError, match="QUEUED"):
            await StartRunHandler(repo, outbox).handle(StartRunCommand(run_id=rid))

    @pytest.mark.asyncio
    async def test_record_step_fails_when_not_running(self, repo, outbox, project_id):
        rid = await _queue(repo, outbox, project_id)
        with pytest.raises(ValueError, match="RUNNING"):
            await RecordStepHandler(repo, outbox).handle(
                RecordStepCommand(run_id=rid, index=0, text="step", passed=True)
            )

    @pytest.mark.asyncio
    async def test_pass_rate_with_mixed_steps(self, repo, outbox, project_id):
        rid = await _queue(repo, outbox, project_id)
        await StartRunHandler(repo, outbox).handle(StartRunCommand(run_id=rid))

        for i, passed in enumerate([True, True, False, True]):
            await RecordStepHandler(repo, outbox).handle(
                RecordStepCommand(run_id=rid, index=i, text=f"step {i}", passed=passed)
            )

        await CompleteRunHandler(repo, outbox).handle(CompleteRunCommand(run_id=rid))
        dto = await GetRunHandler(repo).handle(GetRunQuery(run_id=rid))
        assert dto.pass_rate == pytest.approx(0.75)


class TestListRuns:
    @pytest.mark.asyncio
    async def test_list_by_project(self, repo, outbox):
        p1 = uuid.uuid4()
        p2 = uuid.uuid4()
        await _queue(repo, outbox, p1)
        await _queue(repo, outbox, p1)
        await _queue(repo, outbox, p2)

        dtos = await ListRunsHandler(repo).handle(ListRunsQuery(project_id=p1))
        assert len(dtos) == 2

    @pytest.mark.asyncio
    async def test_run_not_found_returns_none(self, repo):
        dto = await GetRunHandler(repo).handle(GetRunQuery(run_id=uuid.uuid4()))
        assert dto is None
