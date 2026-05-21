"""Extended health endpoint.

Yol: ``GET /api/v1/health/extended``
Amaç: frontend üst bar'daki health dot'un veri kaynağı.

Rate limit middleware bu endpoint'i de kapsayabilir — frontend polling
30s aralıkla olduğu için sorun değil, ama gelecekte yüksek-frekans ihtiyacı
olursa ``X-Skip-Rate-Limit`` header'ı eklenebilir (ayrı iş).
"""

from __future__ import annotations

import time

from fastapi import APIRouter
from pydantic import BaseModel

from app.domains.health.schemas import ExtendedHealth
from app.domains.health.service import get_extended_health

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/extended",
    response_model=ExtendedHealth,
    summary="Tüm bağımlılıkların detaylı sağlık durumu",
    response_description="Bileşen listesi + overall durum",
)
def extended() -> ExtendedHealth:
    """Postgres, Redis, Engine, AI Gateway, Ollama — tümünün tek seferde durumu."""
    return get_extended_health()


class DbHealthResponse(BaseModel):
    status: str
    latency_ms: float | None = None
    connections: int | None = None
    pool_size: int | None = None


@router.get("/db", response_model=DbHealthResponse, summary="PostgreSQL sağlık durumu")
def db_health() -> DbHealthResponse:
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
