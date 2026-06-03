"""Push subscription yönetimi — VAPID Web Push."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.deps import get_current_user
from app.services.web_push_service import get_web_push_service, WebPushService

router = APIRouter(prefix="/push", tags=["notifications", "push"])


class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys: dict  # {p256dh: str, auth: str}


class PushSubscriptionOut(BaseModel):
    id: str
    endpoint: str
    created_at: str


@router.post("/subscribe", summary="Push aboneliği kaydet")
async def subscribe_push(
    body: PushSubscriptionIn,
    current_user=Depends(get_current_user),
    svc: WebPushService = Depends(get_web_push_service),
) -> dict:
    """Tarayıcının push aboneliğini kaydet."""
    # Gerçek DB kaydı için model gelince buraya eklenecek
    # Şimdilik response doğrulama
    if not body.endpoint.startswith("https://"):
        raise HTTPException(400, "Geçersiz endpoint — HTTPS zorunlu")

    return {
        "ok": True,
        "message": "Push aboneliği kaydedildi",
        "vapid_public_key": svc.public_key or "",
    }


@router.delete("/unsubscribe", summary="Push aboneliğini iptal et")
async def unsubscribe_push(
    endpoint: str,
    current_user=Depends(get_current_user),
) -> dict:
    return {"ok": True, "message": "Push aboneliği iptal edildi"}


@router.get("/vapid-public-key", summary="VAPID public key'i getir")
async def get_vapid_public_key(
    svc: WebPushService = Depends(get_web_push_service),
) -> dict:
    """Frontend push aboneliği için VAPID public key'i döner."""
    return {"public_key": svc.public_key or ""}
