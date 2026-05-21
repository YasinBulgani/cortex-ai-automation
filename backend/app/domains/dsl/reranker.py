"""DSL anlamsal arama için cross-encoder reranker katmanı.

Neden gerekli:
    embedding_index.py bge-m3 ile top-K **dense** retrieval yapıyor. Bu yöntem
    hızlı (N×1024 matmul) ama bi-encoder olduğu için query ve candidate ayrı
    ayrı embed edilip sadece vektör uzayında eşleştiriliyor. Bu da Türkçe
    parafraz eşleşmelerinde ("İletişim formunu aç" ↔ "open_url") zayıf
    kalabiliyor — eval raporunda bazı adımların 0.10-0.36 cosine skorla
    yanlış action'a düştüğü görülüyor.

Çözüm:
    Retrieval sonrası bir cross-encoder (query + candidate'ı birlikte işleyen)
    ile yeniden sıralama (reranking). Türkçe triplet verisiyle fine-tune
    edilmiş ``seroe/bge-reranker-v2-m3-turkish-triplet`` bge-m3 embedding'leri
    ile native uyumlu olduğu için ek iş yok — top-20 aday küçük model
    tarafından saniyenin küçük bir kesrinde yeniden skorlanır.

Tasarım kararları:
    * Opsiyonel bağımlılık. ``sentence-transformers`` yoksa veya
      ``AI_MODEL_RERANKER_ENABLED != true`` ise modül pass-through davranır.
      Core embedding arama yolu bozulmaz.
    * Lazy init. Model ağır (~600 MB). İlk ``rerank()`` çağrısında yüklenir,
      sonraki çağrılarda RAM'de kalır. Uygulama startup süresi etkilenmez.
    * Thread-safe. ``CrossEncoder.predict`` GIL altında ve ``torch`` inferans
      tarafı re-entrant; kendi lock'umuzla yüklemeyi tek sefere indiriyoruz.
    * Model adı env ile override edilebilir (kullanıcı başka Turkish/MULTI
      reranker seçmek isterse).

Public API:
    reranker.is_enabled()                            → bool
    reranker.rerank(query, pairs, top_k)             → yeniden sıralanmış subset
    reranker.info()                                  → debug/telemetri

Kullanım örneği (embedding_index içinden):
    from app.domains.dsl.reranker import reranker
    if reranker.is_enabled():
        hits = reranker.rerank(query, hits, top_k=5)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import List, Sequence, TypeVar

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class DslReranker:
    """Thread-safe, lazy, opsiyonel cross-encoder reranker.

    Dış bağımlılık (``sentence-transformers``) bulunamazsa veya feature
    flag kapalıysa sessiz pass-through yapar.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._model = None  # type: ignore[assignment]
        self._load_attempted = False
        self._load_failed_reason: str | None = None
        self._loaded_at: float | None = None

    # ── Public ────────────────────────────────────────────────────────────

    def is_enabled(self) -> bool:
        """Feature flag açık mı? Henüz yüklemeyi tetiklemez."""
        return _env_bool("AI_MODEL_RERANKER_ENABLED", default=False)

    def info(self) -> dict:
        with self._lock:
            return {
                "enabled": self.is_enabled(),
                "model": self._resolved_model_name(),
                "loaded": self._model is not None,
                "loaded_at": self._loaded_at,
                "load_attempted": self._load_attempted,
                "load_failed_reason": self._load_failed_reason,
                "top_k_in": _env_int("AI_MODEL_RERANKER_TOP_K_IN", 20),
                "top_k_out": _env_int("AI_MODEL_RERANKER_TOP_K_OUT", 5),
                "device": os.environ.get("AI_MODEL_RERANKER_DEVICE", "cpu"),
            }

    def rerank(
        self,
        query: str,
        candidates: Sequence[_T],
        *,
        text_of: "callable[[_T], str]",
        top_k: int | None = None,
    ) -> List[_T]:
        """Cross-encoder ile yeniden sırala.

        Args:
            query: Kullanıcının sorgu metni.
            candidates: retrieval sonucunda gelen adaylar (opaque tip).
            text_of: Her adayın reranker'a verilecek metnini üreten fonksiyon
                (candidate → str). embedding_index.SemanticHit için genelde
                ``lambda h: h.matched_alias`` veya action description.
            top_k: Geri döndürülecek adet. None → ``AI_MODEL_RERANKER_TOP_K_OUT``.

        Return:
            ``candidates`` subset'i, cross-encoder skoruna göre azalan sırada.
            Eğer reranker devre dışı, model yüklenememiş veya ``candidates``
            boşsa orijinal liste (top_k ile kırpılmış) döner.
        """
        if not candidates:
            return []

        k_out = top_k if top_k is not None else _env_int("AI_MODEL_RERANKER_TOP_K_OUT", 5)

        if not self.is_enabled():
            return list(candidates)[:k_out]

        # Tek adayda rerank mantıksız — model yüklemeyi de tetiklemeyelim
        if len(candidates) == 1:
            return list(candidates)

        model = self._ensure_loaded()
        if model is None:
            # Lazy load başarısız olduysa retrieval sırasını bozmayız
            return list(candidates)[:k_out]

        try:
            pairs = [(query, text_of(c)) for c in candidates]
            scores = model.predict(pairs)  # numpy veya list[float]
        except Exception as exc:  # pragma: no cover - production guard
            logger.warning(
                "DSL reranker: predict başarısız, retrieval sırası korunuyor: %s",
                exc,
            )
            return list(candidates)[:k_out]

        # Skor + orijinal indeks ile stabil sıralama (tie'da retrieval sırası korunur)
        indexed = list(enumerate(candidates))
        indexed.sort(key=lambda pair: (-float(scores[pair[0]]), pair[0]))
        return [c for _, c in indexed[:k_out]]

    # ── Özel ──────────────────────────────────────────────────────────────

    def _resolved_model_name(self) -> str:
        return os.environ.get(
            "AI_MODEL_RERANKER",
            "seroe/bge-reranker-v2-m3-turkish-triplet",
        )

    def _ensure_loaded(self):  # type: ignore[no-untyped-def]
        """İlk çağrıda modeli yükle, sonraki çağrılarda mevcut nesneyi dön.

        Başarısız yüklemeyi tekrar tekrar denemez — sessiz pass-through'a
        düşer. Bu davranış CI/dev makinelerinde disk/ağ erişimi olmayan
        senaryolarda backend'i kırmamak için.
        """
        with self._lock:
            if self._model is not None:
                return self._model
            if self._load_attempted:
                return None
            self._load_attempted = True
            model_name = self._resolved_model_name()
            device = os.environ.get("AI_MODEL_RERANKER_DEVICE", "cpu")
            try:
                # Lazy import: opsiyonel dependency
                from sentence_transformers import CrossEncoder  # type: ignore
            except ImportError as exc:
                self._load_failed_reason = (
                    "sentence-transformers paketi kurulu değil "
                    "(pip install sentence-transformers)"
                )
                logger.warning(
                    "DSL reranker: devre dışı — %s", self._load_failed_reason
                )
                return None

            t0 = time.monotonic()
            try:
                self._model = CrossEncoder(model_name, device=device)
            except Exception as exc:  # pragma: no cover - network/disk hatası
                self._load_failed_reason = f"Model yüklenemedi: {exc}"
                logger.warning(
                    "DSL reranker: %s (model=%s, device=%s)",
                    self._load_failed_reason,
                    model_name,
                    device,
                )
                return None

            elapsed_ms = int((time.monotonic() - t0) * 1000)
            self._loaded_at = time.time()
            logger.info(
                "DSL reranker: model yüklendi — %s (device=%s, süre=%dms)",
                model_name,
                device,
                elapsed_ms,
            )
            return self._model


reranker = DslReranker()
