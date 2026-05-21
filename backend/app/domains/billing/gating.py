"""Plan-gating guards — call these from feature routers before allowing
resource-creating actions.

Example:
    from app.domains.billing.gating import enforce_capacity

    @router.post("/projects")
    def create_project(user, db, ...):
        enforce_capacity(db, user.tenant_id, "project_count")
        ...
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.billing.service import check_limit, compute_usage_snapshot


def enforce_capacity(
    db: Session,
    tenant_id: str,
    metric: str,
    *,
    delta: float = 1.0,
) -> None:
    """Raise 402 (Payment Required) if adding ``delta`` would exceed plan."""
    snapshot = compute_usage_snapshot(db, tenant_id)
    result = check_limit(snapshot, metric, delta=delta)
    if result.allowed:
        return
    raise HTTPException(
        status_code=402,
        detail={
            "code": "billing.limit_exceeded",
            "message": result.reason or "Plan limiti aşıldı",
            "metric": metric,
            "used": result.used,
            "limit": result.limit,
            "upgrade_url": "/admin/billing",
        },
    )
