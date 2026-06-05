"""Notifications domain için Pydantic şemaları.

Request şemaları:
    * NotificationCreate     : yeni bildirim oluşturma
    * NotificationPrefsUpdate: kullanıcı tercihleri güncelleme
    * BulkNotificationRequest: admin toplu gönderim

Response şemaları:
    * NotificationResponse      : tek bildirim
    * NotificationListResponse  : sayfalı liste
    * NotificationPrefsResponse : bildirim tercihleri
    * WSMessage                 : WebSocket mesaj zarfı
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

# ── WebSocket ─────────────────────────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    timestamp: Optional[str] = None


# ── Notification preferences ──────────────────────────────────────────────────

class NotificationPrefsUpdate(BaseModel):
    """PUT /notifications/prefs request body."""

    notify_on_complete: bool = True
    notify_on_failure: bool = True
    slack_webhook_url: Optional[str] = None
    digest_mode: str = Field(default="instant", description="instant | digest_daily | digest_weekly | off")
    channels: str = Field(default="email,in_app", description="Virgülle ayrılmış kanal listesi")


class NotificationPrefsResponse(BaseModel):
    """GET/PUT /notifications/prefs response."""

    notify_on_complete: bool
    notify_on_failure: bool
    slack_webhook_url: Optional[str] = None
    digest_mode: str = "instant"
    channels: str = "email,in_app"

    model_config = {"from_attributes": True}


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationCreate(BaseModel):
    """Yeni bildirim oluşturma isteği."""

    user_id: str = Field(..., description="Hedef kullanıcı ID'si")
    subject: str = Field(..., min_length=1, max_length=256)
    html_body: str
    plain_text: Optional[str] = None
    event_type: Optional[str] = Field(None, description="Bildirimi tetikleyen olay adı")


class NotificationResponse(BaseModel):
    """Tek bildirim yanıtı."""

    id: str
    user_id: str
    subject: str
    event_type: Optional[str] = None
    created_at: datetime
    is_read: bool = False

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Sayfalı bildirim listesi."""

    items: List[NotificationResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ── Bulk send ─────────────────────────────────────────────────────────────────

class BulkNotificationRequest(BaseModel):
    """Admin toplu bildirim gönderimi."""

    user_ids: List[str] = Field(..., min_length=1)
    subject: str = Field(..., min_length=1, max_length=256)
    html_body: str
    plain_text: Optional[str] = None
