"""
Semantic LLM Cache — ayni/benzer prompt'u tekrar sorunca LLM'e gitmeden cevap don.

Mimari:
    1) Cache KEY: sha1(task_type + normalized_user_message + system_message_hash)
       - Exact match => hizli tekrar yolu.
    2) Cache INDEX: Redis Sorted Set icinde {embedding_id: timestamp} —
       cache entry için 768-dim vector ayri HSET'te saklanir.
       - Exact miss ise embedding cosine similarity kontrolu (>= 0.97).
    3) TTL task_type bazli: chat/spec_analysis 24h, test_generation 6h,
       security_audit asla (kritik görev, yeni kod her calistiginda taze lazim).

Redis veri yapisi:
    Key: llmcache:entry:<sha1>
    Type: HASH
    Fields: task_type, user_msg, system_msg, response, embedding (JSON),
            created_at, hits
    TTL: task_type bazli
    Indexe index:
    Key: llmcache:idx:<task_type>
    Type: SORTED SET (score=created_at_ts, member=entry_sha1)
    Semantic lookup: task_type index taranir -> top K recent -> cosine cek.

Flag: ``ai.cache.semantic`` — default True. Kapanirsa komple bypass.

Kazanimlar (beklenen):
    %30-60 cagri azalmasi chat/spec_analysis'te, 0.1-0.5s latency tasarrufu.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Config sabitleri ─────────────────────────────────────────────────────

# Cache TTL (sn) — task_type bazli; 0 = cache'leme
_CACHE_TTL_SECS: dict[str, int] = {
    "chat": 86400,           # 24h
    "spec_analysis": 86400,  # 24h
    "test_generation": 21600,  # 6h (kod evrimiyle taze kalmali)
    "code_generation": 10800,  # 3h
    "chain_builder": 21600,   # 6h
    "security_audit": 0,      # cache'leme — her koşu taze olmali
    "quality_judge": 0,       # asla cache'leme
    "default": 43200,         # 12h
}

# Semantic lookup esigi
_SIMILARITY_THRESHOLD = 0.97

# Semantic lookup için taranacak max kayit (son N)
_SEMANTIC_SCAN_LIMIT = 50

# Entry key prefix
_ENTRY_PREFIX = "llmcache:entry:"
_INDEX_PREFIX = "llmcache:idx:"


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class CacheEntry:
    response: str
    task_type: str
    user_msg: str
    created_at: float
    hits: int
    similarity: float = 1.0  # exact match default
    source: str = "exact"    # "exact" | "semantic"


# ── Redis client (lazy) ──────────────────────────────────────────────────


_redis_client = None
_redis_failed_at: float = 0.0
_REDIS_COOLDOWN = 30.0


def _get_redis():
    """Redis client (lazy). Hata olursa 30s cooldown."""
    global _redis_client, _redis_failed_at
    if _redis_failed_at and (time.monotonic() - _redis_failed_at) < _REDIS_COOLDOWN:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis  # type: ignore
        url = os.environ.get("REDIS_URL") or _settings_redis_url()
        _redis_client = redis.from_url(url)
        # Ping
        _redis_client.ping()
        logger.debug("Semantic cache: Redis baglandi (%s)", url)
        return _redis_client
    except Exception as exc:
        _redis_failed_at = time.monotonic()
        logger.debug("Semantic cache: Redis yok (%s), cache disabled", exc)
        _redis_client = None
        return None


def _settings_redis_url() -> str:
    try:
        from app.config import settings
        return settings.redis_url
    except Exception:
        return "redis://127.0.0.1:6379/0"


# ── Feature flag ────────────────────────────────────────────────────────


def _cache_enabled(tenant_id: Optional[str] = None) -> bool:
    """Feature flag: ai.cache.semantic — default True."""
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.cache.semantic", tenant_id=tenant_id, default=True)
    except Exception:
        return True


# ── Anahtar uretimi ──────────────────────────────────────────────────────


def _normalize_message(text: str) -> str:
    """Normalize edip exact-match recall'i artir: trim, collapse whitespace,
    trailing nokta/bosluk kaldır, lowercase (prompt'un degil sadece anahtar için).
    """
    if not text:
        return ""
    import re
    s = re.sub(r"\s+", " ", text.strip())
    s = s.rstrip(".!?")
    return s.lower()


def _exact_key(task_type: str, user_msg: str, system_msg: Optional[str]) -> str:
    """Exact match SHA1 anahtari."""
    norm_user = _normalize_message(user_msg)
    sys_hash = hashlib.sha1((system_msg or "").encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    raw = f"{task_type}|{norm_user}|{sys_hash}"
    return hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()


def _cosine(a: list[float], b: list[float]) -> float:
    """Kosinus benzerlik. Vektorler nomic-embed-text'ten normalize gelmiyor,
    dolayisiyla tam kosinus hesapla.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    if denom == 0:
        return 0.0
    return dot / denom


# ── Public API ───────────────────────────────────────────────────────────


def cache_get(
    task_type: str,
    user_msg: str,
    system_msg: Optional[str] = None,
    *,
    tenant_id: Optional[str] = None,
) -> Optional[CacheEntry]:
    """
    Cache hit ararsa CacheEntry, miss ise None.

    Once exact key; yoksa task_type index'inde son N kayit kosinus kontrolu.
    """
    if not _cache_enabled(tenant_id):
        return None
    if _CACHE_TTL_SECS.get(task_type, _CACHE_TTL_SECS["default"]) <= 0:
        return None

    r = _get_redis()
    if r is None:
        return None

    ekey = _exact_key(task_type, user_msg, system_msg)

    # 1) Exact match
    try:
        data = r.hgetall(_ENTRY_PREFIX + ekey)
    except Exception as exc:
        logger.debug("cache_get hgetall hatasi: %s", exc)
        return None

    if data:
        entry = _row_to_entry(data)
        if entry:
            _bump_hits_async(r, _ENTRY_PREFIX + ekey)
            logger.debug("semantic_cache EXACT hit: %s", task_type)
            return entry

    # 2) Semantic lookup
    query_emb = _embed_text(user_msg)
    if query_emb is None:
        return None

    try:
        # Index: sorted set desc by timestamp (biz descending istiyoruz, o yuzden ZREVRANGE)
        members = r.zrevrange(_INDEX_PREFIX + task_type, 0, _SEMANTIC_SCAN_LIMIT - 1)
    except Exception as exc:
        logger.debug("cache_get zrevrange hatasi: %s", exc)
        return None

    best_entry: Optional[CacheEntry] = None
    best_sim = 0.0

    for raw_key in members or []:
        key_str = raw_key.decode("utf-8") if isinstance(raw_key, (bytes, bytearray)) else str(raw_key)
        try:
            data = r.hgetall(_ENTRY_PREFIX + key_str)
        except Exception:
            continue
        if not data:
            continue
        entry = _row_to_entry(data)
        if not entry:
            continue

        emb_str = _decode(data.get(b"embedding") or data.get("embedding"))
        if not emb_str:
            continue
        try:
            emb = json.loads(emb_str)
        except Exception:
            continue
        sim = _cosine(query_emb, emb)
        if sim > best_sim:
            best_sim = sim
            best_entry = entry

    if best_entry and best_sim >= _SIMILARITY_THRESHOLD:
        best_entry.similarity = round(best_sim, 4)
        best_entry.source = "semantic"
        logger.debug(
            "semantic_cache SEMANTIC hit: %s (sim=%.4f)", task_type, best_sim
        )
        return best_entry

    return None


def cache_set(
    task_type: str,
    user_msg: str,
    response: str,
    *,
    system_msg: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> bool:
    """Cevabi cache'e yaz. Başarı/hata sessiz."""
    if not _cache_enabled(tenant_id):
        return False
    ttl = _CACHE_TTL_SECS.get(task_type, _CACHE_TTL_SECS["default"])
    if ttl <= 0:
        return False
    if not response or len(response) < 20:
        return False  # cok kisa cevap cache'leme

    r = _get_redis()
    if r is None:
        return False

    query_emb = _embed_text(user_msg)
    if query_emb is None:
        return False  # embedding yoksa semantic lookup yapamayiz

    ekey = _exact_key(task_type, user_msg, system_msg)
    entry_key = _ENTRY_PREFIX + ekey
    now = time.time()

    try:
        pipe = r.pipeline()
        pipe.hset(entry_key, mapping={
            "task_type": task_type,
            "user_msg": user_msg[:4000],
            "system_msg": (system_msg or "")[:2000],
            "response": response,
            "embedding": json.dumps(query_emb),
            "created_at": str(now),
            "hits": "0",
        })
        pipe.expire(entry_key, ttl)
        pipe.zadd(_INDEX_PREFIX + task_type, {ekey: now})
        # Index'i de TTL'le (en uzun TTL + 1h)
        pipe.expire(_INDEX_PREFIX + task_type, ttl + 3600)
        pipe.execute()
        return True
    except Exception as exc:
        logger.debug("cache_set hatasi: %s", exc)
        return False


def cache_stats() -> dict[str, Any]:
    """Cache özet — UI/metrics için."""
    r = _get_redis()
    if r is None:
        return {"enabled": False, "reason": "redis_unavailable"}

    try:
        stats: dict[str, Any] = {
            "enabled": True,
            "threshold": _SIMILARITY_THRESHOLD,
            "by_task_type": [],
            "total_entries": 0,
        }
        # Her task_type'in index uzunlugu
        for task_type in _CACHE_TTL_SECS.keys():
            if task_type == "default":
                continue
            try:
                count = r.zcard(_INDEX_PREFIX + task_type)
                if count and count > 0:
                    stats["by_task_type"].append({
                        "task_type": task_type,
                        "count": int(count),
                        "ttl_secs": _CACHE_TTL_SECS.get(task_type, 0),
                    })
                    stats["total_entries"] = int(stats["total_entries"]) + int(count)
            except Exception:
                pass
        return stats
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}


def cache_clear(task_type: Optional[str] = None) -> int:
    """task_type verilirse sadece o index; verilmezse tüm cache."""
    r = _get_redis()
    if r is None:
        return 0

    deleted = 0
    try:
        if task_type:
            # Tüm entry'leri topla
            members = r.zrange(_INDEX_PREFIX + task_type, 0, -1) or []
            for m in members:
                key_str = m.decode("utf-8") if isinstance(m, (bytes, bytearray)) else str(m)
                r.delete(_ENTRY_PREFIX + key_str)
                deleted += 1
            r.delete(_INDEX_PREFIX + task_type)
        else:
            # Scan tüm llmcache:* key'leri
            for key in r.scan_iter(match="llmcache:*", count=500):
                r.delete(key)
                deleted += 1
    except Exception as exc:
        logger.debug("cache_clear hatasi: %s", exc)
    return deleted


# ── Internal helpers ─────────────────────────────────────────────────────


def _decode(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="ignore")
    return str(v)


def _row_to_entry(data: dict) -> Optional[CacheEntry]:
    """Redis HASH -> CacheEntry."""
    try:
        response = _decode(data.get(b"response") or data.get("response"))
        if not response:
            return None
        task_type = _decode(data.get(b"task_type") or data.get("task_type")) or "unknown"
        user_msg = _decode(data.get(b"user_msg") or data.get("user_msg")) or ""
        created_at_s = _decode(data.get(b"created_at") or data.get("created_at")) or "0"
        hits_s = _decode(data.get(b"hits") or data.get("hits")) or "0"
        return CacheEntry(
            response=response,
            task_type=task_type,
            user_msg=user_msg,
            created_at=float(created_at_s),
            hits=int(hits_s),
        )
    except Exception:
        return None


def _bump_hits_async(r, entry_key: str) -> None:
    """hits sayacini non-blocking artir."""
    try:
        r.hincrby(entry_key, "hits", 1)
    except Exception:
        pass


def _embed_text(text: str) -> Optional[list[float]]:
    """KnowledgeStore embedding infrastructure'ini kullan."""
    try:
        from app.domains.ai.knowledge_store import _embed  # type: ignore
        return _embed(text)
    except Exception as exc:
        logger.debug("_embed_text hatasi: %s", exc)
        return None
