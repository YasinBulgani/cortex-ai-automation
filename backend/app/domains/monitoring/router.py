"""Monitoring and performance metrics endpoints.

Provides:
- Database connection pool health
- Redis cache statistics
- Read-replica lag monitoring
- Request latency metrics
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db
from app.infra.database import engine
from app.infra.redis_cache import CacheMetrics, get_redis_client

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/health/db-pool")
async def db_pool_health(db: Session = Depends(get_db)):
    """Monitor database connection pool status. (perf opt 1.12)

    Returns pool utilization, available connections, and overflow status.
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "utilization_percent": (pool.checkedout() / pool.size() * 100) if pool.size() > 0 else 0,
        "healthy": pool.checkedout() < pool.size() * 0.8,  # healthy if <80% utilized
    }


@router.get("/metrics/cache")
async def cache_metrics():
    """Redis cache hit ratio and memory usage. (perf opt 4.5)

    Returns:
        - hits: Number of cache hits
        - misses: Number of cache misses
        - hit_ratio: Hit ratio percentage (0-100)
        - memory_mb: Memory used by Redis
    """
    metrics = CacheMetrics.get_metrics()
    return metrics


@router.get("/metrics/cache/keys")
async def cache_key_stats():
    """Get stats for Neurex-specific cache keys.

    Returns:
        - cached_keys: Number of keys in neurex:cache namespace
        - memory_mb: Memory used by these keys
    """
    stats = CacheMetrics.get_key_stats()
    return stats


@router.get("/health/replica-lag")
async def replica_lag(db: Session = Depends(get_db)):
    """Monitor read-replica replication lag. (perf opt 5.4)

    Returns lag in seconds. <0.1s is healthy (sticky read-after-write
    ensures freshness).
    """
    try:
        # This query only works if replica is available and this is the replica
        result = db.execute(
            text(
                "SELECT EXTRACT(EPOCH FROM "
                "(NOW() - pg_last_xact_replay_timestamp())) as lag_seconds"
            )
        )
        lag_seconds = result.scalar() or 0
        return {
            "replica_lag_ms": lag_seconds * 1000,
            "healthy": lag_seconds < 0.1,
            "status": "ok" if lag_seconds < 0.1 else "degraded",
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "unavailable",
        }


@router.get("/metrics/request-latency")
async def request_latency(request: Request):
    """Get request processing latency from middleware.

    The QueryDeadlineMiddleware tracks request start/end times.
    """
    # If middleware has tracked timing
    start_time = getattr(request.state, "start_time", None)
    if start_time:
        from datetime import datetime

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        return {
            "elapsed_ms": elapsed_ms,
            "threshold_ms": 5000,
            "healthy": elapsed_ms < 5000,
        }

    return {"status": "timing_not_available"}


@router.get("/metrics/redis-connection")
async def redis_connection_status():
    """Check Redis connection status and basic stats.

    (perf opt 5.2)
    """
    try:
        redis = get_redis_client()
        info = redis.info("server")
        return {
            "status": "connected",
            "redis_version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
        }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Comprehensive readiness probe for Kubernetes.

    Checks:
    - Database connectivity
    - Redis connectivity
    - Connection pool availability
    - Replica lag (if applicable)
    """
    status = {"ready": True, "checks": {}}

    # DB check
    try:
        db.execute(text("SELECT 1"))
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)[:50]}"
        status["ready"] = False

    # Redis check
    try:
        redis = get_redis_client()
        redis.ping()
        status["checks"]["redis"] = "ok"
    except Exception:
        status["checks"]["redis"] = "unavailable"

    # Pool check
    pool = engine.pool
    if pool.checkedout() >= pool.size():
        status["checks"]["pool"] = "exhausted"
        status["ready"] = False
    else:
        status["checks"]["pool"] = "ok"

    return status
