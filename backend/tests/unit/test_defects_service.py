"""Unit tests for the Defect Feedback Loop service.

Tests app/domains/defects/service.py — pure in-memory state machine,
no external dependencies.  Covers: DefectTicket, state transitions,
open_defect_from_execution deduplication, mark_fix_merged,
verify_and_close, list_defects, get_defect.
"""

from __future__ import annotations

import pytest

# Import service module and grab all symbols
import app.domains.defects.service as svc


@pytest.fixture(autouse=True)
def reset_store() -> None:
    """Reset in-memory store before every test (clear is provided by service)."""
    svc.clear()
    yield
    svc.clear()


# ── DefectTicket ──────────────────────────────────────────────────────────────


class TestDefectTicket:
    def test_to_dict_has_expected_keys(self) -> None:
        ticket = svc.DefectTicket(
            id="def-001",
            project_id="proj-1",
            title="Login fails on Safari",
            description="assertion error in auth",
        )
        d = ticket.to_dict()
        assert "id" in d
        assert "project_id" in d
        assert "status" in d
        assert "history" in d

    def test_default_status_is_open(self) -> None:
        ticket = svc.DefectTicket(id="x", project_id="p", title="t", description="d")
        assert ticket.status == "open"

    def test_transition_updates_status(self) -> None:
        ticket = svc.DefectTicket(id="x", project_id="p", title="t", description="d")
        ticket.transition("awaiting_fix", note="needs fix")
        assert ticket.status == "awaiting_fix"

    def test_transition_records_history(self) -> None:
        ticket = svc.DefectTicket(id="x", project_id="p", title="t", description="d")
        ticket.transition("awaiting_fix", note="assigned to dev", actor="alice")
        assert len(ticket.history) == 1
        entry = ticket.history[0]
        assert entry["from"] == "open"
        assert entry["to"] == "awaiting_fix"
        assert entry["actor"] == "alice"
        assert entry["note"] == "assigned to dev"

    def test_multiple_transitions_append_history(self) -> None:
        ticket = svc.DefectTicket(id="x", project_id="p", title="t", description="d")
        ticket.transition("awaiting_fix")
        ticket.transition("fix_merged")
        ticket.transition("verifying")
        assert len(ticket.history) == 3
        assert ticket.status == "verifying"

    def test_transition_updates_updated_at(self) -> None:
        ticket = svc.DefectTicket(id="x", project_id="p", title="t", description="d")
        before = ticket.updated_at
        ticket.transition("awaiting_fix")
        # updated_at should be set to a new timestamp (may be same second)
        assert ticket.updated_at >= before


# ── open_defect_from_execution ────────────────────────────────────────────────


class TestOpenDefectFromExecution:
    def test_creates_defect(self) -> None:
        defect = svc.open_defect_from_execution(
            project_id="proj-1",
            title="Checkout fails",
            description="Expected 200 got 500",
        )
        assert defect.id.startswith("def-")
        assert defect.project_id == "proj-1"
        assert defect.title == "Checkout fails"

    def test_status_is_awaiting_fix_after_open(self) -> None:
        defect = svc.open_defect_from_execution(
            project_id="proj-1",
            title="Bug",
            description="desc",
        )
        # auto-transition to awaiting_fix after open
        assert defect.status == "awaiting_fix"

    def test_history_has_auto_created_entry(self) -> None:
        defect = svc.open_defect_from_execution(
            project_id="p", title="t", description="d"
        )
        notes = [h["note"] for h in defect.history]
        assert any("Auto-created" in n for n in notes)

    def test_deduplication_same_signature_returns_existing(self) -> None:
        first = svc.open_defect_from_execution(
            project_id="p",
            title="Login bug",
            description="d",
            scenario_id="scn-1",
            error_class="AssertionError",
            locator="[data-testid=login-btn]",
        )
        second = svc.open_defect_from_execution(
            project_id="p",
            title="Login bug again",
            description="d2",
            scenario_id="scn-1",
            error_class="AssertionError",
            locator="[data-testid=login-btn]",
        )
        assert first.id == second.id  # same ticket returned

    def test_deduplication_appends_recurrence_to_history(self) -> None:
        first = svc.open_defect_from_execution(
            project_id="p", title="t", description="d",
            scenario_id="scn-1", error_class="AssertionError", locator="btn",
            execution_id="exec-1",
        )
        svc.open_defect_from_execution(
            project_id="p", title="t", description="d",
            scenario_id="scn-1", error_class="AssertionError", locator="btn",
            execution_id="exec-2",
        )
        recurrence = [h for h in first.history if "Tekrar" in h.get("note", "")]
        assert len(recurrence) == 1

    def test_different_signature_creates_new_defect(self) -> None:
        d1 = svc.open_defect_from_execution(
            project_id="p", title="Bug A", description="d",
            scenario_id="scn-1", error_class="AssertionError", locator="btn-a",
        )
        d2 = svc.open_defect_from_execution(
            project_id="p", title="Bug B", description="d",
            scenario_id="scn-2", error_class="AssertionError", locator="btn-b",
        )
        assert d1.id != d2.id

    def test_auto_jira_assigns_external_ref(self) -> None:
        defect = svc.open_defect_from_execution(
            project_id="p", title="t", description="d", auto_jira=True
        )
        assert defect.external_ref is not None
        assert defect.external_ref.startswith("NEUREX-")
        assert defect.external_url is not None

    def test_severity_assigned(self) -> None:
        defect = svc.open_defect_from_execution(
            project_id="p", title="t", description="d", severity="critical"
        )
        assert defect.severity == "critical"

    def test_defect_stored_in_list(self) -> None:
        svc.open_defect_from_execution(project_id="proj-1", title="t", description="d")
        items = svc.list_defects(project_id="proj-1")
        assert len(items) == 1


# ── mark_fix_merged ───────────────────────────────────────────────────────────


class TestMarkFixMerged:
    def test_transitions_to_verifying(self) -> None:
        defect = svc.open_defect_from_execution(project_id="p", title="t", description="d")
        result = svc.mark_fix_merged(defect.id, "abc123def456")
        assert result.status == "verifying"

    def test_fix_commit_stored(self) -> None:
        defect = svc.open_defect_from_execution(project_id="p", title="t", description="d")
        svc.mark_fix_merged(defect.id, "deadbeef0000")
        updated = svc.get_defect(defect.id)
        assert updated.fix_commit == "deadbeef0000"

    def test_unknown_defect_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="bulunamadı"):
            svc.mark_fix_merged("nonexistent-id", "commit-sha")

    def test_already_closed_defect_returns_unchanged(self) -> None:
        defect = svc.open_defect_from_execution(project_id="p", title="t", description="d")
        # Force-close it
        defect.status = "closed"
        result = svc.mark_fix_merged(defect.id, "sha")
        assert result.status == "closed"  # unchanged

    def test_history_contains_commit(self) -> None:
        defect = svc.open_defect_from_execution(project_id="p", title="t", description="d")
        svc.mark_fix_merged(defect.id, "mycomiit1234")
        notes = [h["note"] for h in defect.history]
        assert any("mycomiit" in n for n in notes)


# ── verify_and_close ──────────────────────────────────────────────────────────


class TestVerifyAndClose:
    def _open_and_merge(self) -> svc.DefectTicket:
        defect = svc.open_defect_from_execution(project_id="p", title="t", description="d")
        return svc.mark_fix_merged(defect.id, "fix-commit-sha")

    def test_rerun_passed_closes_defect(self) -> None:
        defect = self._open_and_merge()
        result = svc.verify_and_close(defect.id, rerun_id="run-001", rerun_passed=True)
        assert result.status == "closed"

    def test_rerun_failed_returns_to_awaiting_fix(self) -> None:
        defect = self._open_and_merge()
        result = svc.verify_and_close(defect.id, rerun_id="run-001", rerun_passed=False)
        assert result.status == "awaiting_fix"

    def test_rerun_id_stored(self) -> None:
        defect = self._open_and_merge()
        svc.verify_and_close(defect.id, rerun_id="rerun-xyz", rerun_passed=True)
        updated = svc.get_defect(defect.id)
        assert updated.rerun_id == "rerun-xyz"

    def test_unknown_defect_raises(self) -> None:
        with pytest.raises(ValueError, match="bulunamadı"):
            svc.verify_and_close("no-such-id", rerun_id="r", rerun_passed=True)

    def test_closed_defect_signature_removed(self) -> None:
        """After successful close, same signature should create a new ticket."""
        defect = svc.open_defect_from_execution(
            project_id="p", title="t", description="d",
            scenario_id="scn-1", error_class="E", locator="l",
        )
        merged = svc.mark_fix_merged(defect.id, "sha")
        svc.verify_and_close(merged.id, rerun_id="r", rerun_passed=True)

        # Same signature → should create NEW ticket since old one is closed
        new_defect = svc.open_defect_from_execution(
            project_id="p", title="t2", description="d2",
            scenario_id="scn-1", error_class="E", locator="l",
        )
        assert new_defect.id != defect.id

    def test_history_records_verified_and_closed(self) -> None:
        defect = self._open_and_merge()
        svc.verify_and_close(defect.id, rerun_id="r", rerun_passed=True)
        statuses = [h["to"] for h in defect.history]
        assert "verified" in statuses
        assert "closed" in statuses


# ── list_defects ──────────────────────────────────────────────────────────────


class TestListDefects:
    def test_empty_store_returns_empty(self) -> None:
        assert svc.list_defects() == []

    def test_returns_all_defects(self) -> None:
        svc.open_defect_from_execution(project_id="p1", title="A", description="d")
        svc.open_defect_from_execution(project_id="p1", title="B", description="d",
                                        error_class="TimeoutError", locator="x")
        assert len(svc.list_defects()) == 2

    def test_filter_by_project_id(self) -> None:
        svc.open_defect_from_execution(project_id="p1", title="A", description="d")
        svc.open_defect_from_execution(project_id="p2", title="B", description="d",
                                        error_class="TypeErr", locator="y")
        p1_items = svc.list_defects(project_id="p1")
        assert len(p1_items) == 1
        assert p1_items[0].project_id == "p1"

    def test_filter_by_status(self) -> None:
        svc.open_defect_from_execution(project_id="p", title="A", description="d")
        d2 = svc.open_defect_from_execution(project_id="p", title="B", description="d",
                                              error_class="X", locator="q")
        svc.mark_fix_merged(d2.id, "sha")
        svc.verify_and_close(d2.id, rerun_id="r", rerun_passed=True)

        open_items = svc.list_defects(status="awaiting_fix")
        assert len(open_items) == 1

        closed_items = svc.list_defects(status="closed")
        assert len(closed_items) == 1


# ── get_defect ────────────────────────────────────────────────────────────────


class TestGetDefect:
    def test_returns_existing_defect(self) -> None:
        defect = svc.open_defect_from_execution(project_id="p", title="t", description="d")
        found = svc.get_defect(defect.id)
        assert found is not None
        assert found.id == defect.id

    def test_returns_none_for_unknown_id(self) -> None:
        assert svc.get_defect("no-such-id") is None


# ── Full state machine integration ────────────────────────────────────────────


class TestFullStateMachineFlow:
    def test_happy_path_open_to_closed(self) -> None:
        """Full lifecycle: open → awaiting_fix → verifying → verified → closed."""
        defect = svc.open_defect_from_execution(
            project_id="p", title="Login regression", description="Safari timeout"
        )
        assert defect.status == "awaiting_fix"

        svc.mark_fix_merged(defect.id, "fix-abc")
        assert defect.status == "verifying"

        svc.verify_and_close(defect.id, rerun_id="rerun-01", rerun_passed=True)
        assert defect.status == "closed"

        # All statuses should appear in history
        statuses_seen = {h["to"] for h in defect.history}
        assert "awaiting_fix" in statuses_seen
        assert "verifying" in statuses_seen
        assert "verified" in statuses_seen
        assert "closed" in statuses_seen

    def test_rejection_loop_awaiting_fix_again(self) -> None:
        """Rejection puts defect back to awaiting_fix for developer to fix again."""
        defect = svc.open_defect_from_execution(project_id="p", title="t", description="d")
        svc.mark_fix_merged(defect.id, "first-attempt-sha")
        svc.verify_and_close(defect.id, rerun_id="r", rerun_passed=False)
        assert defect.status == "awaiting_fix"
        # History should contain rejected
        assert any(h["to"] == "rejected" for h in defect.history)
