"""Redis multi-layer caching strategy for performance optimization.

Implements:
- Query result caching with TTL strategies
- Cache invalidation patterns
- Cache hit ratio monitoring
- Idempotency key storage
"""

from functools import wraps
from typing import Any, Callable, Optional
import json
import hashlib

from redis import Redis
from app.config import settings


class CacheStrategy:
    """TTL strategies for different data mutation frequencies."""

    IMMUTABLE_TTL = 86400 * 7  # 7 days (never changes: product catalogs, configs)
    MUTABLE_TTL = 3600  # 1 hour (changes occasionally: projects, users)
    SHORT_TTL = 300  # 5 min (frequently changes: test runs, analytics)
    VERY_SHORT_TTL = 60  # 1 min (changes every request: volatile metrics)


# Redis client singleton
_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 3,  # TCP_KEEPINTVL
                3: 5,  # TCP_KEEPCNT
            }
        )
    return _redis_client


def cache_key(key: str) -> str:
    """Normalize cache key with namespace."""
    return f"neurex:cache:{key}"


def redis_cache(
    ttl: Optional[int] = None,
    strategy: str = "MUTABLE_TTL",
    key_prefix: str = "",
):
    """Decorator to cache async function results in Redis.

    Usage:
        @redis_cache(strategy="MUTABLE_TTL", key_prefix="test_cases")
        async def list_test_cases(project_id: str):
            return await db.query(TestCase).filter(...).all()

    Cache key is auto-generated from function name + args.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            arg_str = "|".join(
                str(a) for a in args
                if not hasattr(a, '__dict__')  # skip ORM objects
            )
            kwarg_str = "|".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key_suffix = hashlib.md5(
                f"{arg_str}:{kwarg_str}".encode()
            ).hexdigest()

            full_key = cache_key(f"{key_prefix}:{func.__name__}:{key_suffix}")

            # Try cache hit
            redis = get_redis_client()
            try:
                cached = redis.get(full_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass  # Cache miss or Redis error, fall through

            # Cache miss - compute result
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                cache_ttl = ttl or getattr(CacheStrategy, strategy)
                redis.setex(
                    full_key,
                    cache_ttl,
                    json.dumps(result, default=str)  # str() for datetime etc
                )
            except Exception:
                pass  # Redis error, continue without caching

            return result

        return wrapper
    return decorator


class CacheInvalidation:
    """Smart cache invalidation on mutations."""

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        redis = get_redis_client()
        try:
            keys = redis.keys(cache_key(pattern))
            if keys:
                return redis.delete(*keys)
            return 0
        except Exception:
            return 0

    @staticmethod
    def invalidate_related(entity_type: str, entity_id: str) -> None:
        """Invalidate related cache entries after mutation."""
        patterns = {
            "test_case": [
                "test_cases:*",  # all test case lists
                f"test_case:{entity_id}",  # this test case detail
                "coverage:*",  # coverage changes
                "analytics:*",  # stats change
            ],
            "test_run": [
                "test_runs:*",  # all test run lists
                f"test_run:{entity_id}",  # this run detail
                "analytics:*",  # analytics cache
                "dashboard:*",  # dashboard widgets
            ],
            "project": [
                "projects:*",
                f"project:{entity_id}",
                "test_cases:*",
                "test_runs:*",
                "analytics:*",
            ],
            "defect": [
                "defects:*",
                f"defect:{entity_id}",
                "analytics:*",
            ],
        }

        for pattern in patterns.get(entity_type, []):
            CacheInvalidation.invalidate_pattern(pattern)

    @staticmethod
    def warm_cache_on_startup(data: dict) -> None:
        """Pre-populate cache with critical data on startup."""
        redis = get_redis_client()
        for key, value in data.items():
            try:
                redis.setex(
                    cache_key(key),
                    CacheStrategy.MUTABLE_TTL,
                    json.dumps(value, default=str)
                )
            except Exception:
                pass  # Skip on Redis error


class CacheMetrics:
    """Monitor Redis cache health."""

    @staticmethod
    def get_metrics() -> dict:
        """Return cache statistics."""
        redis = get_redis_client()
        try:
            info = redis.info("stats")
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total = hits + misses

            return {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_ratio": (hits / total * 100) if total > 0 else 0,
                "memory_mb": info.get("used_memory", 0) / 1024 / 1024,
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_key_stats() -> dict:
        """Get stats for neurex cache keys specifically."""
        redis = get_redis_client()
        try:
            keys = redis.keys(cache_key("*"))
            return {
                "cached_keys": len(keys),
                "memory_mb": sum(
                    redis.memory_usage(key) or 0 for key in keys
                ) / 1024 / 1024,
            }
        except Exception:
            return {"cached_keys": 0, "memory_mb": 0}


# Idempotency support (perf opt 2.5)
async def cache_idempotent_response(
    idempotency_key: str,
    response_body: bytes,
    ttl: int = 3600,
) -> None:
    """Cache POST/PUT response for idempotency."""
    redis = get_redis_client()
    try:
        redis.setex(
            cache_key(f"idempotency:{idempotency_key}"),
            ttl,
            response_body.decode() if isinstance(response_body, bytes) else response_body,
        )
    except Exception:
        pass  # Cache error, continue without idempotency


async def get_idempotent_response(idempotency_key: str) -> Optional[str]:
    """Retrieve cached response for idempotent request."""
    redis = get_redis_client()
    try:
        return redis.get(cache_key(f"idempotency:{idempotency_key}"))
    except Exception:
        return None
