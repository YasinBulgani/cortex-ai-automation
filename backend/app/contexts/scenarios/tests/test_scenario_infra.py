"""Infrastructure tests for InMemoryScenarioRepository."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.contexts.scenarios.domain import (
    Scenario,
    ScenarioId,
    ScenarioStep,
    ScenarioTitle,
    StepType,
)
from app.contexts.scenarios.infrastructure import InMemoryScenarioRepository


def _make_scenario(project_id=None) -> Scenario:
    return Scenario.create(
        project_id=project_id or uuid4(),
        title=ScenarioTitle("Login testi"),
    )


# ─── save / get ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_get_returns_same_scenario():
    repo = InMemoryScenarioRepository()
    sc = _make_scenario()
    await repo.save(sc)

    fetched = await repo.get(sc.id)
    assert fetched is sc


@pytest.mark.asyncio
async def test_get_missing_returns_none():
    repo = InMemoryScenarioRepository()
    result = await repo.get(ScenarioId.new())
    assert result is None


@pytest.mark.asyncio
async def test_save_overwrites_previous_version():
    repo = InMemoryScenarioRepository()
    sc = _make_scenario()
    await repo.save(sc)

    step = ScenarioStep(type=StepType.GIVEN, text="Kullanıcı giriş sayfasındadır", order=0)
    sc.add_step(step)
    await repo.save(sc)

    fetched = await repo.get(sc.id)
    assert len(fetched.steps) == 1


# ─── list_for_project ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_for_project_returns_only_matching():
    repo = InMemoryScenarioRepository()
    pid = uuid4()
    sc1 = _make_scenario(project_id=pid)
    sc2 = _make_scenario(project_id=pid)
    other = _make_scenario()

    for s in (sc1, sc2, other):
        await repo.save(s)

    result = await repo.list_for_project(pid)
    ids = {s.id for s in result}
    assert ids == {sc1.id, sc2.id}


@pytest.mark.asyncio
async def test_list_for_project_empty_when_none():
    repo = InMemoryScenarioRepository()
    result = await repo.list_for_project(uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_list_for_project_respects_limit():
    repo = InMemoryScenarioRepository()
    pid = uuid4()
    for _ in range(5):
        await repo.save(_make_scenario(project_id=pid))

    result = await repo.list_for_project(pid, limit=3)
    assert len(result) == 3


# ─── clear / len ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clear_removes_all():
    repo = InMemoryScenarioRepository()
    await repo.save(_make_scenario())
    await repo.save(_make_scenario())
    assert len(repo) == 2

    repo.clear()
    assert len(repo) == 0


# ─── state transitions survive re-save ──────────────────────────────────────

@pytest.mark.asyncio
async def test_status_update_persists():
    repo = InMemoryScenarioRepository()
    sc = _make_scenario()
    step = ScenarioStep(type=StepType.WHEN, text="Şifreyi girer", order=0)
    sc.add_step(step)
    sc.submit_for_review()
    await repo.save(sc)

    fetched = await repo.get(sc.id)
    assert fetched.status.value == "review"


@pytest.mark.asyncio
async def test_multiple_steps_round_trip():
    repo = InMemoryScenarioRepository()
    sc = _make_scenario()
    sc.add_step(ScenarioStep(type=StepType.GIVEN, text="Sayfa açık", order=0))
    sc.add_step(ScenarioStep(type=StepType.WHEN, text="Form dolduruluyor", order=1))
    sc.add_step(ScenarioStep(type=StepType.THEN, text="Başarı mesajı görülür", order=2))
    await repo.save(sc)

    fetched = await repo.get(sc.id)
    assert len(fetched.steps) == 3
    assert fetched.steps[0].order == 0
    assert fetched.steps[2].type == StepType.THEN
