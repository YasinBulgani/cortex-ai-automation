"""Hafif Redis cache yardımcısı — Redis yoksa in-process dict fallback.

Kullanım:
    from app.infra.cache import cache_get, cache_set, cache_delete, make_key

    # Önce cache'e bak
    cached = cache_get(key)
    if cached is not None:
        return cached

    result = expensive_computation()
    cache_set(key, result, ttl=30)
    return result

TTL saniye cinsindendir. Değer None ise cache miss sayılır.
"""

from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

# ── In-process fallback storage ─────────────────────────────────────────────
# Redis yoksa bu dict kullanılır. Multi-process ortamlarda paylaşılmaz —
# yalnızca dev/test için yeterlidir.
_local_store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)
_MAX_LOCAL_ENTRIES = 1000  # Bellek taşmasını önlemek için üst limit


def _local_get(key: str) -> Any | None:
    """In-process store'dan TTL kontrolüyle oku."""
    entry = _local_store.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        _local_store.pop(key, None)
        return None
    return value


def _local_set(key: str, value: Any, ttl: int) -> None:
    """In-process store'a yaz; boyut limitini aş‍arsa eski girdileri temizle."""
    if len(_local_store) >= _MAX_LOCAL_ENTRIES:
        # Basit eviction: expire olmuş tüm girdileri sil
        now = time.monotonic()
        expired_keys = [k for k, (_, exp) in _local_store.items() if exp <= now]
        for k in expired_keys:
            _local_store.pop(k, None)
        # Hâlâ doluysa en eski 10%'i sil
        if len(_local_store) >= _MAX_LOCAL_ENTRIES:
            to_remove = list(_local_store.keys())[: _MAX_LOCAL_ENTRIES // 10]
            for k in to_remove:
                _local_store.pop(k, None)
    _local_store[key] = (value, time.monotonic() + ttl)


def _local_delete(key: str) -> None:
    _local_store.pop(key, None)


# ── Redis client (opsiyonel) ─────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_redis():
    """Redis bağlantısını tembel olarak oluştur; yoksa None döndür."""
    try:
        from app.config import settings
        import redis as _redis  # noqa: PLC0415

        client = _redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()  # bağlantıyı doğrula
        logger.debug("Cache: Redis aktif (%s)", settings.redis_url)
        return client
    except Exception as exc:  # noqa: BLE001
        logger.info("Cache: Redis bağlantısı kurulamadı (%s) — in-process fallback kullanılıyor.", exc)
        return None


# ── Public API ───────────────────────────────────────────────────────────────

def make_key(*parts: str | int) -> str:
    """Namespace'li cache anahtarı üret.

    Örnek: make_key("dashboard", "global", user_id)
    → "cortex:dashboard:global:<user_id>"
    """
    return "cortex:" + ":".join(str(p) for p in parts)


def cache_get(key: str) -> Any | None:
    """Cache'den değer oku. Miss veya expire ise None döner."""
    redis = _get_redis()
    if redis is not None:
        try:
            raw = redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache get hatası (key=%s): %s — fallback", key, exc)
    return _local_get(key)


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Cache'e değer yaz. ttl saniye cinsindendir."""
    redis = _get_redis()
    if redis is not None:
        try:
            redis.setex(key, ttl, json.dumps(value, default=str))
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache set hatası (key=%s): %s — fallback", key, exc)
    _local_set(key, value, ttl)


def cache_delete(key: str) -> None:
    """Cache girdisini sil (invalidation için)."""
    redis = _get_redis()
    if redis is not None:
        try:
            redis.delete(key)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache delete hatası (key=%s): %s — fallback", key, exc)
    _local_delete(key)


def cache_delete_pattern(pattern: str) -> None:
    """Pattern ile eşleşen tüm cache girdilerini sil (örn. 'cortex:dashboard:*').

    Redis varsa SCAN+DEL kullanır. Fallback'te prefix kontrolü yapar.
    """
    redis = _get_redis()
    if redis is not None:
        try:
            cursor = 0
            while True:
                cursor, keys = redis.scan(cursor, match=pattern, count=100)
                if keys:
                    redis.delete(*keys)
                if cursor == 0:
                    break
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache delete_pattern hatası (pattern=%s): %s — fallback", pattern, exc)
    # In-process fallback: pattern'ı prefix olarak kullan (basit glob desteği)
    prefix = pattern.rstrip("*")
    to_delete = [k for k in list(_local_store.keys()) if k.startswith(prefix)]
    for k in to_delete:
        _local_store.pop(k, None)
