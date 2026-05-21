"""Orchestrator testleri — ek bağımlılık olmadan (asyncio.run wrap)."""
from __future__ import annotations

import asyncio

import pytest

from app.domains.mobile.orchestrator import (
    _run_single_session,
    get_store,
    start_suite,
)
from app.domains.mobile.schemas import AppiumAction, SessionCreate


pytestmark = pytest.mark.P1


def _run(coro):
    """pytest-asyncio olmadan async coroutine çalıştır."""
    return asyncio.run(coro)


def test_start_suite_creates_sessions():
    req = SessionCreate(
        scenario_name="smoke-login",
        prompt="Uygulamayı aç ve doğrula",
        platform="android",
        parallel=2,
    )
    sessions = _run(start_suite(req))
    assert len(sessions) == 2
    assert all(s.scenario_name == "smoke-login" for s in sessions)
    assert all(s.device_id.startswith("and-") for s in sessions)


def test_start_suite_both_platform():
    req = SessionCreate(scenario_name="cross", prompt="test", platform="both", parallel=3)
    sessions = _run(start_suite(req))
    assert len(sessions) == 3


def test_start_suite_ios_filter():
    req = SessionCreate(scenario_name="ios-only", prompt="test", platform="ios", parallel=5)
    sessions = _run(start_suite(req))
    assert len(sessions) == 4  # yalnızca 4 iOS simülatörü var
    for s in sessions:
        assert s.device_id.startswith("ios-")


def test_start_suite_empty_when_no_device_available():
    # Önce tüm cihazları meşgul et
    req1 = SessionCreate(scenario_name="exhaust", prompt="test", platform="both", parallel=10)
    first = _run(start_suite(req1))
    assert len(first) >= 1

    # Hemen ardından tekrar iste — idle bulamamalı
    req2 = SessionCreate(scenario_name="should-fail", prompt="test", platform="both", parallel=1)
    second = _run(start_suite(req2))
    assert second == []


def test_session_store_records_steps():
    store = get_store()
    steps = [
        AppiumAction(action="launch"),
        AppiumAction(action="verifyVisible", by="accessibilityId", value="home"),
    ]
    sess = store.create(device_id="and-pixel_8", scenario_name="x", steps=steps)
    assert sess.id.startswith("s_")
    assert len(sess.steps) == 2
    assert sess.steps[0].action == "launch"
    assert sess.steps[0].status == "pending"


def test_run_single_session_always_pass_rate():
    """pass_rate=100 ile session kesin pass olmalı."""
    from app.domains.mobile.device_broker import get_broker

    broker = get_broker()
    steps = [
        AppiumAction(action="launch"),
        AppiumAction(action="find", by="accessibilityId", value="ok"),
        AppiumAction(action="tap"),
    ]
    store = get_store()
    sess = store.create("and-pixel_8", "always-pass", steps)

    _run(_run_single_session(sess.id, "and-pixel_8", steps, pass_rate=100, heal_rate=0))

    final = store.get(sess.id)
    assert final is not None
    assert final.status == "passed"
    assert broker.get("and-pixel_8").status == "idle"


def test_run_single_session_always_fail():
    """pass_rate=0 ile session kesin fail olmalı."""
    steps = [
        AppiumAction(action="launch"),
        AppiumAction(action="verifyVisible", by="accessibilityId", value="ok"),
    ]
    store = get_store()
    sess = store.create("and-pixel_6", "always-fail", steps)

    _run(_run_single_session(sess.id, "and-pixel_6", steps, pass_rate=0, heal_rate=0))

    final = store.get(sess.id)
    assert final is not None
    assert final.status == "failed"


def test_list_recent_sorted_by_time():
    store = get_store()
    s1 = store.create("and-pixel_8", "first", [AppiumAction(action="launch")])
    s2 = store.create("and-pixel_6", "second", [AppiumAction(action="launch")])

    recent = store.list_recent(limit=10)
    ids = [r.id for r in recent]
    # s2 daha yeni, ilk sırada olmalı
    assert ids.index(s2.id) < ids.index(s1.id)


def test_update_step_modifies_only_targeted():
    store = get_store()
    steps = [
        AppiumAction(action="launch"),
        AppiumAction(action="tap"),
        AppiumAction(action="back"),
    ]
    sess = store.create("and-pixel_8", "update-test", steps)

    store.update_step(sess.id, 1, status="passed", duration_ms=120)
    refreshed = store.get(sess.id)
    assert refreshed is not None
    assert refreshed.steps[0].status == "pending"
    assert refreshed.steps[1].status == "passed"
    assert refreshed.steps[1].duration_ms == 120
    assert refreshed.steps[2].status == "pending"
