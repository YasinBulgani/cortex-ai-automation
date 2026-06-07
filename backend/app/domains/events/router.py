"""Event Bus inspector router — /api/v1/events.

Read-only — production sistemleri debug ve audit için event history'yi açar.
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.event_bus import DomainEvent, bus
from app.deps import _user_permissions, get_current_user
from app.infra.database import get_db
from app.infra.models import User

from . import schemas as domain_schemas  # noqa: F401 — schemas module created for type contract use

router = APIRouter(prefix="/events", tags=["events"])

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/history")
def event_history(
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    name: Optional[str] = Query(None, description="Tam isim veya 'scenario.*' wildcard"),
    project_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    is_admin = "admin.*" in _user_permissions(user)
    if project_id:
        from app.domains.tspm.models import TspmProject, TspmProjectMember
        if db.get(TspmProject, project_id) is None:
            raise HTTPException(404, "Proje bulunamadı")
        if not is_admin:
            is_member = db.scalar(
                select(func.count()).where(
                    TspmProjectMember.project_id == project_id,
                    TspmProjectMember.user_id == user.id,
                )
            )
            if not is_member:
                raise HTTPException(403, "Bu projeye erişim yetkiniz yok")
    elif not is_admin:
        raise HTTPException(403, "Tüm event geçmişine erişim için proje ID'si veya admin yetkisi gerekli")
    items = bus.history(name=name, project_id=project_id, limit=limit)
    return [e.to_dict() for e in items]


@router.get("/stats")
def event_stats(user: Annotated[User, Depends(get_current_user)]) -> dict:
    return bus.stats()


@router.post("/publish-test")
def publish_test_event(
    user: Annotated[User, Depends(get_current_user)],
    name: str = Query("test.ping"),
    project_id: Optional[str] = Query(None),
) -> dict:
    """Test helper — herhangi bir handler bağlıysa tetiklenir."""
    if "admin.*" not in _user_permissions(user):
        raise HTTPException(403, "Admin yetkisi gerekli")
    evt = DomainEvent(name=name, payload={"source": "test"}, project_id=project_id)
    called = bus.publish(evt)
    return {"event_id": evt.id, "handlers_called": called}
