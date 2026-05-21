"""
Embeddings Cache — sha256(text) -> vector, Redis TTL 30g.

Ihtiyac:
    knowledge_store._embed her retrieve_hybrid'te Ollama'ya gidiyor.
    Ayni sorgu için ayni vektor — bosuna GPU compute. Cache ile:
    - 50ms -> 2ms latency
    - Ollama yuku %70-90 azalmasi
    - Offline mode: cache hit ise Ollama down olsa bile vector var

Strateji:
    Key:   emb:v1:<model>:<sha256(text[:4000])>
    Value: JSON list[float] (768 dim)
    TTL:   30 gun (1 aydan eski embedding farkli model tag'i olabilir)

Flag: ai.cache.embeddings (default True).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_TTL_SECS = 60 * 60 * 24 * 30  # 30 gun
_KEY_PREFIX = "emb:v1:"
_TEXT_TRUNCATE = 4000  # knowledge_store._embed ile tutarli


# ── Redis (lazy) ────────────────────────────────────────────────────────


_redis_client = None
_redis_failed_at: float = 0.0
_REDIS_COOLDOWN = 30.0


def _get_redis():
    global _redis_client, _redis_failed_at
    if _redis_failed_at and (time.monotonic() - _redis_failed_at) < _REDIS_COOLDOWN:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis  # type: ignore
        url = os.environ.get("REDIS_URL") or _settings_redis_url()
        _redis_client = redis.from_url(url)
        _redis_client.ping()
        return _redis_client
    except Exception as exc:
        _redis_failed_at = time.monotonic()
        logger.debug("embedding_cache: Redis yok (%s), cache disabled", exc)
        _redis_client = None
        return None


def _settings_redis_url() -> str:
    try:
        from app.config import settings
        return settings.redis_url
    except Exception:
        return "redis://127.0.0.1:6379/0"


# ── Feature flag ────────────────────────────────────────────────────────


def _enabled(tenant_id: Optional[str] = None) -> bool:
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.cache.embeddings", tenant_id=tenant_id, default=True)
    except Exception:
        return True


# ── Key uretimi ─────────────────────────────────────────────────────────


def _key(text: str, model: str = "nomic-embed-text") -> str:
    """Cache key. Text normalize edilir (whitespace collapse) - Hit rate'i artirir."""
    import re
    norm = re.sub(r"\s+", " ", (text or "").strip().lower())[:_TEXT_TRUNCATE]
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    return f"{_KEY_PREFIX}{model}:{h[:32]}"


# ── Public API ───────────────────────────────────────────────────────────


def get_cached_embedding(text: str, model: str = "nomic-embed-text") -> Optional[list[float]]:
    """Cache hit ise vector, miss ise None."""
    if not _enabled():
        return None
    r = _get_redis()
    if r is None:
        return None
    try:
        raw = r.get(_key(text, model))
    except Exception as exc:
        logger.debug("get_cached_embedding hatasi: %s", exc)
        return None
    if not raw:
        return None
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        if isinstance(data, list) and len(data) > 0:
            return data
    except Exception as exc:
        logger.debug("embedding_cache parse hatasi: %s", exc)
    return None


def set_cached_embedding(
    text: str,
    vector: list[float],
    model: str = "nomic-embed-text",
    ttl_secs: int = _CACHE_TTL_SECS,
) -> bool:
    """Vector'u cache'e yaz. TTL default 30 gun."""
    if not _enabled():
        return False
    if not text or not vector:
        return False
    r = _get_redis()
    if r is None:
        return False
    try:
        r.setex(_key(text, model), ttl_secs, json.dumps(vector))
        return True
    except Exception as exc:
        logger.debug("set_cached_embedding hatasi: %s", exc)
        return False


def cache_stats() -> dict:
    """Dashboard için — Redis INFO ile hit/miss sayimi yapilamaz (key bazli),
    bu yuzden sadece key sayisi + TTL bilgisi doneriz."""
    r = _get_redis()
    if r is None:
        return {"enabled": False, "reason": "redis_unavailable"}
    try:
        # Scan limit 10K — uretimde daha fazla olabilir ama display için yeter
        count = 0
        for _ in r.scan_iter(match=f"{_KEY_PREFIX}*", count=500):
            count += 1
            if count >= 10000:
                break
        return {
            "enabled": True,
            "approximate_keys": count,
            "ttl_secs": _CACHE_TTL_SECS,
            "ttl_days": _CACHE_TTL_SECS // 86400,
        }
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}


def clear_embedding_cache() -> int:
    """Tüm embedding cache'i sil. Admin op."""
    r = _get_redis()
    if r is None:
        return 0
    try:
        deleted = 0
        for key in r.scan_iter(match=f"{_KEY_PREFIX}*", count=500):
            r.delete(key)
            deleted += 1
        return deleted
    except Exception as exc:
        logger.debug("clear_embedding_cache hatasi: %s", exc)
        return 0
