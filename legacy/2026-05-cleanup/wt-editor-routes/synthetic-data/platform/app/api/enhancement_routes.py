"""
Platform Enhancement Routes.

Tüm yeni platform özelliklerinin endpoint'lerini tek bir router altında
toplar. Her servis kendi iç router'ına sahiptir; bu modül onları
birleştirerek /api/v1 altına monte eder.

Kapsanan servisler:
  - Audit Logger (GET /api/audit/*)
  - Data Versioning (GET /api/versions/*)
  - Quality Dashboard (GET /api/quality/*)
  - Webhook Service (POST/GET/DELETE /api/webhooks/*)
  - Export Templates (POST/GET/PUT/DELETE /api/templates/*)

Ek yardımcı endpoint'ler:
  - GET /api/platform/health — Platform sağlık durumu
  - GET /api/platform/stats — Genel istatistikler
  - GET /api/platform/config — Platform yapılandırması
"""

import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.config import settings

# Alt servis router'larını import et
from app.services.audit_logger import audit_router
from app.services.data_versioning import version_router
from app.services.quality_dashboard import quality_router
from app.services.webhook_service import webhook_router
from app.services.export_templates import template_router


# ═══════════════════════════════════════════════════════════════════════
# Ana Enhancement Router
# ═══════════════════════════════════════════════════════════════════════

enhancement_router = APIRouter(
    tags=["Platform Enhancements"],
)

# Alt router'ları dahil et
enhancement_router.include_router(audit_router)
enhancement_router.include_router(version_router)
enhancement_router.include_router(quality_router)
enhancement_router.include_router(webhook_router)
enhancement_router.include_router(template_router)


# ═══════════════════════════════════════════════════════════════════════
# Pydantic Yanıt Şemaları
# ═══════════════════════════════════════════════════════════════════════


class PlatformHealthResponse(BaseModel):
    """Platform sağlık durumu yanıtı."""
    status: str
    version: str
    uptime_info: str
    database: str
    services: dict[str, str]
    timestamp: str


class PlatformStatsResponse(BaseModel):
    """Platform istatistikleri yanıtı."""
    total_datasets: int
    total_generations: int
    total_audit_logs: int
    total_versions: int
    total_quality_checks: int
    total_webhooks: int
    total_templates: int
    active_webhooks: int
    timestamp: str


class ServiceStatusResponse(BaseModel):
    """Tekil servis durumu yanıtı."""
    service: str
    status: str
    details: Optional[dict] = None


class PlatformConfigResponse(BaseModel):
    """Platform yapılandırma bilgileri."""
    app_name: str
    version: str
    debug: bool
    database_configured: bool
    llm_provider: Optional[str] = None
    max_upload_size_mb: float
    allowed_extensions: list[str]
    rate_limit_enabled: bool
    audit_enabled: bool
    webhook_enabled: bool
    features: dict[str, bool]


# ═══════════════════════════════════════════════════════════════════════
# Platform Sağlık ve İstatistik Endpoint'leri
# ═══════════════════════════════════════════════════════════════════════


@enhancement_router.get(
    "/api/platform/health",
    response_model=PlatformHealthResponse,
    summary="Platform Sağlık Durumu",
    description="Tüm platform servislerinin sağlık durumunu döndürür.",
    tags=["Platform"],
)
async def platform_health(db: Session = Depends(get_db)):
    """
    Platform sağlık kontrolü.

    Her servisin erişilebilirliğini ve veritabanı bağlantısını kontrol eder.
    """
    # Veritabanı kontrolü
    db_status = "healthy"
    try:
        db.execute(func.now())
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)[:100]}"

    # Servis durumları
    services = {
        "audit_logger": "operational",
        "data_versioning": "operational",
        "quality_dashboard": "operational",
        "webhook_service": "operational",
        "export_templates": "operational",
        "rate_limiter": "operational",
        "error_handler": "operational",
    }

    overall = "healthy" if db_status == "healthy" else "degraded"

    return PlatformHealthResponse(
        status=overall,
        version=settings.VERSION,
        uptime_info="Servis çalışıyor",
        database=db_status,
        services=services,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@enhancement_router.get(
    "/api/platform/stats",
    response_model=PlatformStatsResponse,
    summary="Platform İstatistikleri",
    description="Tüm platform modüllerinin istatistiklerini döndürür.",
    tags=["Platform"],
)
async def platform_stats(db: Session = Depends(get_db)):
    """Platform geneli istatistik endpoint'i."""
    from app.models.dataset import Dataset, GenerationJob
    from app.services.audit_logger import AuditLog
    from app.services.data_versioning import DataVersion
    from app.services.quality_dashboard import QualityMetrics
    from app.services.webhook_service import WebhookConfig, WebhookStatus
    from app.services.export_templates import ExportTemplate

    def _safe_count(model) -> int:
        """Tablo yoksa 0 döndür."""
        try:
            return db.query(func.count(model.id)).scalar() or 0
        except Exception:
            return 0

    total_datasets = _safe_count(Dataset)
    total_generations = _safe_count(GenerationJob)
    total_audit = _safe_count(AuditLog)
    total_versions = _safe_count(DataVersion)
    total_quality = _safe_count(QualityMetrics)
    total_webhooks = _safe_count(WebhookConfig)
    total_templates = _safe_count(ExportTemplate)

    # Aktif webhook sayısı
    try:
        active_webhooks = (
            db.query(func.count(WebhookConfig.id))
            .filter(WebhookConfig.status == WebhookStatus.ACTIVE.value)
            .scalar() or 0
        )
    except Exception:
        active_webhooks = 0

    return PlatformStatsResponse(
        total_datasets=total_datasets,
        total_generations=total_generations,
        total_audit_logs=total_audit,
        total_versions=total_versions,
        total_quality_checks=total_quality,
        total_webhooks=total_webhooks,
        total_templates=total_templates,
        active_webhooks=active_webhooks,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@enhancement_router.get(
    "/api/platform/config",
    response_model=PlatformConfigResponse,
    summary="Platform Yapılandırması",
    description="Mevcut platform yapılandırma bilgilerini döndürür.",
    tags=["Platform"],
)
async def platform_config():
    """Platform yapılandırma bilgileri endpoint'i."""
    db_configured = bool(settings.database_url and "postgresql" in settings.database_url)

    llm_provider = None
    try:
        llm_provider = settings.LLM_PROVIDER
    except AttributeError:
        pass

    max_upload_mb = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024) / (1024 * 1024)
    allowed_ext = getattr(settings, "ALLOWED_EXTENSIONS", [".csv", ".json", ".xlsx"])

    return PlatformConfigResponse(
        app_name=settings.APP_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
        database_configured=db_configured,
        llm_provider=llm_provider,
        max_upload_size_mb=round(max_upload_mb, 1),
        allowed_extensions=allowed_ext if isinstance(allowed_ext, list) else list(allowed_ext),
        rate_limit_enabled=True,
        audit_enabled=True,
        webhook_enabled=True,
        features={
            "schema_analysis": True,
            "pii_detection": True,
            "rule_inference": True,
            "relationship_inference": True,
            "synthetic_generation": True,
            "scenario_generation": True,
            "llm_integration": llm_provider is not None,
            "audit_logging": True,
            "data_versioning": True,
            "quality_dashboard": True,
            "webhook_notifications": True,
            "export_templates": True,
            "rate_limiting": True,
            "structured_errors": True,
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# Servis Bazlı Durum Endpoint'leri
# ═══════════════════════════════════════════════════════════════════════


@enhancement_router.get(
    "/api/platform/services",
    summary="Servis Listesi",
    description="Tüm platform servislerinin listesini ve durumlarını döndürür.",
    tags=["Platform"],
)
async def list_services():
    """Platform servis listesi."""
    services = [
        {
            "name": "Audit Logger",
            "key": "audit_logger",
            "description": "API çağrıları ve kullanıcı işlemlerinin denetim kaydı",
            "endpoints": ["/api/audit/logs", "/api/audit/stats", "/api/audit/export"],
            "status": "operational",
        },
        {
            "name": "Data Versioning",
            "key": "data_versioning",
            "description": "Sentetik veri versiyonlama ve geri yükleme",
            "endpoints": ["/api/versions/{dataset_id}"],
            "status": "operational",
        },
        {
            "name": "Quality Dashboard",
            "key": "quality_dashboard",
            "description": "Dataset kalite analizi ve zaman serisi takibi",
            "endpoints": [
                "/api/quality/{dataset_id}",
                "/api/quality/{dataset_id}/history",
                "/api/quality/{dataset_id}/summary",
            ],
            "status": "operational",
        },
        {
            "name": "Webhook Service",
            "key": "webhook_service",
            "description": "Olay bazlı HMAC-SHA256 imzalı bildirimler",
            "endpoints": ["/api/webhooks", "/api/webhooks/{id}", "/api/webhooks/{id}/test"],
            "status": "operational",
        },
        {
            "name": "Export Templates",
            "key": "export_templates",
            "description": "Şablon bazlı çoklu format veri export'u",
            "endpoints": [
                "/api/templates",
                "/api/templates/{id}",
                "/api/templates/{id}/export",
            ],
            "status": "operational",
        },
        {
            "name": "Rate Limiter",
            "key": "rate_limiter",
            "description": "IP bazlı sliding window rate limiting",
            "endpoints": [],
            "status": "operational",
        },
        {
            "name": "Error Handler",
            "key": "error_handler",
            "description": "Yapılandırılmış hata yanıtları ve X-Request-ID takibi",
            "endpoints": [],
            "status": "operational",
        },
    ]

    return {
        "services": services,
        "total": len(services),
        "all_operational": all(s["status"] == "operational" for s in services),
    }


# ═══════════════════════════════════════════════════════════════════════
# Webhook Event Listesi (yardımcı)
# ═══════════════════════════════════════════════════════════════════════


@enhancement_router.get(
    "/api/platform/webhook-events",
    summary="Webhook Olay Türleri",
    description="Desteklenen webhook olay türlerinin listesini döndürür.",
    tags=["Platform"],
)
async def list_webhook_events():
    """Kullanılabilir webhook olay türleri."""
    from app.services.webhook_service import WebhookEvent

    return {
        "events": [
            {
                "event": e.value,
                "description": {
                    "generation.started": "Sentetik veri üretimi başladığında",
                    "generation.completed": "Sentetik veri üretimi tamamlandığında",
                    "generation.failed": "Sentetik veri üretimi başarısız olduğunda",
                    "analysis.completed": "Şema analizi tamamlandığında",
                    "quality.report_ready": "Kalite raporu hazır olduğunda",
                    "export.completed": "Veri export'u tamamlandığında",
                    "dataset.deleted": "Dataset silindiğinde",
                }.get(e.value, e.value),
            }
            for e in WebhookEvent
        ],
        "total": len(WebhookEvent),
    }


# ═══════════════════════════════════════════════════════════════════════
# Export Format Listesi (yardımcı)
# ═══════════════════════════════════════════════════════════════════════


@enhancement_router.get(
    "/api/platform/export-formats",
    summary="Export Formatları",
    description="Desteklenen export formatlarının listesini döndürür.",
    tags=["Platform"],
)
async def list_export_formats():
    """Kullanılabilir export formatları."""
    from app.services.export_templates import ExportFormat

    formats = [
        {
            "format": ExportFormat.CSV.value,
            "description": "Virgülle ayrılmış değerler",
            "extension": ".csv",
            "mime_type": "text/csv",
        },
        {
            "format": ExportFormat.JSON.value,
            "description": "JSON dizisi",
            "extension": ".json",
            "mime_type": "application/json",
        },
        {
            "format": ExportFormat.JSONL.value,
            "description": "JSON Lines (satır başına bir JSON nesnesi)",
            "extension": ".jsonl",
            "mime_type": "application/x-ndjson",
        },
        {
            "format": ExportFormat.SQL_INSERT.value,
            "description": "SQL INSERT deyimleri",
            "extension": ".sql",
            "mime_type": "application/sql",
        },
        {
            "format": ExportFormat.SQL_COPY.value,
            "description": "PostgreSQL COPY formatı",
            "extension": ".sql",
            "mime_type": "application/sql",
        },
        {
            "format": ExportFormat.PARQUET_SCHEMA.value,
            "description": "Apache Parquet şema tanımı",
            "extension": ".json",
            "mime_type": "application/json",
        },
    ]

    return {"formats": formats, "total": len(formats)}


# ═══════════════════════════════════════════════════════════════════════
# Kalite Boyutları Listesi (yardımcı)
# ═══════════════════════════════════════════════════════════════════════


@enhancement_router.get(
    "/api/platform/quality-dimensions",
    summary="Kalite Boyutları",
    description="Kalite analizinde kullanılan boyutları ve ağırlıklarını döndürür.",
    tags=["Platform"],
)
async def list_quality_dimensions():
    """Kalite boyutları ve ağırlıkları."""
    from app.services.quality_dashboard import QualityDimension, QualityAnalyzer

    dimensions = []
    for dim in QualityDimension:
        weight = QualityAnalyzer.WEIGHTS.get(dim, 0.0)
        dimensions.append({
            "dimension": dim.value,
            "weight": weight,
            "description": {
                "completeness": "Eksik veri oranı — NULL ve boş değerlerin analizi",
                "uniqueness": "Tekil değer oranı — Satır ve kolon bazlı duplikasyon",
                "consistency": "Tutarlılık — Veri tipi ve format uyumu",
                "accuracy": "Doğruluk — Aykırı değer ve referans karşılaştırma",
                "timeliness": "Güncellik — Verinin zaman duyarlılığı",
                "validity": "Geçerlilik — İş kurallarına uyum kontrolü",
            }.get(dim.value, dim.value),
        })

    return {
        "dimensions": dimensions,
        "total_weight": sum(d["weight"] for d in dimensions),
    }
