"""Per-user LLM rate limiter — token butcesi ve istek limiti."""

from __future__ import annotations

from functools import lru_cache
import logging
import os
import secrets
import threading
import time
from typing import Any, Dict

from app.config import settings

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
MAX_REQUESTS_PER_MINUTE = 30
MAX_TOKENS_PER_HOUR = 500_000
MAX_TOKENS_PER_DAY = 2_000_000

_REDIS_REQ_PREFIX = "bgts:llm:req:"
_REDIS_TOKEN_PREFIX = "bgts:llm:tokens:"

# ── In-memory fallback state ─────────────────────────────────────────
_lock = threading.Lock()
_usage_log: Dict[str, list] = {}
_minute_counters: Dict[str, list] = {}


def _redis_required() -> bool:
    forced = os.getenv("LLM_RATE_LIMIT_REDIS_REQUIRED", "").lower() in {"1", "true", "yes"}
    return forced or settings.is_production_like


@lru_cache(maxsize=1)
def _get_redis_client():
    required = _redis_required()
    try:
        import redis
    except ImportError as exc:
        if required:
            raise RuntimeError(
                "LLM rate limiter icin redis bagimliligi zorunlu "
                "(LLM_RATE_LIMIT_REDIS_REQUIRED/production)."
            ) from exc
        return None

    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        if required:
            client.ping()
        return client
    except Exception as exc:
        if required:
            raise RuntimeError(
                "LLM rate limiter icin redis baglantisi zorunlu fakat ulasilamiyor."
            ) from exc
        return None


def _cleanup_old_entries(user_id: str, now: float) -> None:
    if user_id in _usage_log:
        cutoff = now - 86400
        _usage_log[user_id] = [(ts, tok) for ts, tok in _usage_log[user_id] if ts > cutoff]
    if user_id in _minute_counters:
        cutoff = now - 60
        _minute_counters[user_id] = [ts for ts in _minute_counters[user_id] if ts > cutoff]


def _token_member(tokens_used: int) -> str:
    return f"{max(int(tokens_used), 0)}|{secrets.token_hex(6)}"


def _parse_token_member(value: str) -> int:
    head = value.split("|", 1)[0]
    try:
        return max(int(head), 0)
    except ValueError:
        return 0


def _redis_usage_snapshot(redis_client, user_id: str, now: float) -> tuple[int, int, int]:
    req_key = f"{_REDIS_REQ_PREFIX}{user_id}"
    token_key = f"{_REDIS_TOKEN_PREFIX}{user_id}"
    minute_cutoff = now - 60
    hour_cutoff = now - 3600
    day_cutoff = now - 86400

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(req_key, 0, minute_cutoff)
    pipe.zremrangebyscore(token_key, 0, day_cutoff)
    pipe.zcard(req_key)
    pipe.zrangebyscore(token_key, hour_cutoff, now)
    pipe.zrangebyscore(token_key, day_cutoff, now)
    _, _, minute_reqs, hour_entries, day_entries = pipe.execute()

    hour_tokens = sum(_parse_token_member(entry) for entry in hour_entries)
    day_tokens = sum(_parse_token_member(entry) for entry in day_entries)
    return int(minute_reqs), int(hour_tokens), int(day_tokens)


def check_llm_rate_limit(user_id: str) -> None:
    """Check whether user can issue a new LLM request."""
    from fastapi import HTTPException

    now = time.time()
    try:
        redis_client = _get_redis_client()
    except RuntimeError as exc:
        logger.error("LLM rate limiter backend unavailable: %s", exc)
        raise HTTPException(503, "LLM rate limiter backend ulasilamaz durumda") from exc

    if redis_client is not None:
        try:
            minute_reqs, hour_tokens, day_tokens = _redis_usage_snapshot(redis_client, user_id, now)
        except Exception as exc:
            if _redis_required():
                raise HTTPException(503, "LLM rate limiter backend ulasilamaz durumda") from exc
            logger.warning("LLM redis limiter okunamadi, memory fallback kullanilacak: %s", exc)
            redis_client = None
        else:
            if minute_reqs >= MAX_REQUESTS_PER_MINUTE:
                raise HTTPException(
                    status_code=429,
                    detail=f"LLM istek limiti asildi ({MAX_REQUESTS_PER_MINUTE}/dakika). Lutfen biraz bekleyin.",
                )
            if hour_tokens >= MAX_TOKENS_PER_HOUR:
                raise HTTPException(
                    status_code=429,
                    detail=f"Saatlik token limiti asildi ({MAX_TOKENS_PER_HOUR:,} token). Bir saat sonra tekrar deneyin.",
                )
            if day_tokens >= MAX_TOKENS_PER_DAY:
                raise HTTPException(
                    status_code=429,
                    detail=f"Gunluk token limiti asildi ({MAX_TOKENS_PER_DAY:,} token). Yarin tekrar deneyin.",
                )
            return

    with _lock:
        _cleanup_old_entries(user_id, now)
        minute_reqs = _minute_counters.get(user_id, [])
        if len(minute_reqs) >= MAX_REQUESTS_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=f"LLM istek limiti asildi ({MAX_REQUESTS_PER_MINUTE}/dakika). Lutfen biraz bekleyin.",
            )
        hour_cutoff = now - 3600
        hour_tokens = sum(tok for ts, tok in _usage_log.get(user_id, []) if ts > hour_cutoff)
        if hour_tokens >= MAX_TOKENS_PER_HOUR:
            raise HTTPException(
                status_code=429,
                detail=f"Saatlik token limiti asildi ({MAX_TOKENS_PER_HOUR:,} token). Bir saat sonra tekrar deneyin.",
            )
        day_tokens = sum(tok for _, tok in _usage_log.get(user_id, []))
        if day_tokens >= MAX_TOKENS_PER_DAY:
            raise HTTPException(
                status_code=429,
                detail=f"Gunluk token limiti asildi ({MAX_TOKENS_PER_DAY:,} token). Yarin tekrar deneyin.",
            )


def record_llm_usage(user_id: str, tokens_used: int = 0) -> None:
    """Record one request and token usage."""
    now = time.time()
    try:
        redis_client = _get_redis_client()
    except RuntimeError:
        if _redis_required():
            raise
        redis_client = None

    if redis_client is not None:
        try:
            req_key = f"{_REDIS_REQ_PREFIX}{user_id}"
            token_key = f"{_REDIS_TOKEN_PREFIX}{user_id}"
            pipe = redis_client.pipeline()
            pipe.zadd(req_key, {secrets.token_hex(8): now})
            pipe.zremrangebyscore(req_key, 0, now - 60)
            pipe.expire(req_key, 120)
            pipe.zadd(token_key, {_token_member(tokens_used): now})
            pipe.zremrangebyscore(token_key, 0, now - 86400)
            pipe.expire(token_key, 90000)
            pipe.execute()
            return
        except Exception as exc:
            if _redis_required():
                raise RuntimeError("LLM rate limiter redis yazimi basarisiz") from exc
            logger.warning("LLM redis limiter yazimi basarisiz, memory fallback: %s", exc)

    with _lock:
        _minute_counters.setdefault(user_id, []).append(now)
        _usage_log.setdefault(user_id, []).append((now, max(int(tokens_used), 0)))


def get_user_usage(user_id: str) -> Dict[str, Any]:
    """Get current usage stats for a user."""
    now = time.time()
    try:
        redis_client = _get_redis_client()
    except RuntimeError:
        if _redis_required():
            raise
        redis_client = None

    if redis_client is not None:
        minute_reqs, hour_tokens, day_tokens = _redis_usage_snapshot(redis_client, user_id, now)
        return {
            "requests_this_minute": minute_reqs,
            "max_requests_per_minute": MAX_REQUESTS_PER_MINUTE,
            "tokens_this_hour": hour_tokens,
            "max_tokens_per_hour": MAX_TOKENS_PER_HOUR,
            "tokens_today": day_tokens,
            "max_tokens_per_day": MAX_TOKENS_PER_DAY,
        }

    with _lock:
        _cleanup_old_entries(user_id, now)
        minute_reqs = len(_minute_counters.get(user_id, []))
        hour_cutoff = now - 3600
        hour_tokens = sum(tok for ts, tok in _usage_log.get(user_id, []) if ts > hour_cutoff)
        day_tokens = sum(tok for _, tok in _usage_log.get(user_id, []))
        return {
            "requests_this_minute": minute_reqs,
            "max_requests_per_minute": MAX_REQUESTS_PER_MINUTE,
            "tokens_this_hour": hour_tokens,
            "max_tokens_per_hour": MAX_TOKENS_PER_HOUR,
            "tokens_today": day_tokens,
            "max_tokens_per_day": MAX_TOKENS_PER_DAY,
        }
