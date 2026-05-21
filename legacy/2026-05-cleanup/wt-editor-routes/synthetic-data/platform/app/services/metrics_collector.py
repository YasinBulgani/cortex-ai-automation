"""
Prometheus Metrikleri Kolektörü — SyntheticBankData

Bu modül FastAPI uygulaması için Prometheus metrikleri toplar ve sunar.
Metrikleri takip etmek için prometheus_client kütüphanesi kullanılır.

Metriklerin Türkçe açıklamaları:
  - request_count: Toplam istek sayısı (method, path, status_code ile etiketlenir)
  - request_latency: İstek yanıt süresi (ms cinsinden histogram)
  - active_requests: Eşzamanlı aktif istek sayısı
  - error_count: Toplam hata sayısı (error_type ile etiketlenir)
  - generation_count: Üretilen veri satırı sayısı (generation_type ile etiketlenir)
  - generation_duration: Veri üretim süresi (saniye cinsinden histogram)

Kullanım:
    from app.services.metrics_collector import MetricsCollector, PrometheusMiddleware

    app = FastAPI()
    metrics = MetricsCollector()
    app.add_middleware(PrometheusMiddleware, metrics=metrics)
"""

import time
import logging
from typing import Callable, Optional
from datetime import datetime, timezone
from contextlib import contextmanager

from fastapi import Request
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    REGISTRY,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Prometheus Metrikleri
# ═══════════════════════════════════════════════════════════════════════════════


class MetricsCollector:
    """
    Prometheus metrikleri tanımlar ve yönetir.

    Attributes:
        request_count: Toplam HTTP istek sayısı
        request_latency: HTTP istek yanıt süresi (histogram)
        active_requests: Eşzamanlı aktif istek sayısı
        error_count: Hata sayısı
        generation_count: Üretilen veri satırları
        generation_duration: Veri üretim süresi
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Metrikleri başlat.

        Args:
            registry: Prometheus registry (varsayılan: REGISTRY)
        """
        self.registry = registry or REGISTRY

        # ── HTTP İstek Metrikleri ──────────────────────────────────────────────
        self.request_count = Counter(
            name="syntheticbank_request_count_total",
            documentation="Toplam HTTP istek sayısı",
            labelnames=["method", "path", "status_code"],
            registry=self.registry,
        )

        self.request_latency = Histogram(
            name="syntheticbank_request_latency_seconds",
            documentation="HTTP istek yanıt süresi (saniye)",
            labelnames=["method", "path"],
            buckets=(
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
                10.0,
            ),
            registry=self.registry,
        )

        self.active_requests = Gauge(
            name="syntheticbank_active_requests",
            documentation="Eşzamanlı aktif HTTP istek sayısı",
            labelnames=["method", "path"],
            registry=self.registry,
        )

        # ── Hata Metrikleri ────────────────────────────────────────────────────
        self.error_count = Counter(
            name="syntheticbank_request_error_count_total",
            documentation="Toplam hata sayısı",
            labelnames=["error_type", "path"],
            registry=self.registry,
        )

        # ── Veri Üretim Metrikleri ─────────────────────────────────────────────
        self.generation_count = Counter(
            name="syntheticbank_generation_count_total",
            documentation="Üretilen veri satırları",
            labelnames=["generation_type", "status"],
            registry=self.registry,
        )

        self.generation_duration = Histogram(
            name="syntheticbank_generation_duration_seconds",
            documentation="Veri üretim süresi (saniye)",
            labelnames=["generation_type"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry,
        )

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
    ) -> None:
        """
        HTTP isteğini metriklere kaydet.

        Args:
            method: HTTP yöntemi (GET, POST, vb.)
            path: İstek yolu
            status_code: HTTP durum kodu
            duration: İstek süresi (saniye)
        """
        self.request_count.labels(
            method=method,
            path=path,
            status_code=status_code,
        ).inc()

        self.request_latency.labels(
            method=method,
            path=path,
        ).observe(duration)

    def record_error(
        self,
        error_type: str,
        path: str,
    ) -> None:
        """
        Hatayı metriklere kaydет.

        Args:
            error_type: Hata türü (ValueError, TimeoutError, vb.)
            path: Hatanın oluştuğu yol
        """
        self.error_count.labels(
            error_type=error_type,
            path=path,
        ).inc()

    def record_generation(
        self,
        generation_type: str,
        count: int = 1,
        status: str = "success",
    ) -> None:
        """
        Veri üretimini metriklere kaydет.

        Args:
            generation_type: Üretim türü (customer, transaction, vb.)
            count: Üretilen satır sayısı
            status: Durum (success, failure, skip)
        """
        self.generation_count.labels(
            generation_type=generation_type,
            status=status,
        ).inc(count)

    def record_generation_duration(
        self,
        generation_type: str,
        duration: float,
    ) -> None:
        """
        Veri üretim süresini metriklere kaydет.

        Args:
            generation_type: Üretim türü
            duration: Süre (saniye)
        """
        self.generation_duration.labels(
            generation_type=generation_type,
        ).observe(duration)

    def inc_active_requests(self, method: str, path: str) -> None:
        """Aktif istek sayısını arttır."""
        self.active_requests.labels(method=method, path=path).inc()

    def dec_active_requests(self, method: str, path: str) -> None:
        """Aktif istek sayısını azalt."""
        self.active_requests.labels(method=method, path=path).dec()

    @contextmanager
    def measure_duration(self, generation_type: str):
        """
        Veri üretim süresini ölçüt.

        Kullanım:
            with metrics.measure_duration("customer"):
                # Veri üret
                pass
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_generation_duration(generation_type, duration)


# ═══════════════════════════════════════════════════════════════════════════════
# Prometheus Middleware
# ═══════════════════════════════════════════════════════════════════════════════


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    FastAPI için Prometheus metrikleri middleware'ı.

    Her HTTP isteğinde:
    1. Aktif istek sayısını arttır
    2. İstek süresini ölç
    3. Metrikleri kaydet
    4. Aktif istek sayısını azalt

    Kullanım:
        from app.services.metrics_collector import MetricsCollector, PrometheusMiddleware

        metrics = MetricsCollector()
        app.add_middleware(PrometheusMiddleware, metrics=metrics)
    """

    def __init__(self, app: ASGIApp, metrics: MetricsCollector):
        """
        Middleware'ı başlat.

        Args:
            app: ASGI uygulaması
            metrics: MetricsCollector örneği
        """
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Her HTTP isteğini işle.

        Args:
            request: HTTP isteği
            call_next: Sonraki middleware/handler

        Returns:
            HTTP yanıtı
        """
        method = request.method
        path = request.url.path

        # Aktif istek sayısını arttır
        self.metrics.inc_active_requests(method, path)

        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Başarılı isteği kaydet
            self.metrics.record_request(
                method=method,
                path=path,
                status_code=response.status_code,
                duration=duration,
            )

            return response

        except Exception as exc:
            duration = time.time() - start_time

            # Hata türünü belirle
            error_type = type(exc).__name__

            # Hataları kaydet
            self.metrics.record_error(
                error_type=error_type,
                path=path,
            )

            logger.error(
                f"İstek hatası: {error_type} — {path}",
                exc_info=exc,
            )

            raise

        finally:
            # Aktif istek sayısını azalt
            self.metrics.dec_active_requests(method, path)


# ═══════════════════════════════════════════════════════════════════════════════
# Prometheus Metrikleri Uç Noktası
# ═══════════════════════════════════════════════════════════════════════════════


def get_metrics_endpoint(registry: Optional[CollectorRegistry] = None):
    """
    Prometheus metrikleri sunan uç nokta.

    FastAPI route'unda kullanılır:

        from fastapi import Response
        from app.services.metrics_collector import get_metrics_endpoint

        @app.get("/metrics")
        async def metrics():
            return Response(
                content=get_metrics_endpoint(),
                media_type="text/plain; version=0.0.4"
            )

    Args:
        registry: Prometheus registry (varsayılan: REGISTRY)

    Returns:
        Prometheus metrikleri text formatında
    """
    registry = registry or REGISTRY
    return generate_latest(registry).decode("utf-8")
