"""RBAC domain router — prefix /rbac."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .policy import SoDViolation, sod_http_detail
from .service import (
    check_permission,
    enforce_segregation,
    get_role,
    list_roles,
)

router = APIRouter(prefix="/rbac", tags=["rbac"])


# ── Request / Response models ────────────────────────────────────────────


class CheckPermissionRequest(BaseModel):
    user_permissions: list[str]
    permission: str


class EnforceSodRequest(BaseModel):
    user_id: str
    new_action: str
    resource_type: str | None = None
    resource_id: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────────


@router.get("/roles", summary="List all roles")
def list_all_roles() -> list[str]:
    """Return a sorted list of all defined RBAC role names."""
    return list_roles()


@router.get("/roles/{role_name}", summary="Get role and its permissions")
def get_role_detail(role_name: str) -> dict[str, Any]:
    """Return role metadata including its permission set."""
    try:
        return get_role(role_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/check-permission", summary="Check whether a permission is granted")
def check_permission_endpoint(body: CheckPermissionRequest) -> dict[str, bool]:
    """Return ``{allowed: bool}`` — whether ``permission`` is in user_permissions."""
    allowed = check_permission(body.user_permissions, body.permission)
    return {"allowed": allowed}


@router.post("/enforce-sod", summary="Enforce Segregation-of-Duties policy")
def enforce_sod_endpoint(body: EnforceSodRequest) -> dict[str, bool]:
    """Return ``{ok: true}`` or raise 403 on SoD violation.

    Note: this endpoint requires a real AuditStore. In the current stub
    implementation, no past actions are checked (AuditStore returns empty).
    Wire a real AuditStore via dependency injection for production use.
    """
    from .policy import ActorAction, AuditStore
    from datetime import datetime, timezone
    from typing import List, Optional, Tuple

    class _NoopAuditStore:
        """Stub — always returns empty; replace with real impl via DI."""

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
            return []

    try:
        enforce_segregation(
            audit_store=_NoopAuditStore(),
            user_id=body.user_id,
            new_action=body.new_action,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return {"ok": True}
