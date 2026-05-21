"""Audit event viewing endpoints."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.deps import get_current_user, _user_permissions
from app.infra.database import get_db
from app.infra.models import AuditEvent, User
from fastapi import HTTPException, status as http_status
from pydantic import BaseModel


router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventOut(BaseModel):
    id: str
    ts: str
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    payload: Optional[dict] = None


@router.get("/events", response_model=list[AuditEventOut])
def list_audit_events(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
):
    """Denetim izlerini listeler."""
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Admin yetkisi gerekli")

    stmt = select(AuditEvent).order_by(AuditEvent.ts.desc())
    if action:
        stmt = stmt.where(AuditEvent.action.ilike(f"%{action}%"))
    if resource_type:
        stmt = stmt.where(AuditEvent.resource_type == resource_type)
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    events = list(db.scalars(stmt))

    out = []
    for e in events:
        actor_email = None
        actor_name = None
        if e.actor_user_id:
            u = db.get(User, e.actor_user_id)
            if u:
                actor_email = u.email
                actor_name = u.full_name
        out.append(AuditEventOut(
            id=e.id,
            ts=str(e.ts),
            actor_email=actor_email,
            actor_name=actor_name,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            payload=e.payload,
        ))
    return out
