"""Events domain için Pydantic şemaları.

Request şemaları:
    * EventPublishRequest : event bus'a yeni olay yayınlama

Response şemaları:
    * EventResponse       : tek bir domain event
    * EventPublishResponse: yayın sonucu (id + handler sayısı)
    * EventStatsResponse  : bus istatistikleri
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── Request şemaları ──────────────────────────────────────────────────────────

class EventPublishRequest(BaseModel):
    """POST /events/publish-test request body."""

    name: str = Field(..., min_length=1, description="Olay adı, ör. 'scenario.created'")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Serbest biçim olay verisi")
    project_id: Optional[str] = Field(None, description="Proje kapsamı")


# ── Response şemaları ─────────────────────────────────────────────────────────

class EventResponse(BaseModel):
    """Tek bir domain event yanıtı."""

    id: str
    name: str
    payload: Dict[str, Any] = {}
    project_id: Optional[str] = None
    timestamp: Optional[datetime] = None


class EventPublishResponse(BaseModel):
    """Olay yayınlama sonucu."""

    event_id: str
    handlers_called: int


class EventListResponse(BaseModel):
    """Event geçmişi listesi."""

    items: List[EventResponse]
    total: int


class EventStatsResponse(BaseModel):
    """GET /events/stats yanıtı — bus istatistikleri."""

    total_published: Optional[int] = None
    handlers_registered: Optional[int] = None
    history_size: Optional[int] = None
