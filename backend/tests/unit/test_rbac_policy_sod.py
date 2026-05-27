"""Unit tests for app.domains.rbac.policy — RBAC and Segregation of Duties.

Tests are fully self-contained: no DB, no HTTP.
Covers: ROLES, role_permissions, has_permission, find_rules_for,
enforce_sod (clean pass, violation), SoDViolation, sod_http_detail.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from unittest.mock import MagicMock

try:
    from app.domains.rbac.policy import (
        ROLES,
        SOD_RULES,
        role_permissions,
        has_permission,
        find_rules_for,
        enforce_sod,
        sod_http_detail,
        SoDViolation,
        SoDRule,
        ActorAction,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="rbac.policy import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audit_store(recent: list = None):
    """Fake audit store that returns the given recent actions."""
    store = MagicMock()
    store.actor_recent_actions.return_value = recent or []
    return store


def _make_action(action: str, days_ago: int = 1) -> ActorAction:
    return ActorAction(
        action=action,
        resource_type="prompt",
        resource_id="res-1",
        tenant_id="tenant-1",
        ts=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )


# ---------------------------------------------------------------------------
# ROLES structure
# ---------------------------------------------------------------------------

class TestRoles:
    def test_roles_has_expected_roles(self):
        for role in ("viewer", "test_author", "reviewer", "ops", "auditor", "admin"):
            assert role in ROLES

    def test_each_role_has_set_of_strings(self):
        for role, perms in ROLES.items():
            assert isinstance(perms, set)
            for p in perms:
                assert isinstance(p, str)

    def test_admin_has_wildcard(self):
        assert "admin.*" in ROLES["admin"]

    def test_viewer_has_read_permissions(self):
        assert any("read" in p for p in ROLES["viewer"])


# ---------------------------------------------------------------------------
# role_permissions
# ---------------------------------------------------------------------------

class TestRolePermissions:
    def test_single_role_returns_its_perms(self):
        result = role_permissions(["viewer"])
        assert "tspm.read" in result

    def test_multiple_roles_unioned(self):
        result = role_permissions(["viewer", "test_author"])
        # test_author has write permissions viewer doesn't
        assert "tspm.write" in result
        assert "tspm.read" in result

    def test_unknown_role_ignored(self):
        result = role_permissions(["nonexistent_role"])
        assert result == set()

    def test_empty_roles_empty_set(self):
        result = role_permissions([])
        assert result == set()

    def test_returns_set(self):
        assert isinstance(role_permissions(["viewer"]), set)

    def test_admin_role_has_wildcard(self):
        perms = role_permissions(["admin"])
        assert "admin.*" in perms


# ---------------------------------------------------------------------------
# has_permission
# ---------------------------------------------------------------------------

class TestHasPermission:
    def test_exact_match_returns_true(self):
        perms = {"tspm.read", "ai.generate"}
        assert has_permission(perms, "tspm.read") is True

    def test_missing_permission_returns_false(self):
        perms = {"tspm.read"}
        assert has_permission(perms, "admin.evals") is False

    def test_admin_wildcard_covers_any_permission(self):
        perms = {"admin.*"}
        assert has_permission(perms, "any.permission.at.all") is True

    def test_empty_perms_returns_false(self):
        assert has_permission(set(), "tspm.read") is False

    def test_returns_bool(self):
        assert isinstance(has_permission({"tspm.read"}, "tspm.read"), bool)


# ---------------------------------------------------------------------------
# find_rules_for
# ---------------------------------------------------------------------------

class TestFindRulesFor:
    def test_returns_rules_for_known_action(self):
        rules = find_rules_for("prompt.approve")
        assert len(rules) > 0
        for r in rules:
            assert r.new_action == "prompt.approve"

    def test_returns_empty_for_unknown_action(self):
        rules = find_rules_for("nonexistent.action.xyz")
        assert rules == []

    def test_returns_list_of_sod_rules(self):
        rules = find_rules_for("prompt.rollout.promote")
        for r in rules:
            assert isinstance(r, SoDRule)


# ---------------------------------------------------------------------------
# enforce_sod
# ---------------------------------------------------------------------------

class TestEnforceSod:
    def test_no_rules_for_action_passes_silently(self):
        store = _make_audit_store()
        # Action with no SoD rules
        enforce_sod(
            audit_store=store,
            actor_user_id="user-1",
            new_action="no.sod.rules.action",
        )
        # Should not call the store at all
        store.actor_recent_actions.assert_not_called()

    def test_empty_actor_raises_sod_violation(self):
        store = _make_audit_store()
        with pytest.raises(SoDViolation):
            enforce_sod(
                audit_store=store,
                actor_user_id="",
                new_action="prompt.approve",
            )

    def test_no_conflicting_action_passes(self):
        store = _make_audit_store(recent=[])  # no recent conflicts
        enforce_sod(
            audit_store=store,
            actor_user_id="user-1",
            new_action="prompt.approve",
            resource_type="prompt",
            resource_id="prompt-1",
        )
        # Passes without exception

    def test_conflicting_action_raises_sod_violation(self):
        conflicting = _make_action("prompt.version.create", days_ago=5)
        store = _make_audit_store(recent=[conflicting])
        with pytest.raises(SoDViolation) as exc_info:
            enforce_sod(
                audit_store=store,
                actor_user_id="user-1",
                new_action="prompt.approve",
                resource_type="prompt",
                resource_id="prompt-1",
            )
        assert "prompt_author_vs_approver" in str(exc_info.value)

    def test_violation_contains_rule_and_conflicting(self):
        conflicting = _make_action("prompt.version.create", days_ago=3)
        store = _make_audit_store(recent=[conflicting])
        try:
            enforce_sod(
                audit_store=store,
                actor_user_id="user-1",
                new_action="prompt.approve",
            )
            pytest.fail("SoDViolation not raised")
        except SoDViolation as exc:
            assert exc.rule is not None
            assert exc.conflicting is not None

    def test_audit_store_queried_with_correct_action(self):
        store = _make_audit_store(recent=[])
        enforce_sod(
            audit_store=store,
            actor_user_id="user-1",
            new_action="prompt.approve",
        )
        call_kwargs = store.actor_recent_actions.call_args.kwargs
        assert "prompt.version.create" in call_kwargs["actions"]

    def test_resource_scoped_rule_passes_resource_id(self):
        store = _make_audit_store(recent=[])
        enforce_sod(
            audit_store=store,
            actor_user_id="user-1",
            new_action="prompt.approve",
            resource_type="prompt",
            resource_id="prompt-42",
        )
        call_kwargs = store.actor_recent_actions.call_args.kwargs
        assert call_kwargs["resource_id"] == "prompt-42"

    def test_tenant_scoped_rule_passes_tenant_not_resource(self):
        store = _make_audit_store(recent=[])
        enforce_sod(
            audit_store=store,
            actor_user_id="user-1",
            new_action="ai.budget.bypass",
            tenant_id="tenant-99",
        )
        call_kwargs = store.actor_recent_actions.call_args.kwargs
        assert call_kwargs["tenant_id"] == "tenant-99"
        # Resource id should be None for tenant-scoped
        assert call_kwargs.get("resource_id") is None


# ---------------------------------------------------------------------------
# SoDViolation exception
# ---------------------------------------------------------------------------

class TestSoDViolation:
    def test_message_contains_rule_name(self):
        rule = SoDRule(
            name="my_rule",
            new_action="action.to.do",
            conflicting_actions=("conflicting.action",),
        )
        conflict = _make_action("conflicting.action")
        exc = SoDViolation(rule=rule, conflicting=conflict)
        assert "my_rule" in str(exc)

    def test_has_rule_attribute(self):
        rule = SOD_RULES[0]
        conflict = _make_action(rule.conflicting_actions[0])
        exc = SoDViolation(rule=rule, conflicting=conflict)
        assert exc.rule is rule

    def test_has_conflicting_attribute(self):
        rule = SOD_RULES[0]
        conflict = _make_action(rule.conflicting_actions[0])
        exc = SoDViolation(rule=rule, conflicting=conflict)
        assert exc.conflicting is conflict


# ---------------------------------------------------------------------------
# sod_http_detail
# ---------------------------------------------------------------------------

class TestSodHttpDetail:
    def test_returns_dict(self):
        rule = SOD_RULES[0]
        conflict = _make_action(rule.conflicting_actions[0])
        exc = SoDViolation(rule=rule, conflicting=conflict)
        detail = sod_http_detail(exc)
        assert isinstance(detail, dict)

    def test_has_required_keys(self):
        rule = SOD_RULES[0]
        conflict = _make_action(rule.conflicting_actions[0])
        exc = SoDViolation(rule=rule, conflicting=conflict)
        detail = sod_http_detail(exc)
        assert "error" in detail
        assert "rule" in detail
        assert "message" in detail
        assert "conflicting_action" in detail
        assert "conflicting_ts" in detail

    def test_error_is_sod_violation(self):
        rule = SOD_RULES[0]
        conflict = _make_action(rule.conflicting_actions[0])
        exc = SoDViolation(rule=rule, conflicting=conflict)
        detail = sod_http_detail(exc)
        assert detail["error"] == "sod_violation"
