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

# Faz 3.4: Replica health check imports
from app.infra.failover_manager import get_failover_manager
from app.infra.replica_health_check import get_health_checker

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/extended",
    response_model=ExtendedHealth,
    summary="Tüm bağımlılıkların detaylı sağlık durumu",
    response_description="Bileşen listesi + overall durum",
)
def extended(user: Annotated[User, Depends(get_current_user)]) -> ExtendedHealth:
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
def detailed_health(user: Annotated[User, Depends(get_current_user)]) -> DetailedHealthResponse:
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
def db_health(user: Annotated[User, Depends(get_current_user)]) -> DbHealthResponse:
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


# ────────────────────────────────────────────────────────────────────────────
# Faz 3.4: Multi-region read-replica failover health checks
# ────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field


class ReplicaStatusModel(BaseModel):
    """Per-replica health status."""
    name: str
    state: str  # healthy | degraded | unhealthy | promoted
    lag_ms: float
    consecutive_failures: int
    last_check_time: str | None = None


class ReplicaStatusResponse(BaseModel):
    """Replica health + failover status."""
    status: str  # ok | degraded | failover_required
    primary: str | None = None
    replicas: dict[str, ReplicaStatusModel] = Field(default_factory=dict)
    failover_in_progress: bool = False
    last_failover: str | None = None


class FailoverEventResponse(BaseModel):
    """Single failover event record."""
    timestamp: str
    old_primary: str
    new_primary: str
    reason: str
    success: bool
    duration_seconds: float


class PromoteReplicaRequest(BaseModel):
    """Request to promote replica to primary."""
    replica_name: str = Field(..., description="Replica identifier")


class PromoteReplicaResponse(BaseModel):
    """Promotion result."""
    success: bool
    message: str
    new_primary: str | None = None


@router.get(
    "/replica-status",
    response_model=ReplicaStatusResponse,
    summary="Replica sağlık durumu + failover hali (Faz 3.4)",
)
def get_replica_status(user: Annotated[User, Depends(get_current_user)]) -> ReplicaStatusResponse:
    """Get replica health + failover state.

    Queries health checker for:
    - Current primary + replica states
    - Replication lag per replica
    - Failover in-progress flag
    - Last failover timestamp

    Returns:
        ReplicaStatusResponse with detailed replica health.

    Faz 3.4: Multi-region failover orchestration
    """
    from datetime import datetime

    checker = get_health_checker()
    manager = get_failover_manager()

    if not checker:
        return ReplicaStatusResponse(
            status="error",
            primary=None,
            replicas={},
            failover_in_progress=False,
            last_failover=None,
        )

    status_dict = checker.get_replica_status()
    failover_events = checker.get_failover_events(limit=1)

    replicas = {}
    overall_status = "ok"

    if "replicas" in status_dict:
        for name, info in status_dict["replicas"].items():
            replicas[name] = ReplicaStatusModel(
                name=name,
                state=info.get("state", "unknown"),
                lag_ms=info.get("lag_ms", 0),
                consecutive_failures=info.get("consecutive_failures", 0),
                last_check_time=info.get("last_check_time"),
            )

            # Determine overall status
            if info.get("state") == "unhealthy":
                overall_status = "degraded"

    last_failover = None
    if failover_events:
        last_failover = failover_events[0].timestamp.isoformat()

    primary_name = None
    if checker.replicas:
        # Primary is highest-priority replica
        sorted_replicas = sorted(checker.replicas.values(), key=lambda r: r.priority)
        if sorted_replicas:
            primary_name = sorted_replicas[0].name

    return ReplicaStatusResponse(
        status=overall_status,
        primary=primary_name,
        replicas=replicas,
        failover_in_progress=(
            manager.get_status().get("promotion_in_progress", False)
            if manager
            else False
        ),
        last_failover=last_failover,
    )


@router.get(
    "/failover-events",
    response_model=list[FailoverEventResponse],
    summary="Son failover olayları (Faz 3.4)",
)
def get_failover_events(
    user: Annotated[User, Depends(get_current_user)], limit: int = 10
) -> list[FailoverEventResponse]:
    """Get recent failover event history.

    Args:
        limit: Max number of events to return (default 10, max 100).

    Returns:
        List of FailoverEventResponse in chronological order.

    Faz 3.4: Failover event audit trail
    """
    if limit > 100:
        limit = 100

    checker = get_health_checker()
    if not checker:
        return []

    events = checker.get_failover_events(limit=limit)
    return [
        FailoverEventResponse(
            timestamp=e.timestamp.isoformat(),
            old_primary=e.old_primary,
            new_primary=e.new_primary,
            reason=e.reason,
            success=e.success,
            duration_seconds=e.duration_seconds,
        )
        for e in events
    ]
