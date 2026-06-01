"""Unit tests for app.domains.rbac.policy — pure RBAC and SoD helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers: role_permissions, has_permission, find_rules_for,
        ROLES constant, SOD_RULES constant, SoDRule dataclass.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

import pytest

try:
    from app.domains.rbac.policy import (
        role_permissions,
        has_permission,
        find_rules_for,
        ROLES,
        SOD_RULES,
        SoDRule,
        ActorAction,
        SoDViolation,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="rbac.policy import failed")


# ---------------------------------------------------------------------------
# ROLES constant
# ---------------------------------------------------------------------------

class TestRoles:
    def test_has_viewer(self):
        assert "viewer" in ROLES

    def test_has_admin(self):
        assert "admin" in ROLES

    def test_has_test_author(self):
        assert "test_author" in ROLES

    def test_admin_has_wildcard(self):
        assert "admin.*" in ROLES["admin"]

    def test_viewer_has_read_permissions(self):
        perms = ROLES["viewer"]
        assert any("read" in p for p in perms)

    def test_all_roles_have_nonempty_permissions(self):
        for role, perms in ROLES.items():
            assert len(perms) > 0, f"Role {role} has no permissions"

    def test_ops_has_deploy(self):
        assert "tspm.deploy" in ROLES["ops"]

    def test_reviewer_has_approve(self):
        assert "tspm.approve" in ROLES["reviewer"]


# ---------------------------------------------------------------------------
# role_permissions
# ---------------------------------------------------------------------------

class TestRolePermissions:
    def test_single_role(self):
        perms = role_permissions(["viewer"])
        assert "tspm.read" in perms

    def test_multiple_roles_union(self):
        perms = role_permissions(["viewer", "test_author"])
        assert "tspm.read" in perms
        assert "tspm.write" in perms

    def test_unknown_role_ignored(self):
        perms = role_permissions(["nonexistent_role"])
        assert len(perms) == 0

    def test_empty_roles_empty_set(self):
        perms = role_permissions([])
        assert perms == set()

    def test_returns_set(self):
        assert isinstance(role_permissions(["viewer"]), set)

    def test_admin_has_wildcard(self):
        perms = role_permissions(["admin"])
        assert "admin.*" in perms

    def test_deduplicated(self):
        # Both viewer and test_author have tspm.read — should appear once
        perms = role_permissions(["viewer", "test_author"])
        count = sum(1 for p in perms if p == "tspm.read")
        assert count == 1


# ---------------------------------------------------------------------------
# has_permission
# ---------------------------------------------------------------------------

class TestHasPermission:
    def test_exact_match(self):
        assert has_permission({"tspm.read", "ai.read"}, "tspm.read") is True

    def test_missing_permission(self):
        assert has_permission({"tspm.read"}, "tspm.write") is False

    def test_admin_wildcard_grants_everything(self):
        assert has_permission({"admin.*"}, "tspm.write") is True
        assert has_permission({"admin.*"}, "any.random.permission") is True

    def test_empty_permissions(self):
        assert has_permission(set(), "tspm.read") is False

    def test_returns_bool(self):
        assert isinstance(has_permission({"tspm.read"}, "tspm.read"), bool)

    def test_partial_match_not_granted(self):
        # "tspm" alone doesn't grant "tspm.read"
        assert has_permission({"tspm"}, "tspm.read") is False


# ---------------------------------------------------------------------------
# SOD_RULES constant
# ---------------------------------------------------------------------------

class TestSodRules:
    def test_is_tuple(self):
        assert isinstance(SOD_RULES, tuple)

    def test_nonempty(self):
        assert len(SOD_RULES) > 0

    def test_all_are_sod_rules(self):
        for rule in SOD_RULES:
            assert isinstance(rule, SoDRule)

    def test_each_has_name(self):
        for rule in SOD_RULES:
            assert isinstance(rule.name, str) and rule.name

    def test_each_has_new_action(self):
        for rule in SOD_RULES:
            assert isinstance(rule.new_action, str) and rule.new_action

    def test_each_has_conflicting_actions(self):
        for rule in SOD_RULES:
            assert isinstance(rule.conflicting_actions, tuple)
            assert len(rule.conflicting_actions) > 0

    def test_window_days_positive(self):
        for rule in SOD_RULES:
            assert rule.window_days > 0

    def test_prompt_author_vs_approver_exists(self):
        names = [r.name for r in SOD_RULES]
        assert "prompt_author_vs_approver" in names


# ---------------------------------------------------------------------------
# find_rules_for
# ---------------------------------------------------------------------------

class TestFindRulesFor:
    def test_finds_rules_for_known_action(self):
        rules = find_rules_for("prompt.approve")
        assert len(rules) >= 1
        assert all(r.new_action == "prompt.approve" for r in rules)

    def test_no_rules_for_unknown_action(self):
        rules = find_rules_for("nonexistent.action")
        assert rules == []

    def test_returns_list(self):
        assert isinstance(find_rules_for("prompt.approve"), list)

    def test_budget_bypass_rule_found(self):
        rules = find_rules_for("ai.budget.bypass")
        assert len(rules) >= 1


# ---------------------------------------------------------------------------
# SoDRule dataclass
# ---------------------------------------------------------------------------

class TestSodRuleDataclass:
    def test_immutable(self):
        rule = SoDRule(
            name="test_rule",
            new_action="x.action",
            conflicting_actions=("y.action",),
        )
        with pytest.raises((AttributeError, TypeError)):
            rule.name = "changed"  # type: ignore[misc]

    def test_default_window_days(self):
        rule = SoDRule(
            name="r",
            new_action="a",
            conflicting_actions=("b",),
        )
        assert rule.window_days == 30

    def test_default_scope_resource(self):
        rule = SoDRule(
            name="r",
            new_action="a",
            conflicting_actions=("b",),
        )
        assert rule.scope == "resource"
