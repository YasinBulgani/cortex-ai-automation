"""Unit tests for app.domains.defects.service (in-memory store)."""
from __future__ import annotations

import pytest

try:
    import app.domains.defects.service as svc
except ImportError as _e:  # pragma: no cover
    svc = None  # type: ignore

pytestmark = pytest.mark.skipif(svc is None, reason=f"defects service unavailable: {svc}")


@pytest.fixture(autouse=True)
def _clear_store():
    """Ensure a clean in-memory store for every test."""
    if svc is not None:
        svc.clear()
    yield
    if svc is not None:
        svc.clear()


# ── open_defect_from_execution ────────────────────────────────────────────


def test_open_defect_creates_ticket():
    defect = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Login fails",
        description="AssertionError on login page",
        severity="major",
    )
    assert defect.id.startswith("def-")
    assert defect.project_id == "proj-1"
    assert defect.title == "Login fails"
    assert defect.status == "awaiting_fix"


def test_open_defect_stored_and_retrievable():
    defect = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Button missing",
        description="Submit button not found",
    )
    stored = svc.get_defect(defect.id)
    assert stored is not None
    assert stored.id == defect.id


def test_open_defect_deduplication_returns_existing():
    """Same failure signature → existing open ticket returned, not a new one."""
    first = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Same error",
        description="Dup bug",
        scenario_id="sc-1",
        error_class="TimeoutError",
        locator="#btn",
    )
    second = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Same error again",
        description="Dup bug again",
        scenario_id="sc-1",
        error_class="TimeoutError",
        locator="#btn",
    )
    assert first.id == second.id
    assert len(svc.list_defects()) == 1


def test_open_defect_with_auto_jira_sets_external_ref():
    defect = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Jira bug",
        description="Needs tracking",
        auto_jira=True,
    )
    assert defect.external_ref is not None
    assert defect.external_ref.startswith("NEUREX-")
    assert defect.external_url is not None


# ── get_defect ────────────────────────────────────────────────────────────


def test_get_defect_returns_none_when_not_found():
    """get_defect returns None (not KeyError) for unknown IDs."""
    result = svc.get_defect("def-nonexistent")
    assert result is None


# ── list_defects ──────────────────────────────────────────────────────────


def test_list_defects_project_filter():
    svc.open_defect_from_execution(
        project_id="proj-alpha",
        title="Alpha bug",
        description="Bug in alpha",
    )
    svc.open_defect_from_execution(
        project_id="proj-beta",
        title="Beta bug",
        description="Bug in beta",
    )
    alpha_defects = svc.list_defects(project_id="proj-alpha")
    assert len(alpha_defects) == 1
    assert alpha_defects[0].project_id == "proj-alpha"


def test_list_defects_status_filter():
    d1 = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Open bug",
        description="Still open",
        error_class="TypeError",
        locator="#a",
    )
    d2 = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Another bug",
        description="Will be merged",
        error_class="ValueError",
        locator="#b",
    )
    svc.mark_fix_merged(d2.id, commit_sha="abc123def456")

    verifying = svc.list_defects(status="verifying")
    assert any(d.id == d2.id for d in verifying)
    awaiting = svc.list_defects(status="awaiting_fix")
    assert any(d.id == d1.id for d in awaiting)


# ── mark_fix_merged ───────────────────────────────────────────────────────


def test_mark_fix_merged_transitions_to_verifying():
    defect = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Regression",
        description="Bug details",
    )
    updated = svc.mark_fix_merged(defect.id, commit_sha="deadbeef1234")
    assert updated.fix_commit == "deadbeef1234"
    assert updated.status == "verifying"


def test_mark_fix_merged_raises_for_unknown_id():
    with pytest.raises(ValueError, match="Defect bulunamadı"):
        svc.mark_fix_merged("def-unknown", commit_sha="abc")


def test_mark_fix_merged_noop_when_already_closed():
    defect = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Old bug",
        description="Already fixed",
        error_class="OldError",
        locator="#x",
    )
    svc.mark_fix_merged(defect.id, commit_sha="sha1")
    svc.verify_and_close(defect.id, rerun_id="run-1", rerun_passed=True)

    # Now try to mark merged again — should not raise, just return as-is
    result = svc.mark_fix_merged(defect.id, commit_sha="sha2")
    assert result.status == "closed"


# ── verify_fix / verify_and_close ─────────────────────────────────────────


def test_verify_and_close_passed_closes_defect():
    defect = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Flaky login",
        description="Login fails intermittently",
        error_class="FlakeError",
        locator="#login-btn",
    )
    svc.mark_fix_merged(defect.id, commit_sha="fixsha")
    closed = svc.verify_and_close(defect.id, rerun_id="rerun-99", rerun_passed=True)
    assert closed.status == "closed"
    assert closed.rerun_id == "rerun-99"


def test_verify_and_close_failed_reverts_to_awaiting_fix():
    defect = svc.open_defect_from_execution(
        project_id="proj-1",
        title="Persistent bug",
        description="Still failing after fix",
        error_class="AssertionError",
        locator="#footer",
    )
    svc.mark_fix_merged(defect.id, commit_sha="badfix")
    result = svc.verify_and_close(defect.id, rerun_id="rerun-100", rerun_passed=False)
    assert result.status == "awaiting_fix"


def test_verify_and_close_raises_for_unknown_id():
    with pytest.raises(ValueError, match="Defect bulunamadı"):
        svc.verify_and_close("def-ghost", rerun_id="run-0", rerun_passed=True)
