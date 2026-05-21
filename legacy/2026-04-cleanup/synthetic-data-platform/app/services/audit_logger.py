"""
Audit Log Sistemi.

Tüm API çağrılarını, kullanıcı işlemlerini ve sistem olaylarını
izlenebilir şekilde kaydeder. KVKK ve SOX uyumlu denetim izi sağlar.

Özellikler:
  - AuditLog SQLAlchemy modeli
  - AuditAction enum — UPLOAD, ANALYZE, GENERATE, EXPORT, DELETE, CONFIG_CHANGE
  - log_action() fonksiyonu — her API çağrısında otomatik log
  - Middleware ile otomatik request/response loglama
  - GET /api/audit/logs — Filtrelenebilir audit log listesi
  - Audit log export (CSV)
"""

import csv
import enum
import io
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import (
    DateTime,
    Enum,
    Integer,
    JSON,
    String,
    Text,
    func,
    desc,
)
from sqlalchemy.orm import Mapped, Session, mapped_column
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.models.database import Base, get_db


# ═══════════════════════════════════════════════════════════════════════
# Enum ve Model Tanımları
# ═══════════════════════════════════════════════════════════════════════


class AuditAction(str, enum.Enum):
    """Denetlenebilir eylem türleri."""

    UPLOAD = "upload"                 # Dosya yükleme
    ANALYZE = "analyze"               # Şema/kolon/PII analizi
    GENERATE = "generate"             # Sentetik veri üretimi
    EXPORT = "export"                 # Dışa aktarım
    DELETE = "delete"                 # Kaynak silme
    CONFIG_CHANGE = "config_change"   # Yapılandırma değişikliği
    VIEW = "view"                     # Kaynak görüntüleme
    LIST = "list"                     # Listeleme
    CLASSIFY = "classify"             # Kolon sınıflandırma
    DETECT_PII = "detect_pii"        # PII tespiti
    INFER_RULES = "infer_rules"      # Kural çıkarımı
    INFER_RELATIONS = "infer_relations"  # İlişki çıkarımı
    WEBHOOK = "webhook"              # Webhook işlemi
    VERSION = "version"              # Versiyon işlemi
    QUALITY_CHECK = "quality_check"  # Kalite kontrolü
    LOGIN = "login"                  # Giriş
    LOGOUT = "logout"                # Çıkış
    ERROR = "error"                  # Hata kaydı


class AuditLog(Base):
    """
    Audit log veritabanı modeli.

    Her API çağrısı ve kullanıcı eylemi için bir kayıt oluşturur.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True,
        comment="Kullanıcı kimliği (ileride auth entegrasyonu)",
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction), nullable=False, index=True,
        comment="Gerçekleştirilen eylem",
    )
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True,
        comment="Kaynak türü (dataset, job, webhook, template vb.)",
    )
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Kaynak kimliği",
    )
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment="Eylem detayları (JSON)",
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True,
        comment="İstemci IP adresi",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="İstemci User-Agent bilgisi",
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True,
        comment="İlişkili Request ID",
    )
    method: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        comment="HTTP metodu (GET, POST, DELETE vb.)",
    )
    path: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True,
        comment="İstek yolu",
    )
    status_code: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="HTTP yanıt durum kodu",
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="İstek süresi (milisaniye)",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Olay zamanı",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"resource='{self.resource_type}/{self.resource_id}', "
            f"timestamp='{self.timestamp}')>"
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict döndür."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action.value if self.action else None,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# ═══════════════════════════════════════════════════════════════════════
# Audit Logger Servisi
# ═══════════════════════════════════════════════════════════════════════


# Endpoint path → AuditAction eşleştirmesi
PATH_ACTION_MAP: dict[str, AuditAction] = {
    "/api/v1/upload": AuditAction.UPLOAD,
    "/api/v1/analyze": AuditAction.ANALYZE,
    "/api/v1/classify": AuditAction.CLASSIFY,
    "/api/v1/detect-pii": AuditAction.DETECT_PII,
    "/api/v1/infer-rules": AuditAction.INFER_RULES,
    "/api/v1/infer-relationships": AuditAction.INFER_RELATIONS,
    "/api/v1/generate": AuditAction.GENERATE,
    "/api/v1/generate-scenario": AuditAction.GENERATE,
    "/api/v1/generate-natural": AuditAction.GENERATE,
    "/api/v1/export": AuditAction.EXPORT,
    "/api/v1/download": AuditAction.EXPORT,
    "/api/v1/webhooks": AuditAction.WEBHOOK,
    "/api/v1/versions": AuditAction.VERSION,
    "/api/v1/quality": AuditAction.QUALITY_CHECK,
    "/api/v1/templates": AuditAction.EXPORT,
}

# Loglama dışı tutulacak path'ler
EXCLUDED_PATHS: set[str] = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/",
    "/api/v1/health",
    "/favicon.ico",
}


def _detect_action(method: str, path: str) -> AuditAction:
    """HTTP metod ve path'ten AuditAction belirle."""
    if method == "DELETE":
        return AuditAction.DELETE

    for prefix, action in PATH_ACTION_MAP.items():
        if path.startswith(prefix):
            return action

    if method == "GET":
        if any(seg in path for seg in ["/datasets", "/jobs", "/scenarios"]):
            if path.count("/") > 3:
                return AuditAction.VIEW
            return AuditAction.LIST
        return AuditAction.VIEW

    return AuditAction.VIEW


def _detect_resource_type(path: str) -> Optional[str]:
    """Path'ten kaynak türünü çıkar."""
    segments = path.strip("/").split("/")
    if len(segments) >= 3:
        # /api/v1/{resource_type}/...
        return segments[2]
    return None


def _get_client_ip(request: Request) -> str:
    """İstemci IP adresini al."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


def log_action(
    db: Session,
    action: AuditAction,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    request_id: Optional[str] = None,
) -> AuditLog:
    """
    Audit log kaydı oluştur.

    Herhangi bir API handler'dan doğrudan çağrılabilir.

    Args:
        db: Veritabanı oturumu.
        action: Gerçekleştirilen eylem.
        resource_type: Kaynak türü (dataset, job vb.).
        resource_id: Kaynak kimliği.
        details: Ek detaylar (JSON).
        user_id: Kullanıcı kimliği.
        ip_address: İstemci IP.
        request_id: İlişkili Request ID.

    Returns:
        Oluşturulan AuditLog kaydı.
    """
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        details=details,
        ip_address=ip_address,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
    )

    try:
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
    except Exception:
        db.rollback()
        # Audit log hatası uygulamayı durdurmamalı
        print(f"[AUDIT] Log kaydı oluşturulamadı: action={action.value}")

    return log_entry


# ═══════════════════════════════════════════════════════════════════════
# Audit Log Middleware
# ═══════════════════════════════════════════════════════════════════════


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Otomatik request/response audit loglama middleware.

    Her API çağrısını (hariç tutulanlar dışında) otomatik olarak
    audit log tablosuna kaydeder.
    """

    def __init__(
        self,
        app: ASGIApp,
        db_session_factory=None,
        excluded_paths: Optional[set[str]] = None,
        log_request_body: bool = False,
    ):
        super().__init__(app)
        self.db_session_factory = db_session_factory
        self.excluded_paths = excluded_paths or EXCLUDED_PATHS
        self.log_request_body = log_request_body

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Her isteği audit log'a kaydet."""
        path = request.url.path

        # Hariç tutulan path'ler
        if path in self.excluded_paths:
            return await call_next(request)

        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", "")

        # İsteği işle
        response = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)

        # Audit log kaydı oluştur (async olmayan — fire and forget)
        try:
            if self.db_session_factory:
                db = self.db_session_factory()
                try:
                    action = _detect_action(request.method, path)
                    resource_type = _detect_resource_type(path)

                    log_entry = AuditLog(
                        action=action,
                        resource_type=resource_type,
                        ip_address=_get_client_ip(request),
                        user_agent=request.headers.get("User-Agent", "")[:500],
                        request_id=request_id,
                        method=request.method,
                        path=path,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                        timestamp=datetime.now(timezone.utc),
                    )
                    db.add(log_entry)
                    db.commit()
                finally:
                    db.close()
        except Exception as exc:
            # Audit log hatası uygulamayı etkilememeli
            print(f"[AUDIT MIDDLEWARE] Loglama hatası: {exc}")

        return response


# ═══════════════════════════════════════════════════════════════════════
# Pydantic Şemaları
# ═══════════════════════════════════════════════════════════════════════


class AuditLogResponse(BaseModel):
    """Audit log yanıt şeması."""
    id: int
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[int] = None
    timestamp: Optional[str] = None


class AuditLogListResponse(BaseModel):
    """Audit log listesi yanıtı."""
    logs: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditSummaryResponse(BaseModel):
    """Audit özet istatistikleri."""
    total_logs: int
    actions: dict[str, int]
    top_resources: list[dict[str, Any]]
    top_ips: list[dict[str, Any]]
    error_count: int
    avg_duration_ms: Optional[float] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# API Router — /api/v1/audit/*
# ═══════════════════════════════════════════════════════════════════════

audit_router = APIRouter(prefix="/api/v1/audit", tags=["Denetim Logları"])


@audit_router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="Audit Log Listesi",
    description="Filtrelenebilir audit log listesini döndürür. Tarih, action, user, resource ile filtreleme yapılabilir.",
)
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Action filtresi (upload, generate vb.)"),
    resource_type: Optional[str] = Query(None, description="Kaynak türü filtresi"),
    user_id: Optional[str] = Query(None, description="Kullanıcı ID filtresi"),
    ip_address: Optional[str] = Query(None, description="IP adresi filtresi"),
    start_date: Optional[str] = Query(None, description="Başlangıç tarihi (ISO format)"),
    end_date: Optional[str] = Query(None, description="Bitiş tarihi (ISO format)"),
    status_code: Optional[int] = Query(None, description="HTTP status code filtresi"),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    page_size: int = Query(50, ge=1, le=500, description="Sayfa başına kayıt"),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    """Filtrelenebilir audit log listesi."""
    query = db.query(AuditLog)

    # Filtreler
    if action:
        try:
            audit_action = AuditAction(action)
            query = query.filter(AuditLog.action == audit_action)
        except ValueError:
            pass

    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if ip_address:
        query = query.filter(AuditLog.ip_address == ip_address)

    if status_code:
        query = query.filter(AuditLog.status_code == status_code)

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(AuditLog.timestamp >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(AuditLog.timestamp <= end_dt)
        except ValueError:
            pass

    # Toplam kayıt sayısı
    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)

    # Sayfalandırma
    logs = (
        query.order_by(desc(AuditLog.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return AuditLogListResponse(
        logs=[
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action.value if log.action else "",
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                ip_address=log.ip_address,
                request_id=log.request_id,
                method=log.method,
                path=log.path,
                status_code=log.status_code,
                duration_ms=log.duration_ms,
                timestamp=log.timestamp.isoformat() if log.timestamp else None,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@audit_router.get(
    "/summary",
    response_model=AuditSummaryResponse,
    summary="Audit Özet İstatistikleri",
    description="Belirli bir dönem için audit log özetini döndürür.",
)
async def audit_summary(
    days: int = Query(7, ge=1, le=365, description="Son kaç günün özeti"),
    db: Session = Depends(get_db),
) -> AuditSummaryResponse:
    """Audit log özet istatistikleri."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(AuditLog).filter(AuditLog.timestamp >= cutoff)

    total = query.count()

    # Action dağılımı
    action_counts = {}
    for action in AuditAction:
        count = query.filter(AuditLog.action == action).count()
        if count > 0:
            action_counts[action.value] = count

    # En çok erişilen kaynaklar
    top_resources_query = (
        db.query(
            AuditLog.resource_type,
            func.count(AuditLog.id).label("count"),
        )
        .filter(AuditLog.timestamp >= cutoff)
        .filter(AuditLog.resource_type.isnot(None))
        .group_by(AuditLog.resource_type)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )
    top_resources = [
        {"resource_type": r[0], "count": r[1]}
        for r in top_resources_query
    ]

    # En aktif IP'ler
    top_ips_query = (
        db.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label("count"),
        )
        .filter(AuditLog.timestamp >= cutoff)
        .filter(AuditLog.ip_address.isnot(None))
        .group_by(AuditLog.ip_address)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )
    top_ips = [
        {"ip_address": r[0], "count": r[1]}
        for r in top_ips_query
    ]

    # Hata sayısı
    error_count = (
        query.filter(AuditLog.status_code >= 400).count()
    )

    # Ortalama süre
    avg_duration = (
        db.query(func.avg(AuditLog.duration_ms))
        .filter(AuditLog.timestamp >= cutoff)
        .filter(AuditLog.duration_ms.isnot(None))
        .scalar()
    )

    return AuditSummaryResponse(
        total_logs=total,
        actions=action_counts,
        top_resources=top_resources,
        top_ips=top_ips,
        error_count=error_count,
        avg_duration_ms=round(avg_duration, 2) if avg_duration else None,
        period_start=cutoff.isoformat(),
        period_end=datetime.now(timezone.utc).isoformat(),
    )


@audit_router.get(
    "/export",
    summary="Audit Log CSV Export",
    description="Audit loglarını CSV formatında dışa aktarır.",
)
async def export_audit_logs(
    days: int = Query(30, ge=1, le=365, description="Son kaç günün logu"),
    action: Optional[str] = Query(None, description="Action filtresi"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Audit loglarını CSV olarak export et."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(AuditLog).filter(AuditLog.timestamp >= cutoff)

    if action:
        try:
            audit_action = AuditAction(action)
            query = query.filter(AuditLog.action == audit_action)
        except ValueError:
            pass

    logs = query.order_by(desc(AuditLog.timestamp)).all()

    # CSV oluştur
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "id", "timestamp", "action", "resource_type", "resource_id",
        "user_id", "ip_address", "method", "path", "status_code",
        "duration_ms", "request_id", "details",
    ])

    # Satırlar
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat() if log.timestamp else "",
            log.action.value if log.action else "",
            log.resource_type or "",
            log.resource_id or "",
            log.user_id or "",
            log.ip_address or "",
            log.method or "",
            log.path or "",
            log.status_code or "",
            log.duration_ms or "",
            log.request_id or "",
            str(log.details) if log.details else "",
        ])

    output.seek(0)

    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
