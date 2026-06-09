"""RBAC rules for defect retest lifecycle.

Defect retest lifecycle:
    1. QA/Tester opens defect (defects.write)
    2. Developer marks for retest (defects.retest)
    3. QA re-runs test (defects.retest_execute)
    4. QA verifies fix (defects.verify)

RBAC Matrix:
    QA Engineer: open, update, verify, execute_retest
    Developer: mark_retest (prepare for QA retesting)
    QA Automation: execute_retest
    Manager: read-only on retest queue
"""

from typing import Optional


class RetestRBACPolicy:
    """Defect retest RBAC rules."""

    # Permission matrix: (role) -> [allowed_actions]
    ROLE_PERMISSIONS = {
        "qa_engineer": ["defects.open", "defects.write", "defects.verify", "defects.retest_execute"],
        "developer": ["defects.retest"],  # Mark as ready for retest only
        "qa_automation": ["defects.retest_execute"],  # Execute retest only
        "manager": ["defects.read"],
        "admin": ["defects.read", "defects.write", "defects.retest", "defects.verify", "defects.retest_execute"],
    }

    @classmethod
    def can_mark_retest(cls, user_role: str) -> bool:
        """Can user mark defect for retest (developer action)."""
        perms = cls.ROLE_PERMISSIONS.get(user_role, [])
        return "defects.retest" in perms or "admin.*" in str(user_role)

    @classmethod
    def can_execute_retest(cls, user_role: str) -> bool:
        """Can user execute retest (QA action)."""
        perms = cls.ROLE_PERMISSIONS.get(user_role, [])
        return "defects.retest_execute" in perms

    @classmethod
    def can_verify_fix(cls, user_role: str) -> bool:
        """Can user verify defect fix (QA action)."""
        perms = cls.ROLE_PERMISSIONS.get(user_role, [])
        return "defects.verify" in perms

    @classmethod
    def get_allowed_actions(cls, user_role: str) -> list[str]:
        """Get all allowed actions for role."""
        return cls.ROLE_PERMISSIONS.get(user_role, [])


class RetestStatusTransitions:
    """Defect retest status transitions."""

    # retest_status values: not_ready, ready, in_progress, passed, blocked
    VALID_TRANSITIONS = {
        "not_ready": ["ready"],
        "ready": ["in_progress", "not_ready"],
        "in_progress": ["passed", "blocked", "ready"],
        "passed": ["ready", "not_ready"],
        "blocked": ["ready"],
    }

    @classmethod
    def can_transition(cls, current: str, target: str) -> bool:
        """Check if retest status transition is allowed."""
        allowed = cls.VALID_TRANSITIONS.get(current, [])
        return target in allowed

    @classmethod
    def validate(cls, current: str, target: str) -> None:
        """Raise ValueError if transition invalid."""
        if not cls.can_transition(current, target):
            allowed = cls.VALID_TRANSITIONS.get(current, [])
            raise ValueError(
                f"Invalid retest status transition: {current} → {target}. "
                f"Allowed: {allowed}"
            )
