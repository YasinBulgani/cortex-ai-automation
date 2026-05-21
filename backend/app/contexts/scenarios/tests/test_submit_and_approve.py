"""Unit tests for SubmitForReview + ApproveScenario handlers."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.contexts.scenarios.application import (
    ApproveScenarioCommand,
    ApproveScenarioHandler,
    CreateScenarioCommand,
    CreateScenarioHandler,
    SubmitForReviewCommand,
    SubmitForReviewHandler,
)
from app.contexts.scenarios.application.submit_for_review import (
    ScenarioNotFoundError,
)
from app.contexts.scenarios.domain import (
    ScenarioId,
    ScenarioStatus,
    ScenarioStep,
    StepType,
)

from .test_create_scenario import AlwaysActive, InMemoryOutbox, InMemoryScenarioRepo


@pytest.mark.asyncio
async def test_submit_for_review_with_steps():
    repo = InMemoryScenarioRepo()
    outbox = InMemoryOutbox()
    create = CreateScenarioHandler(scenarios=repo, outbox=outbox, project_check=AlwaysActive())
    submit = SubmitForReviewHandler(scenarios=repo, outbox=outbox)

    sid = await create.handle(CreateScenarioCommand(project_id=uuid4(), title="t"))
    # Domain'i doğrudan kullan: step ekle
    scenario = await repo.get(sid)
    scenario.add_step(ScenarioStep(type=StepType.GIVEN, text="Kullanıcı login", order=1))
    await repo.save(scenario)

    await submit.handle(SubmitForReviewCommand(scenario_id=sid))
    assert (await repo.get(sid)).status == ScenarioStatus.REVIEW


@pytest.mark.asyncio
async def test_submit_without_steps_raises_value_error():
    repo = InMemoryScenarioRepo()
    outbox = InMemoryOutbox()
    create = CreateScenarioHandler(scenarios=repo, outbox=outbox, project_check=AlwaysActive())
    submit = SubmitForReviewHandler(scenarios=repo, outbox=outbox)

    sid = await create.handle(CreateScenarioCommand(project_id=uuid4(), title="t"))
    with pytest.raises(ValueError, match="Step'siz"):
        await submit.handle(SubmitForReviewCommand(scenario_id=sid))


@pytest.mark.asyncio
async def test_submit_unknown_raises_not_found():
    repo = InMemoryScenarioRepo()
    outbox = InMemoryOutbox()
    submit = SubmitForReviewHandler(scenarios=repo, outbox=outbox)

    with pytest.raises(ScenarioNotFoundError):
        await submit.handle(SubmitForReviewCommand(scenario_id=ScenarioId.new()))


@pytest.mark.asyncio
async def test_approve_after_review_succeeds():
    repo = InMemoryScenarioRepo()
    outbox = InMemoryOutbox()
    create = CreateScenarioHandler(scenarios=repo, outbox=outbox, project_check=AlwaysActive())
    submit = SubmitForReviewHandler(scenarios=repo, outbox=outbox)
    approve = ApproveScenarioHandler(scenarios=repo, outbox=outbox)

    sid = await create.handle(CreateScenarioCommand(project_id=uuid4(), title="t"))
    scenario = await repo.get(sid)
    scenario.add_step(ScenarioStep(type=StepType.WHEN, text="butona basar", order=1))
    await repo.save(scenario)
    await submit.handle(SubmitForReviewCommand(scenario_id=sid))

    await approve.handle(ApproveScenarioCommand(scenario_id=sid, approver="yasin"))
    assert (await repo.get(sid)).status == ScenarioStatus.APPROVED


@pytest.mark.asyncio
async def test_approve_draft_raises_invalid_transition():
    repo = InMemoryScenarioRepo()
    outbox = InMemoryOutbox()
    create = CreateScenarioHandler(scenarios=repo, outbox=outbox, project_check=AlwaysActive())
    approve = ApproveScenarioHandler(scenarios=repo, outbox=outbox)

    sid = await create.handle(CreateScenarioCommand(project_id=uuid4(), title="t"))
    with pytest.raises(ValueError, match="state transition"):
        await approve.handle(ApproveScenarioCommand(scenario_id=sid, approver="x"))
