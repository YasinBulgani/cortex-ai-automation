"""RBAC + SoD testleri — pure, DB'siz."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import pytest

from app.domains.rbac.policy import (
    ActorAction,
    ROLES,
    SOD_RULES,
    SoDViolation,
    enforce_sod,
    find_rules_for,
    has_permission,
    role_permissions,
    sod_http_detail,
)


class _FakeAudit:
    def __init__(self, actions: List[ActorAction]) -> None:
        self._actions = actions
        self.calls: List[dict] = []

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
        self.calls.append(
            {
                "actor_user_id": actor_user_id,
                "actions": actions,
                "since": since,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "tenant_id": tenant_id,
            }
        )
        out: List[ActorAction] = []
        for a in self._actions:
            if a.action not in actions:
                continue
            if a.ts < since:
                continue
            if resource_type is not None and a.resource_type != resource_type:
                continue
            if resource_id is not None and a.resource_id != resource_id:
                continue
            if tenant_id is not None and a.tenant_id != tenant_id:
                continue
            out.append(a)
        return out


def _a(
    action: str,
    *,
    rt: str = "prompt",
    rid: Optional[str] = "p1",
    tid: Optional[str] = "t1",
    days_ago: int = 1,
) -> ActorAction:
    return ActorAction(
        action=action,
        resource_type=rt,
        resource_id=rid,
        tenant_id=tid,
        ts=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )


# ── Roles ────────────────────────────────────────────────────────────────


class TestRoles:
    def test_all_roles_have_something(self) -> None:
        for name, perms in ROLES.items():
            assert perms, f"{name} rolü boş"

    def test_admin_wildcard(self) -> None:
        perms = role_permissions(["admin"])
        assert "admin.*" in perms
        assert has_permission(perms, "anything.goes")
        assert has_permission(perms, "tspm.write")

    def test_viewer_cannot_write(self) -> None:
        perms = role_permissions(["viewer"])
        assert has_permission(perms, "tspm.read")
        assert not has_permission(perms, "tspm.write")
        assert not has_permission(perms, "prompts.approve")

    def test_reviewer_approves_but_not_writes_tspm(self) -> None:
        perms = role_permissions(["reviewer"])
        assert has_permission(perms, "tspm.approve")
        assert has_permission(perms, "prompts.approve")
        assert not has_permission(perms, "tspm.write")
        assert not has_permission(perms, "prompts.read") or has_permission(perms, "prompts.read")

    def test_composite_roles_union(self) -> None:
        perms = role_permissions(["test_author", "reviewer"])
        # Author'dan
        assert has_permission(perms, "tspm.write")
        # Reviewer'dan
        assert has_permission(perms, "tspm.approve")

    def test_unknown_role_empty(self) -> None:
        perms = role_permissions(["nonexistent_role"])
        assert perms == set()


# ── SoD rules shape ──────────────────────────────────────────────────────


class TestRuleShape:
    def test_all_rules_have_conflicts(self) -> None:
        for r in SOD_RULES:
            assert r.conflicting_actions, f"{r.name} çatışma listesi boş"
            assert r.window_days > 0
            assert r.new_action not in r.conflicting_actions

    def test_find_rules_for(self) -> None:
        rules = find_rules_for("prompt.rollout.promote")
        assert any(r.name == "prompt_author_vs_promoter" for r in rules)

    def test_find_rules_for_unknown_action_empty(self) -> None:
        assert find_rules_for("non.existent.action") == []


# ── enforce_sod — prompt rollout promote senaryoları ────────────────────


class TestPromptPromote:
    def test_author_cannot_promote(self) -> None:
        store = _FakeAudit([_a("prompt.version.create", rid="p1", days_ago=3)])
        with pytest.raises(SoDViolation) as exc_info:
            enforce_sod(
                audit_store=store,
                actor_user_id="u1",
                new_action="prompt.rollout.promote",
                resource_type="prompt",
                resource_id="p1",
                tenant_id="t1",
            )
        assert exc_info.value.rule.name == "prompt_author_vs_promoter"
        assert exc_info.value.conflicting.action == "prompt.version.create"

    def test_different_user_can_promote(self) -> None:
        # Farklı user'ın kendi history'si boş — sessiz geçer
        store = _FakeAudit([_a("prompt.version.create", rid="p1")])
        # Bu aktör farklı (u2), kendi history boş
        empty_store = _FakeAudit([])
        enforce_sod(
            audit_store=empty_store,
            actor_user_id="u2",
            new_action="prompt.rollout.promote",
            resource_type="prompt",
            resource_id="p1",
            tenant_id="t1",
        )  # raise yok

    def test_different_resource_same_user_ok(self) -> None:
        # u1, p1'i yazdı ama p2'yi promote ediyor — scope=resource farklı
        store = _FakeAudit([_a("prompt.version.create", rid="p1")])
        enforce_sod(
            audit_store=store,
            actor_user_id="u1",
            new_action="prompt.rollout.promote",
            resource_type="prompt",
            resource_id="p2",
            tenant_id="t1",
        )  # temiz

    def test_outside_window_ok(self) -> None:
        store = _FakeAudit(
            [_a("prompt.version.create", rid="p1", days_ago=60)]  # > 30 gün
        )
        enforce_sod(
            audit_store=store,
            actor_user_id="u1",
            new_action="prompt.rollout.promote",
            resource_type="prompt",
            resource_id="p1",
        )


# ── heal_author vs approver ──────────────────────────────────────────────


class TestHealApprove:
    def test_healer_cannot_approve_own_pr(self) -> None:
        store = _FakeAudit(
            [_a("coverup.heal.create", rt="heal_run", rid="r1", days_ago=1)]
        )
        with pytest.raises(SoDViolation):
            enforce_sod(
                audit_store=store,
                actor_user_id="u1",
                new_action="coverup.heal.approve",
                resource_type="heal_run",
                resource_id="r1",
                tenant_id="t1",
            )

    def test_heal_propose_also_conflicts(self) -> None:
        store = _FakeAudit(
            [_a("coverup.heal.propose", rt="heal_run", rid="r2", days_ago=2)]
        )
        with pytest.raises(SoDViolation):
            enforce_sod(
                audit_store=store,
                actor_user_id="u1",
                new_action="coverup.heal.approve",
                resource_type="heal_run",
                resource_id="r2",
            )


# ── tenant-scoped budget bypass ──────────────────────────────────────────


class TestBudgetBypass:
    def test_setter_cannot_bypass(self) -> None:
        store = _FakeAudit(
            [_a("ai.budget.set", rt="tenant", rid="tA", tid="tA", days_ago=5)]
        )
        with pytest.raises(SoDViolation):
            enforce_sod(
                audit_store=store,
                actor_user_id="u1",
                new_action="ai.budget.bypass",
                tenant_id="tA",
            )

    def test_different_tenant_ok(self) -> None:
        store = _FakeAudit(
            [_a("ai.budget.set", rt="tenant", rid="tA", tid="tA", days_ago=5)]
        )
        enforce_sod(
            audit_store=store,
            actor_user_id="u1",
            new_action="ai.budget.bypass",
            tenant_id="tB",
        )


# ── Edge cases ───────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_missing_actor_raises(self) -> None:
        with pytest.raises(SoDViolation):
            enforce_sod(
                audit_store=_FakeAudit([]),
                actor_user_id="",
                new_action="prompt.rollout.promote",
            )

    def test_no_rule_no_raise(self) -> None:
        # SoD kuralı olmayan bir action → her zaman izinli
        store = _FakeAudit([_a("prompt.version.create")])
        enforce_sod(
            audit_store=store,
            actor_user_id="u1",
            new_action="totally.unregulated.action",
        )

    def test_http_detail_payload(self) -> None:
        rule = SOD_RULES[0]
        conflict = _a("prompt.version.create")
        exc = SoDViolation(rule=rule, conflicting=conflict)
        payload = sod_http_detail(exc)
        assert payload["error"] == "sod_violation"
        assert payload["rule"] == rule.name
        assert "message" in payload
        assert payload["conflicting_action"] == "prompt.version.create"
