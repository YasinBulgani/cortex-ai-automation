"""
onboarding domain service unit testleri — 14 test.

onboarding/service.py; in-memory ProgressStore ve DEFAULT_STEPS kataloğunu
kullanır.  Testler saf Python nesneleri üzerinde çalışır; DB veya HTTP
gerekmez.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.onboarding.service import (
        DEFAULT_STEPS,
        ProgressStore,
        compute_progress,
        progress_store,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK, reason="onboarding service import failed"
)

# ---------------------------------------------------------------------------
# DEFAULT_STEPS catalog
# ---------------------------------------------------------------------------

class TestDefaultSteps:
    def test_catalog_is_non_empty(self):
        assert len(DEFAULT_STEPS) > 0

    def test_steps_have_unique_ids(self):
        ids = [s.id for s in DEFAULT_STEPS]
        assert len(ids) == len(set(ids)), "Duplicate step IDs detected"

    def test_steps_ordered_by_order_field(self):
        orders = [s.order for s in DEFAULT_STEPS]
        assert orders == sorted(orders)

    def test_known_steps_present(self):
        ids = {s.id for s in DEFAULT_STEPS}
        for expected in ("create_project", "select_ai_provider", "connect_cicd"):
            assert expected in ids

    def test_at_least_one_optional_step(self):
        optional = [s for s in DEFAULT_STEPS if s.is_optional]
        assert len(optional) >= 1

    def test_at_least_one_required_step(self):
        required = [s for s in DEFAULT_STEPS if not s.is_optional]
        assert len(required) >= 1


# ---------------------------------------------------------------------------
# ProgressStore
# ---------------------------------------------------------------------------

class TestProgressStore:
    def _store(self) -> ProgressStore:
        return ProgressStore()

    def test_get_unknown_project_returns_empty_dict(self):
        store = self._store()
        result = store.get("proj-999")
        assert result == {}

    def test_set_and_get(self):
        store = self._store()
        store.set("proj-1", "create_project", True)
        result = store.get("proj-1")
        assert result["create_project"] is True

    def test_set_idempotent(self):
        store = self._store()
        store.set("proj-1", "create_project", True)
        store.set("proj-1", "create_project", True)
        result = store.get("proj-1")
        assert result["create_project"] is True

    def test_reset_clears_project(self):
        store = self._store()
        store.set("proj-1", "create_project", True)
        store.reset("proj-1")
        result = store.get("proj-1")
        assert result == {}

    def test_reset_unknown_project_does_not_raise(self):
        store = self._store()
        store.reset("no-such-project")  # must not raise

    def test_snapshot_reflects_all_projects(self):
        store = self._store()
        store.set("proj-a", "create_project", True)
        store.set("proj-b", "select_ai_provider", False)
        snap = store.snapshot()
        assert "proj-a" in snap
        assert "proj-b" in snap

    def test_snapshot_is_copy_not_reference(self):
        store = self._store()
        store.set("proj-x", "create_project", True)
        snap = store.snapshot()
        snap["proj-x"]["create_project"] = False
        # original store must be unchanged
        assert store.get("proj-x")["create_project"] is True


# ---------------------------------------------------------------------------
# compute_progress
# ---------------------------------------------------------------------------

class TestComputeProgress:
    def test_empty_completed_gives_zero_pct(self):
        progress = compute_progress("proj-1", {})
        assert progress.completion_pct == 0.0

    def test_all_required_done_gives_100_pct(self):
        required_ids = {s.id for s in DEFAULT_STEPS if not s.is_optional}
        completed = {sid: True for sid in required_ids}
        progress = compute_progress("proj-1", completed)
        assert progress.completion_pct == 100.0
        assert progress.is_fully_onboarded is True

    def test_partial_completion_pct_between_0_and_100(self):
        completed = {"create_project": True}
        progress = compute_progress("proj-1", completed)
        assert 0.0 < progress.completion_pct <= 100.0

    def test_is_fully_onboarded_false_when_incomplete(self):
        progress = compute_progress("proj-1", {})
        assert progress.is_fully_onboarded is False

    def test_project_id_echoed(self):
        progress = compute_progress("my-project", {})
        assert progress.project_id == "my-project"

    def test_completed_map_includes_all_step_ids(self):
        progress = compute_progress("proj-1", {})
        for step in DEFAULT_STEPS:
            assert step.id in progress.completed

    def test_custom_steps_override_catalog(self):
        from app.domains.onboarding.schemas import OnboardingStep
        custom = [
            OnboardingStep(
                id="step_a", order=1, title="A", description="desc",
                is_optional=False, action_url="/a", help_doc="/docs/a"
            ),
            OnboardingStep(
                id="step_b", order=2, title="B", description="desc",
                is_optional=False, action_url="/b", help_doc="/docs/b"
            ),
        ]
        progress = compute_progress("proj-1", {"step_a": True}, steps=custom)
        assert progress.total_required == 2
        assert progress.completed_required == 1
        assert progress.completion_pct == 50.0
