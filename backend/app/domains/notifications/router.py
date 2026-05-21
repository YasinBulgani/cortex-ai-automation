from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.domains.auth.service import decode_token
from app.domains.notifications.service import manager
from app.infra.models import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

_SLACK_WEBHOOK_PREFIX = "https://hooks.slack."


def _mask_webhook_url(url: Optional[str]) -> Optional[str]:
    """Webhook URL'ini maskele — yalnizca son 4 karakter gorunur.

    DB ihlali durumunda tam URL yerine kismi bilgi ifsa edilmis olur.
    Ornek: https://hooks.slack.com/services/****ABCD
    """
    if not url:
        return url
    if len(url) <= 4:
        return "****"
    return url[: url.rfind("/") + 1] + "****" + url[-4:]


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class NotificationPrefsOut(BaseModel):
    notify_on_complete: bool
    notify_on_failure: bool
    slack_webhook_url: Optional[str]

    model_config = {"from_attributes": True}


class NotificationPrefsIn(BaseModel):
    notify_on_complete: bool = True
    notify_on_failure: bool = True
    slack_webhook_url: Optional[str] = None

    @field_validator("slack_webhook_url")
    @classmethod
    def _validate_slack_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not v.startswith(_SLACK_WEBHOOK_PREFIX):
            raise ValueError(
                f"Gecersiz Slack webhook URL'i — '{_SLACK_WEBHOOK_PREFIX}' ile baslamalidir"
            )
        if len(v) > 500:
            raise ValueError("Slack webhook URL'i cok uzun (max 500 karakter)")
        return v


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query("")):
    """Kullanici icin bildirim websocket baglantisi acar."""
    if not token:
        token = websocket.cookies.get("bgts_access_token", "")
    user_id = None
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except Exception as exc:
        logger.warning("Notification websocket token decode failed: %s", exc)
        await websocket.close(code=4001)
        return
    if not user_id:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)


# ── Notification Preferences ──────────────────────────────────────────────────

@router.get("/notifications/prefs", response_model=NotificationPrefsOut)
def get_notification_prefs(db: DB, current_user: CurrentUser):
    """Mevcut kullanıcının bildirim tercihlerini döndürür. Kayıt yoksa varsayılanları döner."""
    from app.domains.notifications.models import NotificationPrefs

    prefs = db.get(NotificationPrefs, current_user.id)
    if prefs is None:
        return NotificationPrefsOut(
            notify_on_complete=True,
            notify_on_failure=True,
            slack_webhook_url=None,
        )
    return NotificationPrefsOut(
        notify_on_complete=prefs.notify_on_complete,
        notify_on_failure=prefs.notify_on_failure,
        slack_webhook_url=prefs.slack_webhook_url,
    )


@router.put("/notifications/prefs", response_model=NotificationPrefsOut)
def upsert_notification_prefs(body: NotificationPrefsIn, db: DB, current_user: CurrentUser):
    """Mevcut kullanıcının bildirim tercihlerini oluşturur veya günceller."""
    from datetime import datetime, timezone
    from fastapi import HTTPException
    from app.domains.notifications.models import NotificationPrefs

    prefs = db.get(NotificationPrefs, current_user.id)
    if prefs is None:
        prefs = NotificationPrefs(user_id=current_user.id)
        db.add(prefs)

    prefs.notify_on_complete = body.notify_on_complete
    prefs.notify_on_failure = body.notify_on_failure
    prefs.slack_webhook_url = body.slack_webhook_url
    prefs.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(prefs)
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Failed to persist notification preferences for user %s",
            current_user.id,
        )
        raise HTTPException(status_code=500, detail="Bildirim tercihleri kaydedilemedi.") from exc

    return prefs
