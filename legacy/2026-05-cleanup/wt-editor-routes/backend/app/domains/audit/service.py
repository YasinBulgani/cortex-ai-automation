"""Append-only denetim kayıtları."""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.infra.models import AuditEvent, utcnow


def log_audit(
    db: Session,
    *,
    actor_user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    payload: Optional[Dict[str, Any]],
    ip: Optional[str],
) -> None:
    ev = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        ip=ip,
        ts=utcnow(),
    )
    db.add(ev)
