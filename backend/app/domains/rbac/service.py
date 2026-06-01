"""RBAC service facade — HTTP-agnostic wrapper over policy.py.

Raises ValueError/KeyError, never HTTPException.
"""
from __future__ import annotations

from typing import Any

from .policy import ROLES, AuditStore, SoDViolation, enforce_sod, has_permission


def get_role(role_name: str) -> dict[str, Any]:
    """Return role metadata dict. Raises KeyError if role is unknown."""
    if role_name not in ROLES:
        raise KeyError(f"Unknown role: {role_name!r}")
    return {
        "name": role_name,
        "permissions": sorted(ROLES[role_name]),
    }


def list_roles() -> list[str]:
    """Return sorted list of all defined role names."""
    return sorted(ROLES.keys())


def check_permission(user_permissions: list[str], permission: str) -> bool:
    """Return True if user_permissions satisfies the required permission.

    Supports ``admin.*`` wildcard (any user with admin.* passes all checks).
    """
    return has_permission(set(user_permissions), permission)


def get_role_permissions(role_name: str) -> set[str]:
    """Return the permission set for the given role. Raises KeyError if unknown."""
    if role_name not in ROLES:
        raise KeyError(f"Unknown role: {role_name!r}")
    return set(ROLES[role_name])


def enforce_segregation(
    audit_store: AuditStore,
    user_id: str,
    new_action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> None:
    """Enforce Segregation-of-Duties for the given action.

    Raises ValueError (wrapping SoDViolation message) on a policy breach.
    Callers should NOT catch SoDViolation directly — use this facade.
    """
    try:
        enforce_sod(
            audit_store=audit_store,
            actor_user_id=user_id,
            new_action=new_action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    except SoDViolation as exc:
        raise ValueError(str(exc)) from exc
