"""Extended health check — tüm kritik bağımlılıkların durumunu toplar.

Her check zaman-sınırlı (default 2s), aralarında paralel çalışabilir ama
ilk implementasyon sıralı (basit + predictable). Frontend polling 30s
interval'ı için bu yeterince hızlıdır.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Callable, List, Tuple

import httpx

from app.config import settings
from app.domains.health.schemas import ComponentStatus, ExtendedHealth, HealthLevel

logger = logging.getLogger(__name__)

_DEFAULT_CHECK_TIMEOUT_S = 2.0


def _timed(check: Callable[[], ComponentStatus]) -> ComponentStatus:
    """Check'in kendisi zaten ComponentStatus döndürüyor; bu sarmalayıcı süre
    ölçümü işini soyutlar (check içinde de yapılabilirdi, burada tek noktada).
    """
    t0 = time.monotonic()
    try:
        result = check()
    except Exception as exc:  # pragma: no cover - defansif
        return ComponentStatus(
            name="unknown",
            label="Bilinmeyen",
            level=HealthLevel.down,
            detail=f"Check patladı: {exc}",
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
    if result.latency_ms is None:
        object.__setattr__(
            result, "latency_ms", int((time.monotonic() - t0) * 1000)
        )
    return result


def _check_database() -> ComponentStatus:
    try:
        from sqlalchemy import text
        from app.infra.database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return ComponentStatus(
            name="postgres",
            label="Veritabanı (PostgreSQL)",
            level=HealthLevel.ok,
        )
    except Exception as exc:
        return ComponentStatus(
            name="postgres",
            label="Veritabanı (PostgreSQL)",
            level=HealthLevel.down,
            detail=str(exc)[:120],
        )


def _check_redis() -> ComponentStatus:
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_timeout=_DEFAULT_CHECK_TIMEOUT_S)
        client.ping()
        return ComponentStatus(
            name="redis",
            label="Redis",
            level=HealthLevel.ok,
            optional=True,   # Redis yoksa rate-limit devre dışı ama backend çalışır
        )
    except Exception as exc:
        return ComponentStatus(
            name="redis",
            label="Redis",
            level=HealthLevel.down,
            detail=str(exc)[:120],
            optional=True,
        )


def _check_engine() -> ComponentStatus:
    try:
        r = httpx.get(f"{settings.engine_base_url}/health", timeout=_DEFAULT_CHECK_TIMEOUT_S)
        if r.status_code == 200:
            return ComponentStatus(
                name="engine",
                label="Test Motoru",
                level=HealthLevel.ok,
            )
        return ComponentStatus(
            name="engine",
            label="Test Motoru",
            level=HealthLevel.degraded,
            detail=f"HTTP {r.status_code}",
        )
    except Exception as exc:
        return ComponentStatus(
            name="engine",
            label="Test Motoru",
            level=HealthLevel.down,
            detail=str(exc)[:120],
        )


def _check_ai_gateway() -> ComponentStatus:
    base = os.environ.get("AI_GATEWAY_BASE_URL", "http://127.0.0.1:8080")
    try:
        r = httpx.get(f"{base}/ai/health", timeout=_DEFAULT_CHECK_TIMEOUT_S)
        if r.status_code == 200:
            return ComponentStatus(
                name="ai_gateway",
                label="AI Gateway",
                level=HealthLevel.ok,
            )
        return ComponentStatus(
            name="ai_gateway",
            label="AI Gateway",
            level=HealthLevel.degraded,
            detail=f"HTTP {r.status_code}",
        )
    except Exception as exc:
        return ComponentStatus(
            name="ai_gateway",
            label="AI Gateway",
            level=HealthLevel.down,
            detail=str(exc)[:120],
            optional=True,   # AI Gateway yoksa bazı özellikler pasif ama backend çalışır
        )


def _check_ollama() -> ComponentStatus:
    """Ollama lokal kurulu değilse ok — gateway fallback'i başka provider'a gider."""
    try:
        # Ollama'nın /api/tags endpoint'i modelleri listeler; 200 ise ayakta
        ollama_url = settings.ollama_base_url.rstrip("/v1").rstrip("/")
        r = httpx.get(f"{ollama_url}/api/tags", timeout=_DEFAULT_CHECK_TIMEOUT_S)
        if r.status_code == 200:
            return ComponentStatus(
                name="ollama",
                label="Ollama (lokal LLM)",
                level=HealthLevel.ok,
                optional=True,
            )
        return ComponentStatus(
            name="ollama",
            label="Ollama (lokal LLM)",
            level=HealthLevel.degraded,
            detail=f"HTTP {r.status_code}",
            optional=True,
        )
    except Exception as exc:
        return ComponentStatus(
            name="ollama",
            label="Ollama (lokal LLM)",
            level=HealthLevel.down,
            detail=str(exc)[:120],
            optional=True,
        )


_CHECKS: Tuple[Callable[[], ComponentStatus], ...] = (
    _check_database,
    _check_redis,
    _check_engine,
    _check_ai_gateway,
    _check_ollama,
)


def _compute_overall(components: List[ComponentStatus]) -> HealthLevel:
    """Zorunlu bileşenlerin en kötüsü. Opsiyonel olanlar overall'u aşağı çekmez."""
    required = [c for c in components if not c.optional]
    if any(c.level == HealthLevel.down for c in required):
        return HealthLevel.down
    if any(c.level == HealthLevel.degraded for c in required):
        return HealthLevel.degraded
    # Opsiyoneller de yellow/red ise overall degraded gösterebilir — görsel ipucu
    if any(c.level in (HealthLevel.down, HealthLevel.degraded) for c in components):
        return HealthLevel.degraded
    return HealthLevel.ok


def get_extended_health() -> ExtendedHealth:
    components = [_timed(check) for check in _CHECKS]
    overall = _compute_overall(components)
    return ExtendedHealth(
        overall=overall,
        components=components,
        checked_at_unix=time.time(),
        app_name=settings.app_name,
    )
