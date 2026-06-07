"""Extended health endpoint.

Yol: ``GET /api/v1/health/extended``
Amaç: frontend üst bar'daki health dot'un veri kaynağı.

Rate limit middleware bu endpoint'i de kapsayabilir — frontend polling
30s aralıkla olduğu için sorun değil, ama gelecekte yüksek-frekans ihtiyacı
olursa ``X-Skip-Rate-Limit`` header'ı eklenebilir (ayrı iş).
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import get_current_user
from app.infra.models import User

CurrentUser = Annotated[User, Depends(get_current_user)]

from app.domains.health.schemas import ExtendedHealth
from app.domains.health.service import get_extended_health

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/extended",
    response_model=ExtendedHealth,
    summary="Tüm bağımlılıkların detaylı sağlık durumu",
    response_description="Bileşen listesi + overall durum",
)
def extended(user: CurrentUser) -> ExtendedHealth:
    """Postgres, Redis, Engine, AI Gateway, Ollama — tümünün tek seferde durumu."""
    return get_extended_health()


class DetailedHealthResponse(BaseModel):
    status: str
    services: dict
    version: str


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="DB + Redis detaylı sağlık kontrolü",
)
def detailed_health(user: CurrentUser) -> DetailedHealthResponse:
    """Veritabanı ve Redis ping'i yaparak servis durumunu döner."""
    from sqlalchemy import text

    from app.infra.database import engine

    services: dict = {}

    # DB check
    try:
        t0 = time.monotonic()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        services["database"] = {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:
        services["database"] = {"status": "error", "error": str(exc)[:100]}

    # Redis check
    try:
        import redis as redis_lib

        from app.config import settings

        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        services["redis"] = {"status": "ok"}
    except Exception as exc:
        services["redis"] = {"status": "degraded", "error": str(exc)[:100]}

    overall = (
        "ok" if all(s.get("status") == "ok" for s in services.values()) else "degraded"
    )
    return DetailedHealthResponse(
        status=overall,
        services=services,
        version="2026.06.07",
    )


class DbHealthResponse(BaseModel):
    status: str
    latency_ms: float | None = None
    connections: int | None = None
    pool_size: int | None = None


@router.get("/db", response_model=DbHealthResponse, summary="PostgreSQL sağlık durumu")
def db_health(user: CurrentUser) -> DbHealthResponse:
    """Veritabanı ping + bağlantı havuzu istatistikleri."""
    try:
        from sqlalchemy import text

        from app.infra.database import engine

        t0 = time.monotonic()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.monotonic() - t0) * 1000, 1)

        pool = engine.pool
        connections = getattr(pool, "checkedout", lambda: None)()
        pool_size = getattr(pool, "size", lambda: None)()

        return DbHealthResponse(
            status="ok",
            latency_ms=latency_ms,
            connections=connections,
            pool_size=pool_size,
        )
    except Exception as exc:
        return DbHealthResponse(status=f"down: {str(exc)[:80]}")
