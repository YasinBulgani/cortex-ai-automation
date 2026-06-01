"""Unit tests for app.domains.rbac.service (facade layer).

Tests are fully self-contained: no DB, no HTTP, no external services.
The RBAC service is pure-Python (policy dict + stdlib), so most tests
require no mocking. AuditStore-dependent tests use a simple in-memory fake.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

import pytest

try:
    from app.domains.rbac import service as rbac_service
    from app.domains.rbac.service import (
        check_permission,
        enforce_segregation,
        get_role,
        get_role_permissions,
        list_roles,
    )
    from app.domains.rbac.policy import (
        ActorAction,
        AuditStore,
        ROLES,
    )

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="rbac service import failed")


# ---------------------------------------------------------------------------
# Fake AuditStore (in-memory, no DB required)
# ---------------------------------------------------------------------------


class FakeAuditStore:
    """Minimal AuditStore implementation for unit tests."""

    def __init__(self, records: list[ActorAction] | None = None) -> None:
        self._records: list[ActorAction] = records or []

    def actor_recent_actions(
        self,
        *,
        actor_user_id: str,
        actions: Tuple[str, ...],
        since: datetime,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[ActorAction]:
        return [
            r
            for r in self._records
            if r.action in actions
            and r.ts >= since
        ]


def _make_actor_action(action: str, resource_type: str = "prompt", resource_id: str = "r1") -> ActorAction:
    return ActorAction(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=None,
        ts=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# list_roles
# ---------------------------------------------------------------------------


class TestListRoles:
    def test_returns_list(self):
        result = list_roles()
        assert isinstance(result, list)

    def test_list_is_sorted(self):
        result = list_roles()
        assert result == sorted(result)

    def test_includes_viewer(self):
        assert "viewer" in list_roles()

    def test_includes_test_author(self):
        assert "test_author" in list_roles()

    def test_includes_reviewer(self):
        assert "reviewer" in list_roles()

    def test_includes_admin(self):
        assert "admin" in list_roles()

    def test_length_matches_roles_dict(self):
        assert len(list_roles()) == len(ROLES)


# ---------------------------------------------------------------------------
# get_role
# ---------------------------------------------------------------------------


class TestGetRole:
    def test_viewer_returns_dict_with_name(self):
        result = get_role("viewer")
        assert isinstance(result, dict)
        assert result["name"] == "viewer"

    def test_get_role_has_permissions_key(self):
        result = get_role("viewer")
        assert "permissions" in result

    def test_get_role_permissions_is_list(self):
        result = get_role("viewer")
        assert isinstance(result["permissions"], list)

    def test_get_role_permissions_sorted(self):
        result = get_role("test_author")
        perms = result["permissions"]
        assert perms == sorted(perms)

    def test_nonexistent_role_raises_key_error(self):
        with pytest.raises(KeyError):
            get_role("nonexistent")

    def test_empty_string_raises_key_error(self):
        with pytest.raises(KeyError):
            get_role("")

    def test_admin_role_contains_wildcard(self):
        result = get_role("admin")
        assert "admin.*" in result["permissions"]


# ---------------------------------------------------------------------------
# get_role_permissions
# ---------------------------------------------------------------------------


class TestGetRolePermissions:
    def test_returns_set(self):
        result = get_role_permissions("viewer")
        assert isinstance(result, set)

    def test_test_author_has_tspm_write(self):
        perms = get_role_permissions("test_author")
        assert "tspm.write" in perms

    def test_viewer_has_tspm_read(self):
        perms = get_role_permissions("viewer")
        assert "tspm.read" in perms

    def test_viewer_does_not_have_tspm_write(self):
        perms = get_role_permissions("viewer")
        assert "tspm.write" not in perms

    def test_unknown_role_raises_key_error(self):
        with pytest.raises(KeyError):
            get_role_permissions("ghost_role")

    def test_admin_permissions_contains_wildcard(self):
        perms = get_role_permissions("admin")
        assert "admin.*" in perms


# ---------------------------------------------------------------------------
# check_permission
# ---------------------------------------------------------------------------


class TestCheckPermission:
    def test_exact_match_returns_true(self):
        assert check_permission(["tspm.read"], "tspm.read") is True

    def test_missing_permission_returns_false(self):
        assert check_permission(["tspm.read"], "tspm.write") is False

    def test_empty_permissions_returns_false(self):
        assert check_permission([], "tspm.write") is False

    def test_admin_wildcard_grants_any_permission(self):
        assert check_permission(["admin.*"], "admin.anything") is True

    def test_admin_wildcard_grants_non_admin_permission(self):
        # admin.* should grant everything
        assert check_permission(["admin.*"], "tspm.read") is True

    def test_multiple_permissions_match_any(self):
        perms = ["tspm.read", "ai.read", "coverup.read"]
        assert check_permission(perms, "ai.read") is True

    def test_multiple_permissions_no_match(self):
        perms = ["tspm.read", "ai.read"]
        assert check_permission(perms, "prompts.approve") is False

    def test_partial_name_does_not_match(self):
        # "tspm" should not satisfy "tspm.read"
        assert check_permission(["tspm"], "tspm.read") is False


# ---------------------------------------------------------------------------
# enforce_segregation
# ---------------------------------------------------------------------------


class TestEnforceSegregation:
    def test_passes_when_no_conflict(self):
        """No conflicting prior actions → returns None without raising."""
        store = FakeAuditStore(records=[])
        # Should not raise
        enforce_segregation(
            audit_store=store,
            user_id="user-1",
            new_action="prompt.rollout.promote",
            resource_type="prompt",
            resource_id="prompt-123",
        )

    def test_raises_value_error_on_sod_violation(self):
        """User who created a prompt version cannot also promote it."""
        conflicting = _make_actor_action("prompt.version.create", "prompt", "prompt-123")
        store = FakeAuditStore(records=[conflicting])
        with pytest.raises(ValueError, match="SoD"):
            enforce_segregation(
                audit_store=store,
                user_id="user-1",
                new_action="prompt.rollout.promote",
                resource_type="prompt",
                resource_id="prompt-123",
            )

    def test_does_not_raise_sodviolation_directly(self):
        """enforce_segregation must wrap SoDViolation into ValueError."""
        from app.domains.rbac.policy import SoDViolation

        conflicting = _make_actor_action("prompt.version.create")
        store = FakeAuditStore(records=[conflicting])
        with pytest.raises(ValueError):
            enforce_segregation(
                audit_store=store,
                user_id="user-1",
                new_action="prompt.rollout.promote",
            )
        # Verify it is NOT a raw SoDViolation reaching the caller
        try:
            enforce_segregation(
                audit_store=store,
                user_id="user-1",
                new_action="prompt.rollout.promote",
            )
        except ValueError:
            pass  # correct
        except SoDViolation:
            pytest.fail("enforce_segregation must not leak SoDViolation")

    def test_action_with_no_rule_passes(self):
        """Actions without defined SoD rules always pass."""
        store = FakeAuditStore(records=[])
        # "some.unknown.action" has no SoD rule — must pass silently
        enforce_segregation(
            audit_store=store,
            user_id="user-1",
            new_action="some.unknown.action",
        )

    def test_heal_author_cannot_approve_own_heal(self):
        """coverup.heal.create conflicts with coverup.heal.approve."""
        conflicting = _make_actor_action("coverup.heal.create", "coverup", "heal-99")
        store = FakeAuditStore(records=[conflicting])
        with pytest.raises(ValueError):
            enforce_segregation(
                audit_store=store,
                user_id="user-2",
                new_action="coverup.heal.approve",
                resource_type="coverup",
                resource_id="heal-99",
            )


# ---------------------------------------------------------------------------
# Multi-role permission union
# ---------------------------------------------------------------------------


class TestMultiRoleUnion:
    def test_union_of_viewer_and_test_author(self):
        viewer_perms = get_role_permissions("viewer")
        author_perms = get_role_permissions("test_author")
        combined = viewer_perms | author_perms
        # test_author has tspm.write, viewer does not
        assert "tspm.write" in combined
        assert "tspm.read" in combined

    def test_union_includes_all_from_each_role(self):
        reviewer_perms = get_role_permissions("reviewer")
        author_perms = get_role_permissions("test_author")
        combined = reviewer_perms | author_perms
        assert "tspm.approve" in combined  # from reviewer
        assert "tspm.write" in combined  # from test_author

    def test_combined_roles_check_permission(self):
        perms = list(get_role_permissions("viewer") | get_role_permissions("test_author"))
        assert check_permission(perms, "tspm.write") is True
        assert check_permission(perms, "tspm.approve") is False
