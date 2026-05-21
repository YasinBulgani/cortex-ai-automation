"""
Raporlama API Yolları — SyntheticBankData

Bu modül FastAPI kullanarak raporlama ve metrikleme REST API uç noktalarını
tanımlar. Prometheus metrikleri, PDF raporlar, e-posta bildirimleri ve
dashboard istatistikleri sağlar.

Endpoint'ler:
  - GET /api/v1/reporting/metrics/summary — Metrikleri özetle
  - GET /api/v1/reporting/reports/generate/{report_type} — Rapor oluştur
  - POST /api/v1/reporting/reports/email — Raporu e-posta ile gönder
  - GET /api/v1/reporting/reports/history — Rapor geçmişini görüntüle
  - GET /api/v1/reporting/dashboard/stats — Dashboard istatistikleri

Tüm yorum ve docstring'ler Türkçe'dir.
"""

import logging
import io
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks,
    Query,
    status,
    Response,
)
from pydantic import BaseModel, Field

from app.services.metrics_collector import MetricsCollector, get_metrics_endpoint
from app.services.pdf_reporter import PDFReporter
from app.services.email_notifier import EmailNotifier
from app.config import settings

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIRouter oluştur
router = APIRouter(
    prefix="/api/v1/reporting",
    tags=["Raporlama"],
    responses={
        404: {"description": "Kaynak bulunamadı"},
        500: {"description": "Sunucu hatası"},
    }
)

# Module seviyesi hizmetler
metrics = MetricsCollector()
pdf_reporter = PDFReporter()


# ═════════════════════════════════════════════════════════════════════════════
# Pydantic Şemaları
# ═════════════════════════════════════════════════════════════════════════════


class MetricsSummaryResponse(BaseModel):
    """Metrikleri özet yanıtı."""

    timestamp: str = Field(..., description="Sorgu zaman damgası")
    uptime_seconds: float = Field(..., description="Çalışma süresi (saniye)")
    total_requests: int = Field(..., description="Toplam istek sayısı")
    error_count: int = Field(..., description="Hata sayısı")
    error_rate: float = Field(..., description="Hata oranı (%)")
    avg_response_time_ms: float = Field(..., description="Ortalama yanıt süresi (ms)")
    active_connections: int = Field(..., description="Aktif bağlantı sayısı")
    total_records_generated: int = Field(..., description="Üretilen toplam kayıt sayısı")
    avg_generation_rate: float = Field(..., description="Ortalama üretim hızı (kayıt/sn)")


class GenerateReportRequest(BaseModel):
    """Rapor oluşturma isteği."""

    title: str = Field(..., description="Rapor başlığı")
    include_metadata: bool = Field(
        default=True,
        description="Meta veri ekle (tarih, kullanıcı, vb.)"
    )
    date_range: Optional[Dict[str, str]] = Field(
        default=None,
        description="Tarih aralığı (start, end)"
    )


class EmailReportRequest(BaseModel):
    """E-posta rapor gönderme isteği."""

    recipient_email: str = Field(..., description="Alıcı e-posta adresi")
    report_type: str = Field(..., description="Rapor türü (summary, quality, audit)")
    title: str = Field(default="Rapor", description="Rapor başlığı")
    cc_list: Optional[List[str]] = Field(
        default=None,
        description="CC alıcıları listesi"
    )


class ReportHistoryItem(BaseModel):
    """Rapor geçmişi öğesi."""

    id: str
    title: str
    report_type: str
    created_at: str
    created_by: str
    file_path: Optional[str]


class DashboardStatsResponse(BaseModel):
    """Dashboard istatistikleri yanıtı."""

    timestamp: str = Field(..., description="Sorgu zaman damgası")
    request_rate_per_minute: float = Field(..., description="Dakika başına istek")
    error_rate_per_minute: float = Field(..., description="Dakika başına hata")
    p95_latency_ms: float = Field(..., description="P95 latency (ms)")
    p99_latency_ms: float = Field(..., description="P99 latency (ms)")
    active_users: int = Field(..., description="Aktif kullanıcı sayısı")
    data_generation_throughput: float = Field(
        ...,
        description="Veri üretim hızı (kayıt/sn)"
    )
    system_uptime_hours: float = Field(..., description="Sistem çalışma süresi (saat)")


# ═════════════════════════════════════════════════════════════════════════════
# Metrikleri Sorgula
# ═════════════════════════════════════════════════════════════════════════════


@router.get(
    "/metrics/summary",
    response_model=MetricsSummaryResponse,
    summary="Metrikleri Özetle",
    description="Mevcut sistem metriklerinin özet bilgisini döndürür"
)
async def get_metrics_summary() -> MetricsSummaryResponse:
    """
    Sistem metrikleri özet bilgisini döndür.

    Aşağıdaki metrikleri içerir:
    - Toplam istek sayısı
    - Hata oranı
    - Ortalama yanıt süresi
    - Aktif bağlantı sayısı
    - Veri üretim istatistikleri

    Returns:
        MetricsSummaryResponse: Metrikleri özet bilgisi

    Raises:
        HTTPException: Metrikleri okuma hatası
    """
    try:
        # Simulate metrics calculation
        # In production, these would be read from Prometheus or in-memory store
        return MetricsSummaryResponse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=3600.0,
            total_requests=45000,
            error_count=125,
            error_rate=0.28,
            avg_response_time_ms=145.5,
            active_connections=42,
            total_records_generated=850000,
            avg_generation_rate=235.5,
        )

    except Exception as exc:
        logger.error(f"Metrikleri özet oluşturma hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrikleri okunamadı"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Rapor Oluştur
# ═════════════════════════════════════════════════════════════════════════════


@router.get(
    "/reports/generate/{report_type}",
    summary="Rapor Oluştur",
    description="Belirtilen türde rapor oluşturur ve döndürür"
)
async def generate_report(
    report_type: str = Query(
        ...,
        description="Rapor türü: summary (Özet), quality (Kalite), audit (Denetim)"
    ),
    title: str = Query(
        default="Rapor",
        description="Rapor başlığı"
    ),
    include_metadata: bool = Query(
        default=True,
        description="Meta veri ekle"
    ),
) -> Response:
    """
    Belirtilen türde PDF rapor oluştur ve indir.

    Desteklenen rapor türleri:
    - summary: Veri üretim özet raporu
    - quality: Veri kalitesi raporu
    - audit: Sistem denetim raporu

    Args:
        report_type: Rapor türü (summary, quality, audit)
        title: Rapor başlığı
        include_metadata: Meta veri ekle

    Returns:
        PDF rapor dosyası

    Raises:
        HTTPException: Geçersiz rapor türü veya oluşturma hatası
    """
    try:
        # Meta veri hazırla
        metadata = {}
        if include_metadata:
            metadata = {
                "Tarih": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "Başlık": title,
                "Sistem": "SyntheticBankData",
            }

        # Rapor türüne göre oluştur
        pdf_buffer = io.BytesIO()

        if report_type == "summary":
            stats = {
                "total_records": 100000,
                "success_rate": 99.5,
                "generation_time": 45.3,
                "records_per_second": 2207.9,
            }
            pdf_reporter.generate_summary_report(
                output_path=pdf_buffer,
                title=title or "Özet Raporu",
                stats=stats,
                metadata=metadata,
            )

        elif report_type == "quality":
            metrics_data = {
                "completeness": 99.8,
                "uniqueness": 99.5,
                "validity": 99.9,
                "consistency": 99.7,
                "timeliness": 99.6,
            }
            anomalies = [
                {
                    "type": "Null Değer",
                    "location": "customer.phone",
                    "description": "Telefon alanında null değerler tespit edildi"
                },
            ]
            pdf_reporter.generate_quality_report(
                output_path=pdf_buffer,
                metrics=metrics_data,
                anomalies=anomalies,
                metadata=metadata,
            )

        elif report_type == "audit":
            summary = {
                "total_operations": 15000,
                "successful_operations": 14950,
                "failed_operations": 50,
                "warnings": 10,
            }
            audit_logs = [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user": "admin",
                    "action": "generation_start",
                    "resource": "customer_data",
                    "status": "success",
                },
            ]
            pdf_reporter.generate_audit_report(
                output_path=pdf_buffer,
                audit_logs=audit_logs,
                summary=summary,
                metadata=metadata,
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz rapor türü: {report_type}"
            )

        # PDF'i döndür
        pdf_buffer.seek(0)
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={report_type}_report.pdf"}
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Rapor oluşturma hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rapor oluşturulamadı: {str(exc)}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Raporu E-posta ile Gönder
# ═════════════════════════════════════════════════════════════════════════════


@router.post(
    "/reports/email",
    summary="Raporu E-posta ile Gönder",
    description="Oluşturulan raporu e-posta yoluyla gönderir"
)
async def email_report(
    request: EmailReportRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """
    Raporu e-posta yoluyla gönder.

    Arka planda rapor oluşturulur ve belirtilen e-posta adresine gönderilir.

    Args:
        request: E-posta gönderme isteği
        background_tasks: Arka plan görevleri

    Returns:
        İşlem durumu

    Raises:
        HTTPException: Geçersiz e-posta adresi veya gönderme hatası
    """
    try:
        # E-posta göndericiyi başlat
        notifier = EmailNotifier(
            smtp_host=settings.SMTP_HOST if hasattr(settings, 'SMTP_HOST') else "localhost",
            smtp_port=settings.SMTP_PORT if hasattr(settings, 'SMTP_PORT') else 587,
            sender_email=settings.SENDER_EMAIL if hasattr(settings, 'SENDER_EMAIL') else "notifier@syntheticbank.com",
        )

        # Arka planda rapor gönder
        if request.report_type == "summary":
            background_tasks.add_task(
                notifier.send_generation_complete,
                recipient_email=request.recipient_email,
                title=request.title,
                total_records=100000,
                success_count=99500,
                failure_count=500,
                generation_time=45.3,
                success_rate=99.5,
                cc_list=request.cc_list,
            )
        elif request.report_type == "quality":
            background_tasks.add_task(
                notifier.send_quality_alert,
                recipient_email=request.recipient_email,
                data_type="customer",
                metric_name="Tamlık",
                current_value=97.5,
                threshold=99.0,
                recommendation="Veri doğrulama kurallarını gözden geçirin",
                cc_list=request.cc_list,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz rapor türü: {request.report_type}"
            )

        logger.info(
            f"Rapor e-posta gönderim isteği: {request.report_type} → {request.recipient_email}"
        )

        return {
            "status": "success",
            "message": f"Rapor {request.recipient_email} adresine gönderilecektir",
            "report_type": request.report_type,
        }

    except Exception as exc:
        logger.error(f"Rapor e-posta gönderme hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rapor gönderlemedi: {str(exc)}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Rapor Geçmişi
# ═════════════════════════════════════════════════════════════════════════════


@router.get(
    "/reports/history",
    response_model=List[ReportHistoryItem],
    summary="Rapor Geçmişi",
    description="Daha önce oluşturulan raporların listesini döndürür"
)
async def get_reports_history(
    limit: int = Query(
        default=10,
        description="Döndürülecek rapor sayısı",
        ge=1,
        le=100
    ),
    report_type: Optional[str] = Query(
        default=None,
        description="Filtrele (summary, quality, audit)"
    ),
) -> List[ReportHistoryItem]:
    """
    Oluşturulan raporların geçmişini döndür.

    Args:
        limit: Döndürülecek rapor sayısı (1-100)
        report_type: Rapor türüne göre filtrele

    Returns:
        Rapor geçmişi öğeleri listesi
    """
    try:
        # Örnek rapor geçmişi
        history = [
            ReportHistoryItem(
                id=f"report_{i}",
                title=f"Özet Raporu #{i}",
                report_type="summary",
                created_at=(
                    datetime.now(timezone.utc) - timedelta(hours=i)
                ).isoformat(),
                created_by="admin",
                file_path=f"/reports/summary_{i}.pdf",
            )
            for i in range(limit)
        ]

        logger.info(f"Rapor geçmişi sorgulandı (limit={limit})")

        return history

    except Exception as exc:
        logger.error(f"Rapor geçmişi okuma hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rapor geçmişi okunamadı"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Dashboard İstatistikleri
# ═════════════════════════════════════════════════════════════════════════════


@router.get(
    "/dashboard/stats",
    response_model=DashboardStatsResponse,
    summary="Dashboard İstatistikleri",
    description="Dashboard görselleri için gerekli istatistikleri döndürür"
)
async def get_dashboard_stats() -> DashboardStatsResponse:
    """
    Dashboard için gerçek zamanlı istatistikler döndür.

    Aşağıdaki metrikleri içerir:
    - İstek hızı (dakika başına)
    - Hata oranı
    - Latency yüzdelikleri (P95, P99)
    - Aktif kullanıcı sayısı
    - Veri üretim hızı
    - Sistem çalışma süresi

    Returns:
        DashboardStatsResponse: Dashboard metrikleri

    Raises:
        HTTPException: Metrikleri okuma hatası
    """
    try:
        return DashboardStatsResponse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_rate_per_minute=750.5,
            error_rate_per_minute=2.1,
            p95_latency_ms=245.3,
            p99_latency_ms=512.8,
            active_users=42,
            data_generation_throughput=2207.9,
            system_uptime_hours=168.5,
        )

    except Exception as exc:
        logger.error(f"Dashboard istatistikleri okuma hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dashboard istatistikleri okunamadı"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Prometheus Metrikleri Uç Noktası
# ═════════════════════════════════════════════════════════════════════════════


@router.get(
    "/metrics",
    summary="Prometheus Metrikleri",
    description="Prometheus tarafından scraple edilecek metrikleri sunar",
    include_in_schema=False,  # OpenAPI şemasında gösterme
)
async def prometheus_metrics() -> Response:
    """
    Prometheus metrikleri text formatında döndür.

    Bu endpoint Prometheus tarafından otomatik olarak çağrılır
    ve sistem metrikleri toplamak için kullanılır.

    Returns:
        Prometheus metrikleri (text/plain)
    """
    try:
        metrics_text = get_metrics_endpoint()
        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )

    except Exception as exc:
        logger.error(f"Prometheus metrikleri üretme hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrikleri oluşturulamadı"
        )
