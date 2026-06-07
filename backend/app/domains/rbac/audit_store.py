"""Real AuditStore implementation backed by sd_audit_events."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.infra.database import get_db
from app.infra.models import AuditEvent

from .policy import ActorAction, AuditStore


class DbAuditStore:
    """Queries sd_audit_events to satisfy the AuditStore protocol."""

    def __init__(self, db: Session) -> None:
        self._db = db

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
        if not actions:
            return []

        filters = [
            AuditEvent.actor_user_id == actor_user_id,
            AuditEvent.action.in_(actions),
            AuditEvent.ts >= since,
        ]
        if resource_type is not None:
            filters.append(AuditEvent.resource_type == resource_type)
        if resource_id is not None:
            filters.append(AuditEvent.resource_id == resource_id)
        if tenant_id is not None:
            filters.append(AuditEvent.tenant_id == tenant_id)

        rows = self._db.execute(
            select(AuditEvent)
            .where(and_(*filters))
            .order_by(AuditEvent.ts.desc())
            .limit(1)
        ).scalars().all()

        return [
            ActorAction(
                action=row.action,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                tenant_id=row.tenant_id,
                ts=row.ts,
            )
            for row in rows
        ]


def get_audit_store(
    db: Annotated[Session, Depends(get_db)],
) -> AuditStore:
    return DbAuditStore(db)
