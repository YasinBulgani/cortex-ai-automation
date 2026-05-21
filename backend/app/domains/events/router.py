"""Event Bus inspector router — /api/v1/events.

Read-only — production sistemleri debug ve audit için event history'yi açar.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.core.event_bus import bus, DomainEvent

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/history")
def event_history(
    name: Optional[str] = Query(None, description="Tam isim veya 'scenario.*' wildcard"),
    project_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    items = bus.history(name=name, project_id=project_id, limit=limit)
    return [e.to_dict() for e in items]


@router.get("/stats")
def event_stats() -> dict:
    return bus.stats()


@router.post("/publish-test")
def publish_test_event(
    name: str = Query("test.ping"),
    project_id: Optional[str] = Query(None),
) -> dict:
    """Test helper — herhangi bir handler bağlıysa tetiklenir."""
    evt = DomainEvent(name=name, payload={"source": "test"}, project_id=project_id)
    called = bus.publish(evt)
    return {"event_id": evt.id, "handlers_called": called}
