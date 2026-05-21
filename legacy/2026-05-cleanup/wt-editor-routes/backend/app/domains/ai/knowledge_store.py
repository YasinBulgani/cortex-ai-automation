"""
KnowledgeStore — TestwrightAI projesinin sürekli öğrenen hafızası.

Mimari:
  - Embedding: Ollama nomic-embed-text (768 boyut, tamamen local, ücretsiz)
    → Ollama zaten kurulu olduğundan ek kurulum gerekmez
  - Depolama: PostgreSQL + pgvector (projedeki mevcut postgres kullanılır)
  - Maskeleme: IBAN, TC kimlik, e-posta, telefon, kredi kartı → embed öncesi temizlenir

Kaynak türleri (source):
  feature_file   — BDD .feature dosyaları
  execution      — Her test koşusunun sonucu
  insight        — PatternAnalyzer'ın ürettiği AI tespitleri
  docs           — /docs klasöründeki markdown dosyaları
  code_change    — Git commit mesajları + değişen dosya listesi
  error_pattern  — Tekrar eden hata mesajları ve çözümleri
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768
EMBED_MODEL = "nomic-embed-text"
SYSTEM_PROJECT_ID = "__system__"

# Ollama base URL: Docker içinden host makinaya ulaşmak için host.docker.internal
def _ollama_base() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1").replace("/v1", "")

# ── Connection Pool ──────────────────────────────────────────────────────────
import threading as _threading

_ks_pool_lock = _threading.Lock()
_ks_pool: list[Any] = []
_KS_POOL_MAX = 4


def _pool_get_conn(db_url: str):
    """Connection pool'dan baglanti al veya yeni olustur."""
    with _ks_pool_lock:
        while _ks_pool:
            conn = _ks_pool.pop()
            try:
                if not conn.closed:
                    # Test connection
                    conn.cursor().execute("SELECT 1")
                    return conn
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

    import psycopg2
    dsn = db_url.replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    return conn


def _pool_return_conn(conn) -> None:
    """Baglantiyi pool'a geri koy."""
    if conn is None or conn.closed:
        return
    with _ks_pool_lock:
        if len(_ks_pool) < _KS_POOL_MAX:
            _ks_pool.append(conn)
        else:
            try:
                conn.close()
            except Exception:
                pass


# ── Maskeleme Regex Kalıpları ─────────────────────────────────────────────────

_MASK_PATTERNS: list[tuple[re.Pattern, str]] = [
    # IBAN: TR + 24 rakam
    (re.compile(r"\bTR\d{2}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{2}\b", re.I), "[IBAN]"),
    # TC Kimlik: 10-11 basamaklı sıfırla başlamayan rakam dizisi
    (re.compile(r"\b[1-9]\d{9,10}\b"), "[TC_KIMLIK]"),
    # Kredi kartı: 4x4 rakam grupları
    (re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b"), "[KART]"),
    # Türk cep telefonu: 05xx veya +905xx
    (re.compile(r"(?:\+90|0)?\s*5\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b"), "[TEL]"),
    # E-posta
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", re.I), "[EMAIL]"),
    # Şifre benzeri alanlar: password=, şifre= vb.
    (re.compile(r"(?:password|passwd|şifre|parola)\s*[=:]\s*\S+", re.I), "[SIFRE]"),
]

# ── Embedding Cache (LRU + TTL) ─────────────────────────────────────────────

_EMBED_CACHE_MAX = 256
_EMBED_CACHE_TTL = 300  # 5 dakika

_embed_cache: OrderedDict[str, tuple[list[float], float]] = OrderedDict()


def _embed_cache_key(text: str) -> str:
    """Metin icin cache anahtari — hash kullan (bellek tasarrufu)."""
    return hashlib.sha256(text[:4000].encode("utf-8", errors="replace")).hexdigest()[:32]


def _embed_cached(text: str) -> list[float] | None:
    """Cache'den embedding al. Yoksa veya expired ise None."""
    key = _embed_cache_key(text)
    if key in _embed_cache:
        vec, ts = _embed_cache[key]
        if (time.time() - ts) < _EMBED_CACHE_TTL:
            _embed_cache.move_to_end(key)
            return vec
        else:
            del _embed_cache[key]
    return None


def _embed_store(text: str, vec: list[float]) -> None:
    """Embedding'i cache'e kaydet."""
    key = _embed_cache_key(text)
    _embed_cache[key] = (vec, time.time())
    if len(_embed_cache) > _EMBED_CACHE_MAX:
        _embed_cache.popitem(last=False)


# ── Veri Sınıfları ────────────────────────────────────────────────────────────

@dataclass
class KnowledgeChunk:
    content: str
    source: str
    metadata: dict[str, Any]
    similarity: float = 0.0


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────

def mask_sensitive(text: str) -> str:
    """Hassas verileri embed etmeden önce maskele."""
    for pattern, replacement in _MASK_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _embed(text: str, max_retries: int = 2) -> list[float] | None:
    """Ollama nomic-embed-text ile metni vektore donustur. Erisilemezse None dondur.
    Retry destekli — gecici hatalarda (timeout, connection reset) yeniden dener.
    """
    # Cache kontrolu
    cached = _embed_cached(text)
    if cached is not None:
        return cached

    import urllib.request
    import urllib.error

    masked = mask_sensitive(text)
    truncated = masked[:4000]  # RAG context arttirildi: 2000 → 4000
    payload = json.dumps({"model": EMBED_MODEL, "input": truncated}).encode()
    url = f"{_ollama_base()}/api/embed"

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                embeddings = data.get("embeddings") or data.get("embedding")
                if embeddings:
                    vec = embeddings[0] if isinstance(embeddings[0], list) else embeddings
                    _embed_store(text, vec)
                    return vec
                logger.warning("Ollama embedding bos yanit dondurdu (attempt %d)", attempt)
        except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
            if attempt < max_retries:
                wait = 1.0 * attempt
                logger.debug("Ollama embedding retry %d/%d (%.1fs): %s", attempt, max_retries, wait, e)
                time.sleep(wait)
            else:
                logger.warning("Ollama embedding %d denemede basarisiz: %s", max_retries, e)
        except Exception as e:
            logger.warning("Ollama embedding beklenmeyen hata: %s", e)
            break
    return None


async def _embed_async(text: str) -> list[float] | None:
    """Async embedding — event loop'u bloklamaz."""
    import asyncio
    cached = _embed_cached(text)
    if cached is not None:
        return cached
    return await asyncio.to_thread(_embed, text)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """İki normalize vektör arasındaki kosinüs benzerliği."""
    return sum(x * y for x, y in zip(a, b))


# ── KnowledgeStore ────────────────────────────────────────────────────────────

class KnowledgeStore:
    """
    Projenin kalıcı ve büyüyen hafızası.

    Kullanım:
        store = KnowledgeStore(db_url)
        store.ingest("Login testi fail etti: TimeoutError", source="execution", metadata={...})
        chunks = store.retrieve("login timeout neden?", top_k=5)
    """

    def __init__(self, db_url: str | None = None, project_id: str | None = None):
        self._db_url = db_url or self._get_db_url()
        self._conn = None
        self._project_id = project_id
        self._project_scope_supported: bool | None = None

    # ── Bağlantı ─────────────────────────────────────────────────────────────

    @staticmethod
    def _get_db_url() -> str:
        try:
            from app.config import settings
            return settings.database_url
        except Exception:
            import os
            return os.environ.get(
                "DATABASE_URL",
                "postgresql://twai_user:twai_pass@127.0.0.1:5432/twai_db",
            )

    def _get_conn(self):
        """psycopg2 baglantisini pool'dan al (lazy)."""
        if self._conn is None or self._conn.closed:
            self._conn = _pool_get_conn(self._db_url)
        return self._conn

    def _resolve_project_id(
        self,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        require_scope: bool,
    ) -> str | None:
        resolved = (project_id or self._project_id or (metadata or {}).get("project_id") or "").strip()
        if resolved:
            return resolved
        if require_scope:
            return None
        return SYSTEM_PROJECT_ID

    def _supports_project_scope(self, cur=None) -> bool:
        if self._project_scope_supported is not None:
            return self._project_scope_supported

        owns_cursor = cur is None
        if cur is None:
            conn = self._get_conn()
            cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'project_knowledge'
                  AND column_name = 'project_id'
                """
            )
            self._project_scope_supported = cur.fetchone() is not None
        except Exception:
            self._project_scope_supported = False
        finally:
            if owns_cursor:
                cur.close()

        return bool(self._project_scope_supported)

    # ── Yazma ────────────────────────────────────────────────────────────────

    def ingest(
        self,
        text: str,
        source: str,
        metadata: dict[str, Any] | None = None,
        project_id: str | None = None,
    ) -> bool:
        """
        Yeni bilgiyi hafızaya kaydet.

        Args:
            text:     Saklanacak metin (hassas veriler otomatik maskelenir)
            source:   Kaynak türü — feature_file | execution | insight |
                      docs | code_change | error_pattern
            metadata: Ek bilgi (tarih, test_id, dosya adı vb.)

        Returns:
            True → başarılı, False → embedding modeli yoksa (metin yine kaydedilir)
        """
        if not text or not text.strip():
            return False

        embedding = _embed(text)
        masked_text = mask_sensitive(text)
        metadata = dict(metadata or {})
        scoped_project_id = self._resolve_project_id(project_id, metadata, require_scope=False)
        metadata.setdefault("project_id", scoped_project_id)

        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                supports_project_scope = self._supports_project_scope(cur)
                if embedding is not None:
                    if supports_project_scope:
                        cur.execute(
                            """
                            INSERT INTO project_knowledge
                                (project_id, content, embedding, source, metadata, embedding_vec)
                            VALUES (%s, %s, %s, %s, %s,
                                CASE
                                    WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
                                    THEN %s::vector
                                    ELSE NULL
                                END
                            )
                            """,
                            (
                                scoped_project_id,
                                masked_text,
                                json.dumps(embedding),
                                source,
                                json.dumps(metadata),
                                "[" + ",".join(map(str, embedding)) + "]",
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO project_knowledge
                                (content, embedding, source, metadata, embedding_vec)
                            VALUES (%s, %s, %s, %s,
                                CASE
                                    WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
                                    THEN %s::vector
                                    ELSE NULL
                                END
                            )
                            """,
                            (
                                masked_text,
                                json.dumps(embedding),
                                source,
                                json.dumps(metadata),
                                "[" + ",".join(map(str, embedding)) + "]",
                            ),
                        )
                else:
                    # Model yoksa sadece metin kaydet
                    if supports_project_scope:
                        cur.execute(
                            "INSERT INTO project_knowledge (project_id, content, source, metadata) VALUES (%s, %s, %s, %s)",
                            (scoped_project_id, masked_text, source, json.dumps(metadata)),
                        )
                    else:
                        cur.execute(
                            "INSERT INTO project_knowledge (content, source, metadata) VALUES (%s, %s, %s)",
                            (masked_text, source, json.dumps(metadata)),
                        )
            return embedding is not None
        except Exception as e:
            logger.warning("KnowledgeStore.ingest hatası: %s", e)
            return False

    def ingest_batch(self, items: list[dict], project_id: str | None = None) -> int:
        """
        Toplu kayıt.

        items: [{"text": ..., "source": ..., "metadata": ...}, ...]
        Başarılı kayıt sayısını döndürür.
        """
        count = 0
        for item in items:
            item_project_id = item.get("project_id") or project_id
            if self.ingest(
                item.get("text", ""),
                item.get("source", "unknown"),
                item.get("metadata"),
                project_id=item_project_id,
            ):
                count += 1
        return count

    # ── Okuma ────────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        sources: list[str] | None = None,
        min_similarity: float = 0.30,
        project_id: str | None = None,
    ) -> list[KnowledgeChunk]:
        """
        Sorguya en yakın bilgileri getir.

        Args:
            query:          Arama sorusu
            top_k:          Kaç sonuç dönsün
            sources:        Belirli kaynaklarla filtrele (None = hepsi)
            min_similarity: Bu eşiğin altındaki sonuçları atla

        Returns:
            Benzerliğe göre sıralı KnowledgeChunk listesi
        """
        scoped_project_id = self._resolve_project_id(project_id, require_scope=True)
        if not scoped_project_id:
            logger.warning("KnowledgeStore.retrieve project_id olmadan reddedildi")
            return []

        query_embedding = _embed(query)
        if query_embedding is None:
            return self._fallback_keyword_search(query, top_k, sources, scoped_project_id)

        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                if not self._supports_project_scope(cur):
                    logger.warning(
                        "KnowledgeStore.retrieve project scope migration'i bekliyor; project_id=%s",
                        scoped_project_id,
                    )
                    return []
                # pgvector varsa native kosinüs araması yap
                if self._has_pgvector(cur):
                    return self._vector_search(
                        cur, query_embedding, top_k, sources, min_similarity, scoped_project_id
                    )
                else:
                    return self._python_similarity_search(
                        cur, query_embedding, top_k, sources, min_similarity, scoped_project_id
                    )
        except Exception as e:
            logger.warning("KnowledgeStore.retrieve hatası: %s", e)
            return []

    async def retrieve_async(
        self,
        query: str,
        top_k: int = 5,
        sources: list[str] | None = None,
        min_similarity: float = 0.30,
        project_id: str | None = None,
    ) -> list[KnowledgeChunk]:
        """Async retrieve — senkron retrieve'i thread pool'da calistir, event loop'u bloklamaz."""
        import asyncio
        return await asyncio.to_thread(
            self.retrieve, query, top_k, sources, min_similarity, project_id
        )

    def _vector_search(self, cur, query_vec, top_k, sources, min_sim, project_id: str) -> list[KnowledgeChunk]:
        """pgvector native IVFFLAT araması (en hızlı)."""
        vec_str = "[" + ",".join(map(str, query_vec)) + "]"

        cur.execute(
            f"""
            SELECT content, source, metadata,
                   1 - (embedding_vec <=> %s::vector) AS similarity
            FROM project_knowledge
            WHERE project_id = %s
              AND embedding_vec IS NOT NULL
            {"AND source = ANY(%s)" if sources else ""}
            ORDER BY embedding_vec <=> %s::vector
            LIMIT %s
            """,
            ([vec_str, project_id] + ([sources] if sources else []) + [vec_str, top_k]),
        )
        rows = cur.fetchall()
        return [
            KnowledgeChunk(
                content=r[0], source=r[1],
                metadata=r[2] or {}, similarity=float(r[3])
            )
            for r in rows if float(r[3]) >= min_sim
        ]

    def _python_similarity_search(
        self,
        cur,
        query_vec,
        top_k,
        sources,
        min_sim,
        project_id: str,
    ) -> list[KnowledgeChunk]:
        """pgvector olmadığında Python'da kosinüs hesapla (fallback)."""
        where = "WHERE project_id = %s AND embedding IS NOT NULL"
        params: list = [project_id]
        if sources:
            where += " AND source = ANY(%s)"
            params.append(sources)

        cur.execute(f"SELECT content, source, metadata, embedding FROM project_knowledge {where} LIMIT 200", params)
        rows = cur.fetchall()

        results = []
        for content, source, metadata, emb_json in rows:
            try:
                stored_vec = json.loads(emb_json)
                sim = _cosine_similarity(query_vec, stored_vec)
                if sim >= min_sim:
                    results.append(KnowledgeChunk(
                        content=content, source=source,
                        metadata=metadata or {}, similarity=sim,
                    ))
            except Exception:
                continue

        results.sort(key=lambda c: c.similarity, reverse=True)
        return results[:top_k]

    def _fallback_keyword_search(
        self,
        query: str,
        top_k: int,
        sources: list[str] | None,
        project_id: str,
    ) -> list[KnowledgeChunk]:
        """Embedding yoksa basit keyword arama."""
        try:
            conn = self._get_conn()
            if not self._supports_project_scope():
                logger.warning(
                    "KnowledgeStore keyword search project scope migration'i bekliyor; project_id=%s",
                    project_id,
                )
                return []
            keywords = [w for w in query.lower().split() if len(w) > 3]
            if not keywords:
                return []
            conditions = " OR ".join(["LOWER(content) LIKE %s"] * len(keywords))
            params: list = [project_id] + [f"%{kw}%" for kw in keywords]
            where = f"WHERE project_id = %s AND ({conditions})"
            if sources:
                where += " AND source = ANY(%s)"
                params.append(sources)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT content, source, metadata FROM project_knowledge {where} LIMIT %s",
                    params + [top_k],
                )
                return [
                    KnowledgeChunk(content=r[0], source=r[1], metadata=r[2] or {}, similarity=0.5)
                    for r in cur.fetchall()
                ]
        except Exception:
            return []

    # ── İstatistik ────────────────────────────────────────────────────────────

    def stats(self, project_id: str | None = None) -> dict:
        """Hafıza istatistiklerini döndür."""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                scoped_project_id = self._resolve_project_id(project_id, require_scope=False)
                supports_project_scope = self._supports_project_scope(cur)
                params: list[Any] = []
                where = ""
                if supports_project_scope and scoped_project_id:
                    where = "WHERE project_id = %s"
                    params.append(scoped_project_id)
                cur.execute(
                    f"""
                    SELECT source, COUNT(*) as count,
                           MAX(created_at) as last_update
                    FROM project_knowledge
                    {where}
                    GROUP BY source
                    ORDER BY count DESC
                    """,
                    params,
                )
                rows = cur.fetchall()
                total = sum(r[1] for r in rows)
                return {
                    "total": total,
                    "project_id": scoped_project_id if supports_project_scope else None,
                    "project_scope_supported": supports_project_scope,
                    "by_source": [
                        {
                            "source": r[0],
                            "count": r[1],
                            "last_update": r[2].isoformat() if r[2] else None,
                        }
                        for r in rows
                    ],
                    "embedding_model": EMBED_MODEL,
                    "embedding_dim": EMBEDDING_DIM,
                }
        except Exception as e:
            return {"total": 0, "error": str(e)}

    # ── Yardımcılar ───────────────────────────────────────────────────────────

    @staticmethod
    def _has_pgvector(cur) -> bool:
        try:
            cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            return cur.fetchone() is not None
        except Exception:
            return False

    def close(self) -> None:
        """Baglantiyi pool'a geri koy."""
        if self._conn is not None:
            _pool_return_conn(self._conn)
            self._conn = None

    def __del__(self):
        self.close()
