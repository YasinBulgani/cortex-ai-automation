"""Onboarding service + store için unit testler — UX-F3-302."""
from __future__ import annotations

import pytest

from app.domains.onboarding.service import (
    DEFAULT_STEPS,
    ProgressStore,
    compute_progress,
)


# ── DEFAULT_STEPS bütünlüğü ───────────────────────────────────────────────


def test_steps_unique_ids() -> None:
    ids = [s.id for s in DEFAULT_STEPS]
    assert len(set(ids)) == len(ids), f"Duplike ID: {ids}"


def test_steps_order_strictly_increasing() -> None:
    orders = [s.order for s in DEFAULT_STEPS]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)


def test_at_least_one_optional_step() -> None:
    # CI/CD opsiyonel olmalı, aksi halde %100 tamamlama çok zor
    assert any(s.is_optional for s in DEFAULT_STEPS)


def test_required_steps_have_action_url() -> None:
    for s in DEFAULT_STEPS:
        if not s.is_optional:
            assert s.action_url, f"{s.id} için action_url yok"


# ── compute_progress ──────────────────────────────────────────────────────


def test_fresh_user_zero_pct() -> None:
    p = compute_progress(project_id="p1", completed={})
    assert p.completion_pct == 0.0
    assert p.completed_required == 0
    assert p.is_fully_onboarded is False


def test_all_required_complete() -> None:
    required_ids = [s.id for s in DEFAULT_STEPS if not s.is_optional]
    completed = {sid: True for sid in required_ids}
    p = compute_progress(project_id="p1", completed=completed)
    assert p.completion_pct == 100.0
    assert p.is_fully_onboarded is True


def test_optional_step_doesnt_affect_completion() -> None:
    """Opsiyonel adım tamamlanmamışken tüm zorunlular tamamsa %100."""
    completed = {s.id: True for s in DEFAULT_STEPS if not s.is_optional}
    p = compute_progress(project_id="p1", completed=completed)
    assert p.completion_pct == 100.0
    # Opsiyonel hâlâ False olmalı map'te
    optional = [s for s in DEFAULT_STEPS if s.is_optional][0]
    assert p.completed[optional.id] is False


def test_partial_completion_pct() -> None:
    required = [s for s in DEFAULT_STEPS if not s.is_optional]
    half = {s.id: True for s in required[: len(required) // 2]}
    p = compute_progress(project_id="p1", completed=half)
    assert 0 < p.completion_pct < 100


def test_missing_keys_are_false() -> None:
    p = compute_progress(project_id="p1", completed={"create_project": True})
    for s in DEFAULT_STEPS:
        if s.id == "create_project":
            assert p.completed[s.id] is True
        else:
            assert p.completed[s.id] is False


def test_unknown_keys_are_ignored() -> None:
    """completed dict'te geçersiz step_id varsa etkilememeli."""
    p = compute_progress(
        project_id="p1",
        completed={"create_project": True, "bogus_step": True},
    )
    assert "bogus_step" not in p.completed
    assert p.completed["create_project"] is True


# ── ProgressStore ─────────────────────────────────────────────────────────


def test_store_empty_by_default() -> None:
    store = ProgressStore()
    assert store.get("any") == {}


def test_store_set_and_get() -> None:
    store = ProgressStore()
    store.set("p1", "create_project", True)
    state = store.get("p1")
    assert state == {"create_project": True}


def test_store_projects_isolated() -> None:
    store = ProgressStore()
    store.set("p1", "create_project", True)
    store.set("p2", "select_ai_provider", True)
    assert store.get("p1") == {"create_project": True}
    assert store.get("p2") == {"select_ai_provider": True}


def test_store_reset() -> None:
    store = ProgressStore()
    store.set("p1", "create_project", True)
    store.reset("p1")
    assert store.get("p1") == {}


def test_store_reset_non_existent_is_safe() -> None:
    store = ProgressStore()
    store.reset("never-existed")   # no crash


def test_store_set_false_removes_done() -> None:
    store = ProgressStore()
    store.set("p1", "create_project", True)
    store.set("p1", "create_project", False)
    assert store.get("p1") == {"create_project": False}


def test_store_get_returns_copy() -> None:
    """get() döndürdüğü dict mutate edilse orijinali etkilememeli."""
    store = ProgressStore()
    store.set("p1", "create_project", True)
    state = store.get("p1")
    state["tamper"] = True
    # Mutate sonrası orijinal etkilenmedi
    assert store.get("p1") == {"create_project": True}


# ── End-to-end (service integration) ──────────────────────────────────────


def test_progress_flow() -> None:
    store = ProgressStore()
    p_start = compute_progress("p1", store.get("p1"))
    assert p_start.completed_required == 0

    store.set("p1", "create_project", True)
    store.set("p1", "select_ai_provider", True)

    p_mid = compute_progress("p1", store.get("p1"))
    assert p_mid.completed_required == 2
    assert p_mid.completion_pct > p_start.completion_pct
    assert p_mid.is_fully_onboarded is False
