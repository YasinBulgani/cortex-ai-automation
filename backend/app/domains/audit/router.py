"""Audit event viewing and export endpoints.

SOC 2 / DPA evidence: admin-only endpoints for listing, exporting (CSV/JSON)
and generating compliance reports from the tamper-evident audit log.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Response
from fastapi import HTTPException, status as http_status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, _user_permissions
from app.infra.database import get_db
from app.infra.models import AuditEvent, User


router = APIRouter(prefix="/audit", tags=["audit"])

# ── Schemas ────────────────────────────────────────────────────────────────────


class AuditEventOut(BaseModel):
    id: str
    ts: str
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    payload: Optional[dict] = None
    ip: Optional[str] = None
    tenant_id: Optional[str] = None
    seq: Optional[int] = None
    prev_hash: Optional[str] = None
    hash: Optional[str] = None


class AuditExportSummary(BaseModel):
    exported_at: str
    total_events: int
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    format: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require_admin(user: User) -> None:
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Admin yetkisi gerekli",
        )


def _build_query(
    db: Session,
    *,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    stmt = select(AuditEvent).order_by(AuditEvent.ts.asc())
    if action:
        stmt = stmt.where(AuditEvent.action.ilike(f"%{action}%"))
    if resource_type:
        stmt = stmt.where(AuditEvent.resource_type == resource_type)
    if actor_user_id:
        stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            stmt = stmt.where(AuditEvent.ts >= dt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Geçersiz date_from: {date_from}")
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            stmt = stmt.where(AuditEvent.ts <= dt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Geçersiz date_to: {date_to}")
    return stmt


def _enrich(db: Session, events: list[AuditEvent]) -> list[AuditEventOut]:
    """Attach actor email/name from user table."""
    # Batch load distinct actor ids
    actor_ids = {e.actor_user_id for e in events if e.actor_user_id}
    user_map: dict[str, User] = {}
    for uid in actor_ids:
        u = db.get(User, uid)
        if u:
            user_map[uid] = u

    out: list[AuditEventOut] = []
    for e in events:
        u = user_map.get(e.actor_user_id) if e.actor_user_id else None
        out.append(AuditEventOut(
            id=e.id,
            ts=e.ts.isoformat() if hasattr(e.ts, "isoformat") else str(e.ts),
            actor_email=u.email if u else None,
            actor_name=u.full_name if u else None,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            payload=e.payload,
            ip=e.ip,
            tenant_id=e.tenant_id,
            seq=e.seq,
            prev_hash=e.prev_hash,
            hash=e.hash,
        ))
    return out


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/events", response_model=list[AuditEventOut])
def list_audit_events(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    actor_user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO 8601, örn: 2026-01-01T00:00:00Z"),
    date_to: Optional[str] = Query(None, description="ISO 8601, örn: 2026-12-31T23:59:59Z"),
):
    """Denetim izlerini sayfalı listeler. Admin yetkisi gerekir."""
    _require_admin(user)
    stmt = _build_query(
        db,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    stmt = stmt.order_by(None).order_by(AuditEvent.ts.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    events = list(db.scalars(stmt))
    return _enrich(db, events)


@router.get(
    "/export/json",
    response_class=Response,
    summary="Audit log JSON export (SOC 2 evidence)",
)
def export_audit_json(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    actor_user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(10_000, ge=1, le=100_000),
):
    """Audit log'u JSON formatında indir — SOC 2 / DPA evidence."""
    _require_admin(user)
    stmt = _build_query(
        db,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    ).limit(limit)
    events = list(db.scalars(stmt))
    enriched = _enrich(db, events)

    export_ts = datetime.now(timezone.utc).isoformat()
    payload = {
        "meta": {
            "exported_at": export_ts,
            "total_events": len(enriched),
            "date_from": date_from,
            "date_to": date_to,
            "exported_by": user.email,
            "format": "json",
            "description": "Cortex AI Automation — Audit Log Export (SOC 2 / BDDK evidence)",
        },
        "events": [e.model_dump() for e in enriched],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    filename = f"cortex_audit_{export_ts[:10]}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/export/csv",
    response_class=Response,
    summary="Audit log CSV export (SOC 2 evidence)",
)
def export_audit_csv(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    actor_user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(10_000, ge=1, le=100_000),
):
    """Audit log'u CSV formatında indir — SOC 2 / DPA evidence."""
    _require_admin(user)
    stmt = _build_query(
        db,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    ).limit(limit)
    events = list(db.scalars(stmt))
    enriched = _enrich(db, events)

    buf = io.StringIO()
    fieldnames = [
        "id", "ts", "actor_email", "actor_name", "action",
        "resource_type", "resource_id", "ip", "tenant_id",
        "seq", "prev_hash", "hash",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for e in enriched:
        row = e.model_dump()
        # Flatten payload to string for CSV
        if row.get("payload"):
            row["payload"] = json.dumps(row["payload"], ensure_ascii=False)
        writer.writerow({k: row.get(k, "") for k in fieldnames})

    export_ts = datetime.now(timezone.utc).isoformat()
    filename = f"cortex_audit_{export_ts[:10]}.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/summary", response_model=AuditExportSummary)
def export_audit_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Export metadata — toplam kayıt sayısı ve tarih aralığı."""
    _require_admin(user)
    stmt = _build_query(db, date_from=date_from, date_to=date_to)
    count = len(list(db.scalars(stmt)))
    return AuditExportSummary(
        exported_at=datetime.now(timezone.utc).isoformat(),
        total_events=count,
        date_from=date_from,
        date_to=date_to,
        format="summary",
    )
