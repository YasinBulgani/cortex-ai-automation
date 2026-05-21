"""DSL alias corpus'u için embedding tabanlı anlamsal arama indeksi.

Altyapı:
    * AI Gateway'in /ai/embed endpoint'i üzerinden Ollama bge-m3 (veya başka
      multilingual embedding modeli) kullanılır.
    * Her cümleciğin TR + EN alias'ları ve description'u ayrı ayrı embed edilir.
      Aynı action için birden çok satır olur — sorgu ile en yüksek cosine
      similarity sergileyen satırı döneriz.
    * İndeks on-disk olarak `packages/dsl/embeddings/index.npz` altına yazılır.
      Kaynak (source hash) değişmediği sürece pod restart'larında yeniden
      hesaplanmaz.

Tasarım kararları:
    * FAISS kullanılmıyor. ~1K cümlecik × ~10 alias = 10K satır × ~1024 dim →
      10K×1024 float32 matmul aynısı bge-m3 tek inferansından daha hızlı.
    * Sorgu embedding'i cache'lenmez — query çok çeşitli, TTL yönetimi overkill.
    * Rebuild thread-safe. catalog_cache.load() sonrası çağrılır ama başarısız
      olursa search lexical'e düşer.

Public API:
    AliasIndex()                 # singleton tarafından yönetilir
    index.rebuild()              # katalogtan + gateway'den yeniden inşa
    index.search(q, k)           # top-k anlamsal eşleşme
    index.is_ready()             # True → numeric vektörler hazır
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from app.domains.ai.gateway_client import gateway_embed
from app.domains.dsl.loader import catalog_cache
from app.domains.dsl.schemas import DslAction

logger = logging.getLogger(__name__)

# packages/dsl/embeddings — loader ile aynı çerçevede
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_EMBED_DIR = _PROJECT_ROOT / "packages" / "dsl" / "embeddings"
_INDEX_PATH = _EMBED_DIR / "index.npz"
_META_PATH = _EMBED_DIR / "build_info.json"

# Tek bir action için en fazla kaç alias embed edilir (çoğu zaten az)
_MAX_ALIAS_PER_LANG = 6
# Batch boyutu — gateway'e tek seferde gönderilecek metin sayısı
_EMBED_BATCH = 32


@dataclass(frozen=True)
class IndexEntry:
    """Bir embed satırı: action + hangi alias'a ait."""

    action_id: str
    language: str   # "tr" | "en" | "meta" (description)
    text: str       # Embed edilen ham metin


@dataclass(frozen=True)
class SemanticHit:
    action: DslAction
    score: float            # 0..1 cosine
    matched_language: str
    matched_alias: str


def _hash_corpus(entries: list[IndexEntry], model: str) -> str:
    """Corpus + model → rebuild gerekli mi için deterministik hash."""
    payload = json.dumps(
        {"model": model, "rows": [(e.action_id, e.language, e.text) for e in entries]},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _collect_entries(actions: list[DslAction]) -> list[IndexEntry]:
    """Her cümlecik için embed edilecek metin satırlarını topla."""
    rows: list[IndexEntry] = []
    for a in actions:
        aliases = a.aliases or {}
        seen: set[str] = set()
        for lang in ("tr", "en"):
            for alias in (aliases.get(lang) or [])[:_MAX_ALIAS_PER_LANG]:
                alias = (alias or "").strip()
                if not alias or alias.lower() in seen:
                    continue
                seen.add(alias.lower())
                rows.append(IndexEntry(action_id=a.id, language=lang, text=alias))
        # description'u da ekle (meta dili) — TR aramada EN alias'a geçen
        # cümleleri yakalamak için ekstra bir sinyal
        desc = (a.description or "").strip()
        if desc and desc.lower() not in seen:
            rows.append(IndexEntry(action_id=a.id, language="meta", text=desc))
    return rows


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """Cosine için satır bazlı normalize. Sıfır satırı güvenli işler."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class AliasIndex:
    """Thread-safe in-memory + on-disk embedding indeksi."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ready = False
        self._entries: List[IndexEntry] = []
        self._matrix: Optional[np.ndarray] = None  # shape=(N, dim) normalized
        self._model: str = ""
        self._dim: int = 0
        self._built_at: Optional[float] = None
        self._corpus_hash: str = ""

    # ── Public ───────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        with self._lock:
            return self._ready and self._matrix is not None and len(self._entries) > 0

    def info(self) -> dict:
        with self._lock:
            return {
                "ready": self.is_ready(),
                "rows": len(self._entries),
                "dim": self._dim,
                "model": self._model,
                "built_at": self._built_at,
                "corpus_hash": self._corpus_hash,
            }

    def ensure_loaded(self) -> None:
        """İlk çağrıda diskten yüklemeyi dener; disk yoksa rebuild yapmaz.

        Katalog cache'inin yüklenmiş olmasına bağlı değil — sadece ham numpy
        dosyasını okur.
        """
        with self._lock:
            if self._ready or self._matrix is not None:
                return
            self._try_load_from_disk()

    def rebuild(self, *, force: bool = False) -> dict:
        """Katalogtan corpus topla, değişmişse gateway'den embed al, kaydet.

        `force=True` hash aynı olsa bile yeniden hesaplar.
        """
        with self._lock:
            actions = catalog_cache.all()
            entries = _collect_entries(actions)
            if not entries:
                self._reset()
                logger.info("DSL embed index: boş corpus, indeks temizlendi")
                return {"status": "empty", "rows": 0}

            # Eğer diskte uygun hash varsa ve force değilse → yükle
            model = os.environ.get("DSL_EMBEDDING_MODEL", "bge-m3")
            new_hash = _hash_corpus(entries, model)
            if not force and self._corpus_hash == new_hash and self._matrix is not None:
                logger.debug("DSL embed index: corpus değişmemiş, skip")
                return {"status": "skipped", "rows": len(entries)}

            if not force and self._try_load_from_disk(expected_hash=new_hash):
                logger.info(
                    "DSL embed index: diskten yüklendi (%d satır, hash=%s)",
                    len(self._entries),
                    new_hash,
                )
                return {"status": "loaded", "rows": len(self._entries)}

            # Gateway'den embed iste — batch'ler halinde
            logger.info(
                "DSL embed index: rebuild başlıyor — %d satır (model=%s)",
                len(entries),
                model,
            )
            t0 = time.monotonic()
            vectors: list[list[float]] = []
            try:
                for i in range(0, len(entries), _EMBED_BATCH):
                    chunk = entries[i : i + _EMBED_BATCH]
                    data = gateway_embed(
                        [e.text for e in chunk],
                        model=model,
                        correlation_id=f"dsl-index-{i}",
                    )
                    vectors.extend(data["vectors"])
            except RuntimeError as exc:
                logger.warning(
                    "DSL embed index: gateway başarısız, indeks boş kalıyor: %s",
                    exc,
                )
                self._reset()
                return {"status": "gateway_unavailable", "error": str(exc), "rows": 0}

            matrix = _l2_normalize(np.asarray(vectors, dtype=np.float32))
            self._entries = entries
            self._matrix = matrix
            self._model = model
            self._dim = int(matrix.shape[1]) if matrix.size else 0
            self._corpus_hash = new_hash
            self._built_at = time.time()
            self._ready = True
            elapsed = int((time.monotonic() - t0) * 1000)
            logger.info(
                "DSL embed index: rebuild OK — %d satır, dim=%d, süre=%dms",
                len(entries),
                self._dim,
                elapsed,
            )
            self._persist()
            return {"status": "rebuilt", "rows": len(entries), "latency_ms": elapsed}

    def search(
        self,
        query: str,
        *,
        lang: Optional[str] = None,
        k: int = 20,
        min_score: float = 0.3,
    ) -> List[SemanticHit]:
        """Sorgu → top-k cosine eşleşmesi. Index boşsa [] döner."""
        q = (query or "").strip()
        if not q:
            return []
        with self._lock:
            if not self.is_ready() or self._matrix is None:
                return []
            entries = self._entries
            matrix = self._matrix
            model = self._model

        try:
            data = gateway_embed([q], model=model, correlation_id="dsl-query")
            qvec = np.asarray(data["vectors"][0], dtype=np.float32)
        except RuntimeError as exc:
            logger.warning("DSL semantic search: query embed başarısız: %s", exc)
            return []

        qnorm = np.linalg.norm(qvec)
        if qnorm == 0:
            return []
        qvec = qvec / qnorm
        sims = matrix @ qvec  # (N,)

        # Her action için en iyi satırı seç (deduplicate)
        best_per_action: dict[str, Tuple[int, float]] = {}
        for idx, score in enumerate(sims):
            score_f = float(score)
            if score_f < min_score:
                continue
            entry = entries[idx]
            if lang and entry.language not in {lang, "meta"}:
                continue
            cur = best_per_action.get(entry.action_id)
            if cur is None or score_f > cur[1]:
                best_per_action[entry.action_id] = (idx, score_f)

        ranked = sorted(
            best_per_action.items(), key=lambda kv: kv[1][1], reverse=True
        )[:k]

        hits: List[SemanticHit] = []
        for action_id, (entry_idx, score) in ranked:
            action = catalog_cache.get(action_id)
            if action is None:
                continue
            entry = entries[entry_idx]
            hits.append(
                SemanticHit(
                    action=action,
                    score=score,
                    matched_language=entry.language,
                    matched_alias=entry.text,
                )
            )
        return hits

    # ── Özel ─────────────────────────────────────────────────────────────

    def _reset(self) -> None:
        self._entries = []
        self._matrix = None
        self._model = ""
        self._dim = 0
        self._built_at = None
        self._corpus_hash = ""
        self._ready = False

    def _persist(self) -> None:
        try:
            _EMBED_DIR.mkdir(parents=True, exist_ok=True)
            np.savez(
                _INDEX_PATH,
                matrix=self._matrix,
                action_ids=np.asarray([e.action_id for e in self._entries]),
                languages=np.asarray([e.language for e in self._entries]),
                texts=np.asarray([e.text for e in self._entries]),
            )
            _META_PATH.write_text(
                json.dumps(
                    {
                        "model": self._model,
                        "dim": self._dim,
                        "rows": len(self._entries),
                        "corpus_hash": self._corpus_hash,
                        "built_at": self._built_at,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("DSL embed index diske yazılamadı: %s", exc)

    def _try_load_from_disk(self, *, expected_hash: str | None = None) -> bool:
        if not _INDEX_PATH.exists() or not _META_PATH.exists():
            return False
        try:
            meta = json.loads(_META_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        disk_hash = meta.get("corpus_hash", "")
        if expected_hash is not None and disk_hash != expected_hash:
            return False

        try:
            data = np.load(_INDEX_PATH, allow_pickle=False)
            matrix = data["matrix"].astype(np.float32)
            action_ids = data["action_ids"].tolist()
            languages = data["languages"].tolist()
            texts = data["texts"].tolist()
        except (OSError, KeyError, ValueError) as exc:
            logger.warning("DSL embed index: disk okunurken hata: %s", exc)
            return False

        if matrix.shape[0] != len(action_ids):
            return False

        self._entries = [
            IndexEntry(action_id=aid, language=lang, text=txt)
            for aid, lang, txt in zip(action_ids, languages, texts)
        ]
        self._matrix = matrix
        self._model = str(meta.get("model", ""))
        self._dim = int(meta.get("dim", matrix.shape[1] if matrix.size else 0))
        self._corpus_hash = disk_hash
        self._built_at = meta.get("built_at")
        self._ready = True
        return True


# Singleton — app ömrü boyunca paylaşılır
alias_index = AliasIndex()
