"""
Webhook Servisi.

Olay bazlı bildirim sistemi. Dataset üretimi tamamlandığında,
kalite raporu hazırlandığında veya hata oluştuğunda kayıtlı
endpoint'lere HMAC-SHA256 imzalı webhook gönderir.

Özellikler:
  - WebhookConfig SQLAlchemy modeli
  - HMAC-SHA256 imzalama
  - Retry mekanizması (üssel geri çekilme)
  - POST /api/webhooks — Yeni webhook kaydı
  - GET /api/webhooks — Kayıtlı webhook listesi
  - DELETE /api/webhooks/{id} — Webhook silme
  - POST /api/webhooks/{id}/test — Test webhook gönderimi
"""

import enum
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    Integer,
    JSON,
    String,
    Text,
    func,
    desc,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.models.database import Base, get_db


# ═══════════════════════════════════════════════════════════════════════
# Enum ve Model Tanımları
# ═══════════════════════════════════════════════════════════════════════


class WebhookEvent(str, enum.Enum):
    """Desteklenen webhook olayları."""
    GENERATION_STARTED = "generation.started"
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"
    ANALYSIS_COMPLETED = "analysis.completed"
    QUALITY_REPORT_READY = "quality.report_ready"
    EXPORT_COMPLETED = "export.completed"
    DATASET_DELETED = "dataset.deleted"


class WebhookStatus(str, enum.Enum):
    """Webhook durumu."""
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"       # Ardışık hata sonrası devre dışı
    DELETED = "deleted"     # Soft delete


class WebhookConfig(Base):
    """Webhook yapılandırma modeli."""

    __tablename__ = "webhook_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str] = mapped_column(String(256), nullable=False)

    # Hangi olayları dinliyor
    events: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        String(20), default=WebhookStatus.ACTIVE.value
    )

    # İstatistikler
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Yapılandırma
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Zaman damgaları
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<WebhookConfig(id={self.id}, name='{self.name}', status={self.status})>"


class WebhookDeliveryLog(Base):
    """Webhook gönderim log modeli."""

    __tablename__ = "webhook_delivery_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Gönderim detayları
    request_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    request_headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    request_body: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Yanıt detayları
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Durum
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


from sqlalchemy import Float


# ═══════════════════════════════════════════════════════════════════════
# Pydantic Şemaları
# ═══════════════════════════════════════════════════════════════════════


class WebhookCreateRequest(BaseModel):
    """Webhook oluşturma isteği."""
    name: str = Field(..., min_length=1, max_length=200, description="Webhook adı")
    url: str = Field(..., description="Hedef URL")
    events: list[str] = Field(
        ..., min_length=1,
        description="Dinlenecek olay türleri"
    )
    secret: Optional[str] = Field(
        None, description="HMAC secret (otomatik üretilir)"
    )
    max_retries: int = Field(3, ge=0, le=10)
    timeout_seconds: int = Field(10, ge=1, le=60)


class WebhookResponse(BaseModel):
    """Webhook yanıt modeli."""
    id: int
    name: str
    url: str
    events: list[str]
    status: str
    total_sent: int
    total_failed: int
    last_sent_at: Optional[str] = None
    created_at: str


class WebhookListResponse(BaseModel):
    """Webhook listesi yanıtı."""
    webhooks: list[WebhookResponse]
    total: int


class WebhookTestResponse(BaseModel):
    """Test webhook yanıtı."""
    success: bool
    delivery_id: str
    response_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# Webhook Dispatcher
# ═══════════════════════════════════════════════════════════════════════


class WebhookDispatcher:
    """
    Webhook gönderim motoru.

    HMAC-SHA256 imza ile güvenli webhook gönderimi,
    üssel geri çekilme ile retry mekanizması sağlar.
    """

    MAX_CONSECUTIVE_FAILURES = 10  # Bu sayıdan sonra webhook devre dışı

    @staticmethod
    def generate_secret() -> str:
        """Rastgele HMAC secret üret."""
        return hashlib.sha256(uuid.uuid4().bytes).hexdigest()

    @staticmethod
    def sign_payload(payload: bytes, secret: str) -> str:
        """HMAC-SHA256 ile payload imzala."""
        return hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    async def dispatch(
        cls,
        db: Session,
        event: WebhookEvent,
        payload: dict[str, Any],
    ) -> list[dict]:
        """
        Belirtilen olayı dinleyen tüm aktif webhook'lara gönder.

        Returns:
            Her webhook için gönderim sonucu listesi.
        """
        webhooks = (
            db.query(WebhookConfig)
            .filter(
                WebhookConfig.is_active.is_(True),
                WebhookConfig.status == WebhookStatus.ACTIVE.value,
            )
            .all()
        )

        results = []
        for wh in webhooks:
            if event.value not in (wh.events or []):
                continue
            result = await cls._send_webhook(db, wh, event, payload)
            results.append(result)

        return results

    @classmethod
    async def _send_webhook(
        cls,
        db: Session,
        webhook: WebhookConfig,
        event: WebhookEvent,
        payload: dict[str, Any],
    ) -> dict:
        """Tek bir webhook'a gönderim yap (retry destekli)."""
        delivery_id = uuid.uuid4().hex
        body = {
            "event": event.value,
            "delivery_id": delivery_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        body_bytes = json.dumps(body, default=str).encode("utf-8")
        signature = cls.sign_payload(body_bytes, webhook.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event.value,
            "X-Webhook-Delivery": delivery_id,
            "X-Webhook-Signature": f"sha256={signature}",
            "User-Agent": "SyntheticBankData-Webhook/1.0",
        }

        last_error = None
        for attempt in range(1, webhook.max_retries + 1):
            start_time = time.monotonic()
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        webhook.url,
                        content=body_bytes,
                        headers=headers,
                        timeout=webhook.timeout_seconds,
                    )
                elapsed_ms = (time.monotonic() - start_time) * 1000

                # Gönderim logla
                log = WebhookDeliveryLog(
                    webhook_id=webhook.id,
                    event_type=event.value,
                    delivery_id=delivery_id,
                    request_url=webhook.url,
                    request_headers=headers,
                    request_body=body,
                    response_status=resp.status_code,
                    response_body=resp.text[:2000] if resp.text else None,
                    response_time_ms=round(elapsed_ms, 2),
                    success=200 <= resp.status_code < 300,
                    attempt=attempt,
                )
                db.add(log)

                if 200 <= resp.status_code < 300:
                    webhook.total_sent += 1
                    webhook.consecutive_failures = 0
                    webhook.last_sent_at = datetime.now(timezone.utc)
                    webhook.last_error = None
                    db.commit()
                    return {
                        "webhook_id": webhook.id,
                        "success": True,
                        "delivery_id": delivery_id,
                        "status_code": resp.status_code,
                        "elapsed_ms": round(elapsed_ms, 2),
                    }

                last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"

            except Exception as exc:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                last_error = str(exc)

                log = WebhookDeliveryLog(
                    webhook_id=webhook.id,
                    event_type=event.value,
                    delivery_id=delivery_id,
                    request_url=webhook.url,
                    request_headers=headers,
                    request_body=body,
                    response_time_ms=round(elapsed_ms, 2),
                    success=False,
                    attempt=attempt,
                    error_message=str(exc),
                )
                db.add(log)

            # Üssel geri çekilme (1s, 2s, 4s, ...)
            if attempt < webhook.max_retries:
                import asyncio
                await asyncio.sleep(2 ** (attempt - 1))

        # Tüm denemeler başarısız
        webhook.total_failed += 1
        webhook.consecutive_failures += 1
        webhook.last_error = last_error

        if webhook.consecutive_failures >= cls.MAX_CONSECUTIVE_FAILURES:
            webhook.status = WebhookStatus.FAILED.value
            webhook.is_active = False

        db.commit()

        return {
            "webhook_id": webhook.id,
            "success": False,
            "delivery_id": delivery_id,
            "error": last_error,
        }


# ═══════════════════════════════════════════════════════════════════════
# FastAPI Router
# ═══════════════════════════════════════════════════════════════════════

webhook_router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@webhook_router.post(
    "",
    response_model=WebhookResponse,
    status_code=201,
    summary="Webhook Oluştur",
    description="Yeni webhook kaydı oluşturur. Otomatik HMAC secret üretilir.",
)
async def create_webhook(
    request: WebhookCreateRequest,
    db: Session = Depends(get_db),
):
    """Yeni webhook kaydı oluştur."""
    # Event doğrulama
    valid_events = {e.value for e in WebhookEvent}
    invalid = [e for e in request.events if e not in valid_events]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz olay türleri: {invalid}. "
                   f"Geçerli: {sorted(valid_events)}"
        )

    secret = request.secret or WebhookDispatcher.generate_secret()

    webhook = WebhookConfig(
        name=request.name,
        url=request.url,
        secret=secret,
        events=request.events,
        max_retries=request.max_retries,
        timeout_seconds=request.timeout_seconds,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        status=webhook.status,
        total_sent=webhook.total_sent,
        total_failed=webhook.total_failed,
        last_sent_at=webhook.last_sent_at.isoformat() if webhook.last_sent_at else None,
        created_at=webhook.created_at.isoformat(),
    )


@webhook_router.get(
    "",
    response_model=WebhookListResponse,
    summary="Webhook Listesi",
    description="Kayıtlı webhook'ların listesini döndürür.",
)
async def list_webhooks(
    status: Optional[str] = Query(None, description="Durum filtresi"),
    db: Session = Depends(get_db),
):
    """Webhook listesi endpoint'i."""
    query = db.query(WebhookConfig).filter(
        WebhookConfig.status != WebhookStatus.DELETED.value
    )
    if status:
        query = query.filter(WebhookConfig.status == status)

    webhooks = query.order_by(desc(WebhookConfig.created_at)).all()

    return WebhookListResponse(
        webhooks=[
            WebhookResponse(
                id=wh.id,
                name=wh.name,
                url=wh.url,
                events=wh.events or [],
                status=wh.status,
                total_sent=wh.total_sent,
                total_failed=wh.total_failed,
                last_sent_at=wh.last_sent_at.isoformat() if wh.last_sent_at else None,
                created_at=wh.created_at.isoformat(),
            )
            for wh in webhooks
        ],
        total=len(webhooks),
    )


@webhook_router.delete(
    "/{webhook_id}",
    summary="Webhook Sil",
    description="Webhook kaydını soft-delete yapar.",
)
async def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
):
    """Webhook silme endpoint'i (soft delete)."""
    webhook = db.query(WebhookConfig).filter(WebhookConfig.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook bulunamadı")

    webhook.status = WebhookStatus.DELETED.value
    webhook.is_active = False
    db.commit()

    return {"message": "Webhook silindi", "id": webhook_id}


@webhook_router.post(
    "/{webhook_id}/test",
    response_model=WebhookTestResponse,
    summary="Test Webhook",
    description="Kayıtlı webhook'a test bildirimi gönderir.",
)
async def test_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
):
    """Test webhook gönderimi."""
    webhook = db.query(WebhookConfig).filter(WebhookConfig.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook bulunamadı")

    test_payload = {
        "message": "Bu bir test webhook bildirimidir.",
        "webhook_id": webhook_id,
        "webhook_name": webhook.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result = await WebhookDispatcher._send_webhook(
        db, webhook, WebhookEvent.GENERATION_COMPLETED, test_payload
    )

    return WebhookTestResponse(
        success=result.get("success", False),
        delivery_id=result.get("delivery_id", ""),
        response_status=result.get("status_code"),
        response_time_ms=result.get("elapsed_ms"),
        error=result.get("error"),
    )
