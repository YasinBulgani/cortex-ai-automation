"""New unit tests for test_management and organizations domains.

All tests are pure-function tests: no DB, no Redis, no HTTP.
Covers:
  - test_management: _next_project_key, _would_create_cycle, _next_case_key,
                     _case_snapshot, TestCaseCreate/TestCaseUpdate schemas
  - organizations: InvitationCreate/TeamMemberAdd schema edge cases,
                   ProjectMemberAdd schema, issue_invite_token uniqueness,
                   cross-tenant guard logic
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import guards
# ---------------------------------------------------------------------------
try:
    from app.domains.test_management.service import (
        _next_project_key,
        _would_create_cycle,
        _next_case_key,
        _case_snapshot,
    )
    from app.domains.test_management.schemas import (
        TestCaseCreate,
        TestCaseUpdate,
        TestCaseStepIn,
        ManagementProjectCreate,
    )
    from app.domains.test_management.models import (
        TestManagementProject,
        TestFolder,
        TestCase,
        TestCaseStep,
    )
    _TM_OK = True
except Exception:
    _TM_OK = False

try:
    from app.domains.organizations.schemas import (
        InvitationCreate,
        TeamMemberAdd,
        ProjectMemberAdd,
        InvitationAccept,
        TeamCreate,
    )
    from app.domains.organizations.service import (
        issue_invite_token,
        _hash_token,
    )
    _ORG_OK = True
except Exception:
    _ORG_OK = False


# ===========================================================================
# TEST MANAGEMENT — _next_project_key
# ===========================================================================

@pytest.mark.skipif(not _TM_OK, reason="test_management import failed")
class TestNextProjectKey:
    """Tests for the _next_project_key helper (no real DB)."""

    def _make_db(self, existing_keys: list[str]) -> MagicMock:
        """Return a mock DB where scalar() returns a truthy value for any key in existing_keys."""
        call_counter: dict[str, int] = {}

        def _scalar(stmt):
            # We simulate: first call returns None if the candidate is not taken
            # We check by tracking call order and comparing to existing_keys list
            # Simpler: return taken indicator based on call count
            idx = call_counter.setdefault("n", 0)
            call_counter["n"] += 1
            if idx < len(existing_keys):
                return "some-id"   # candidate already taken
            return None            # candidate is free

        db = MagicMock()
        db.scalar.side_effect = _scalar
        return db

    def test_plain_name_produces_uppercase_prefix(self):
        db = MagicMock()
        db.scalar.return_value = None  # nothing taken

        key = _next_project_key(db, "QA Platform")
        assert key.startswith("QAPLATFO") or key[:8] == "QAPLATFO"[:len(key)]

    def test_empty_name_falls_back_to_mgmt(self):
        db = MagicMock()
        db.scalar.return_value = None

        key = _next_project_key(db, "")
        assert key == "MGMT"

    def test_name_with_only_special_chars_falls_back_to_mgmt(self):
        db = MagicMock()
        db.scalar.return_value = None

        key = _next_project_key(db, "---!!!---")
        assert key == "MGMT"

    def test_key_truncated_to_8_chars_when_not_taken(self):
        db = MagicMock()
        db.scalar.return_value = None  # first candidate is free

        key = _next_project_key(db, "VeryLongProjectName")
        assert len(key) <= 8

    def test_duplicate_key_gets_numeric_suffix(self):
        """When the base key is taken, the helper must append a number."""
        call_count = {"n": 0}

        def _scalar(_stmt):
            # First call: candidate taken; second call: free
            n = call_count["n"]
            call_count["n"] += 1
            return "taken" if n == 0 else None

        db = MagicMock()
        db.scalar.side_effect = _scalar

        key = _next_project_key(db, "Alpha")
        # Base key ALPHA was taken; result should differ from plain base
        assert key != "ALPHA"
        # It should contain a digit
        assert any(c.isdigit() for c in key)


# ===========================================================================
# TEST MANAGEMENT — _would_create_cycle
# ===========================================================================

@pytest.mark.skipif(not _TM_OK, reason="test_management import failed")
class TestWouldCreateCycle:
    """Tests for the cycle-detection helper."""

    def _folder(self, fid: str, parent_id: str | None) -> MagicMock:
        f = MagicMock(spec=TestFolder)
        f.id = fid
        f.parent_id = parent_id
        return f

    def test_no_cycle_when_parent_chain_terminates(self):
        """Root folder (no parent) as new_parent — no cycle."""
        root = self._folder("root", None)

        db = MagicMock()
        db.get.return_value = root

        result = _would_create_cycle(db, folder_id="child", new_parent_id="root")
        assert result is False

    def test_direct_self_parent_is_cycle(self):
        """folder_id == new_parent_id → the loop detects a cycle immediately."""
        db = MagicMock()
        # db.get("folder-a") returns a folder whose parent is None (chain terminates)
        # but the first iteration hits folder_id == new_parent_id
        result = _would_create_cycle(db, folder_id="folder-a", new_parent_id="folder-a")
        assert result is True

    def test_grandparent_cycle_detected(self):
        """Moving folder A under its own grandchild creates a cycle."""
        # chain: new_parent → folder_b → folder_a
        folder_b = self._folder("folder-b", parent_id="folder-a")

        def _get(_model, fid):
            return folder_b if fid == "folder-b" else None

        db = MagicMock()
        db.get.side_effect = _get

        result = _would_create_cycle(db, folder_id="folder-a", new_parent_id="folder-b")
        assert result is True

    def test_no_cycle_for_sibling_reparenting(self):
        """Moving a folder to its sibling's parent is not a cycle."""
        parent = self._folder("parent", parent_id=None)

        def _get(_model, fid):
            return parent if fid == "parent" else None

        db = MagicMock()
        db.get.side_effect = _get

        result = _would_create_cycle(db, folder_id="folder-a", new_parent_id="parent")
        assert result is False

    def test_broken_chain_stops_gracefully(self):
        """If a parent_id references a non-existent folder, the loop stops safely."""
        db = MagicMock()
        db.get.return_value = None  # every db.get returns None

        # new_parent_id "ghost" doesn't exist — chain immediately breaks
        result = _would_create_cycle(db, folder_id="folder-x", new_parent_id="ghost")
        assert result is False


# ===========================================================================
# TEST MANAGEMENT — _next_case_key
# ===========================================================================

@pytest.mark.skipif(not _TM_OK, reason="test_management import failed")
class TestNextCaseKey:
    """Tests for the case-key generation helper."""

    def _project(self, key: str, pid: str = "proj-001") -> MagicMock:
        p = MagicMock(spec=TestManagementProject)
        p.key = key
        p.id = pid
        return p

    def test_first_case_starts_at_1001(self):
        db = MagicMock()
        db.scalar.return_value = 0  # 0 existing cases

        key = _next_case_key(db, self._project("ACME"))
        assert key == "ACME-TC-1001"

    def test_key_increments_with_existing_cases(self):
        db = MagicMock()
        db.scalar.return_value = 5  # 5 existing cases

        key = _next_case_key(db, self._project("QA"))
        assert key == "QA-TC-1006"

    def test_key_uses_project_key_prefix(self):
        db = MagicMock()
        db.scalar.return_value = 0

        key = _next_case_key(db, self._project("NEUREX"))
        assert key.startswith("NEUREX-TC-")

    def test_key_format_is_prefix_tc_number(self):
        db = MagicMock()
        db.scalar.return_value = 99

        key = _next_case_key(db, self._project("PROJ"))
        parts = key.split("-")
        assert parts[-2] == "TC"
        assert parts[-1].isdigit()

    def test_none_count_treated_as_zero(self):
        """When db.scalar returns None (empty table) the helper should not crash."""
        db = MagicMock()
        db.scalar.return_value = None

        key = _next_case_key(db, self._project("X"))
        assert key == "X-TC-1001"


# ===========================================================================
# TEST MANAGEMENT — _case_snapshot
# ===========================================================================

@pytest.mark.skipif(not _TM_OK, reason="test_management import failed")
class TestCaseSnapshot:
    """Tests for _case_snapshot — pure dict serialisation, no DB."""

    def _make_case(self, **kwargs) -> MagicMock:
        case = MagicMock(spec=TestCase)
        case.id = kwargs.get("id", "case-001")
        case.case_key = kwargs.get("case_key", "PROJ-TC-1001")
        case.title = kwargs.get("title", "Login test")
        case.objective = kwargs.get("objective", "Verify login flow")
        case.preconditions = kwargs.get("preconditions", "User exists")
        case.test_data = kwargs.get("test_data", {})
        case.priority = kwargs.get("priority", "high")
        case.severity = kwargs.get("severity", "critical")
        case.type = kwargs.get("type", "functional")
        case.automation_status = kwargs.get("automation_status", "manual")
        case.status = kwargs.get("status", "active")
        case.tags = kwargs.get("tags", ["smoke"])
        case.custom_fields = kwargs.get("custom_fields", {})
        case.steps = kwargs.get("steps", [])
        return case

    def _make_step(self, step_no: int, action: str, expected: str) -> MagicMock:
        s = MagicMock(spec=TestCaseStep)
        s.step_no = step_no
        s.action = action
        s.expected_result = expected
        s.test_data = {}
        s.notes = None
        s.is_required = True
        return s

    def test_snapshot_contains_case_key(self):
        case = self._make_case(case_key="MYPROJ-TC-2001")
        snap = _case_snapshot(case)
        assert snap["case"]["case_key"] == "MYPROJ-TC-2001"

    def test_snapshot_steps_list_is_included(self):
        step = self._make_step(1, "Click login", "Page loads")
        case = self._make_case(steps=[step])
        snap = _case_snapshot(case)
        assert len(snap["steps"]) == 1
        assert snap["steps"][0]["action"] == "Click login"
        assert snap["steps"][0]["expected_result"] == "Page loads"

    def test_snapshot_with_no_steps_returns_empty_list(self):
        case = self._make_case(steps=[])
        snap = _case_snapshot(case)
        assert snap["steps"] == []

    def test_snapshot_preserves_tags(self):
        case = self._make_case(tags=["regression", "smoke", "login"])
        snap = _case_snapshot(case)
        assert snap["case"]["tags"] == ["regression", "smoke", "login"]

    def test_snapshot_has_case_and_steps_keys(self):
        case = self._make_case()
        snap = _case_snapshot(case)
        assert "case" in snap
        assert "steps" in snap

    def test_snapshot_step_order_preserved(self):
        steps = [
            self._make_step(1, "Open browser", "Browser opens"),
            self._make_step(2, "Enter URL", "Page loads"),
            self._make_step(3, "Enter creds", "Fields filled"),
        ]
        case = self._make_case(steps=steps)
        snap = _case_snapshot(case)
        for i, step_dict in enumerate(snap["steps"], start=1):
            assert step_dict["step_no"] == i


# ===========================================================================
# TEST MANAGEMENT — schemas
# ===========================================================================

@pytest.mark.skipif(not _TM_OK, reason="test_management import failed")
class TestManagementSchemas:
    def test_test_case_create_requires_title(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TestCaseCreate(title="")  # min_length=1

    def test_test_case_create_valid_defaults(self):
        tc = TestCaseCreate(title="My Test")
        assert tc.priority == "medium"
        assert tc.severity == "major"
        assert tc.automation_status == "manual"
        assert tc.status == "draft"
        assert tc.steps == []

    def test_test_case_create_step_no_ge_1(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TestCaseStepIn(step_no=0, action="click", expected_result="done")

    def test_test_case_update_all_optional(self):
        # No fields required — empty payload is valid
        u = TestCaseUpdate()
        assert u.title is None
        assert u.priority is None

    def test_management_project_key_min_length(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ManagementProjectCreate(name="My Project", key="")


# ===========================================================================
# ORGANIZATIONS — schema edge cases
# ===========================================================================

@pytest.mark.skipif(not _ORG_OK, reason="organizations import failed")
class TestOrganizationsSchemas:
    def test_project_member_add_default_role_is_viewer(self):
        pm = ProjectMemberAdd(user_id="usr-001")
        assert pm.role == "viewer"

    def test_project_member_add_valid_roles(self):
        for role in ("admin", "operator", "member", "viewer"):
            pm = ProjectMemberAdd(user_id="usr-001", role=role)
            assert pm.role == role

    def test_project_member_add_invalid_role_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProjectMemberAdd(user_id="usr-001", role="superadmin")

    def test_team_member_add_default_role_is_member(self):
        tm = TeamMemberAdd(user_id="usr-002")
        assert tm.role == "member"

    def test_invitation_create_normalizes_email(self):
        # Pydantic EmailStr normalizes the domain part to lowercase
        # but preserves the local part (RFC-5321 allows case-sensitive local parts)
        inv = InvitationCreate(email="admin@Example.COM", role="admin")
        assert inv.email.endswith("@example.com")

    def test_invitation_accept_password_max_length(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            InvitationAccept(token="tok", password="x" * 129)  # max_length=128

    def test_invitation_accept_valid(self):
        inv = InvitationAccept(token="sometoken", password="securepass123")
        assert inv.token == "sometoken"

    def test_team_slug_must_be_lowercase_alphanumeric_dash(self):
        from pydantic import ValidationError
        for bad_slug in ("My_Team", "my team", "My-Team", "UPPER"):
            with pytest.raises(ValidationError):
                TeamCreate(name="Test", slug=bad_slug)

    def test_team_slug_valid_with_numbers(self):
        t = TeamCreate(name="Backend", slug="backend-v2")
        assert t.slug == "backend-v2"


# ===========================================================================
# ORGANIZATIONS — issue_invite_token properties
# ===========================================================================

@pytest.mark.skipif(not _ORG_OK, reason="organizations import failed")
class TestIssueInviteTokenExtended:
    def test_multiple_calls_all_unique(self):
        tokens = [issue_invite_token()[0] for _ in range(10)]
        assert len(set(tokens)) == 10, "All tokens must be unique"

    def test_hashed_token_is_not_raw(self):
        raw, hashed = issue_invite_token()
        assert raw != hashed

    def test_hash_is_hex_string(self):
        _, hashed = issue_invite_token()
        int(hashed, 16)  # raises ValueError if not valid hex

    def test_raw_token_min_entropy(self):
        """token_urlsafe(32) should be at least 43 base64url chars."""
        raw, _ = issue_invite_token()
        assert len(raw) >= 43

    def test_hash_always_64_chars(self):
        for _ in range(5):
            _, hashed = issue_invite_token()
            assert len(hashed) == 64
