"""DSL retrieval adapter — `alias_index.search()` sarıcısı.

Inputs şeması:
    query       : str (zorunlu)
    k           : int = 10
    lang        : "tr" | "en" | null
    min_score   : float = 0.3
    rerank      : bool | null   (null = reranker.is_enabled)

Actual çıktısı:
    ranked_ids : list[str]     # action_id'ler, skor azalan
    top_1      : str | null
    matched    : list[{action_id, score, matched_language, matched_alias}]
    latency_ms : int

``available()`` False döner → alias_index hazır değil (indeks build
edilmemiş veya gateway erişimi yok). Runner bu suite'i skip eder.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DslRetrievalAdapter:
    name = "dsl_retrieval"

    def available(self) -> bool:
        try:
            from app.domains.dsl.embedding_index import alias_index

            alias_index.ensure_loaded()
            return alias_index.is_ready()
        except Exception as exc:  # pragma: no cover - import/boot sorunu
            logger.warning("DslRetrievalAdapter unavailable: %s", exc)
            return False

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        from app.domains.dsl.embedding_index import alias_index

        query = str(inputs.get("query") or "").strip()
        if not query:
            raise ValueError("inputs.query boş olamaz")
        k = int(inputs.get("k", 10))
        lang = inputs.get("lang")
        min_score = float(inputs.get("min_score", 0.3))
        rerank = inputs.get("rerank")  # None | bool

        t0 = time.monotonic()
        hits = alias_index.search(
            query,
            lang=lang if lang in (None, "tr", "en") else None,
            k=k,
            min_score=min_score,
            rerank=rerank,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        ranked_ids = [h.action.id for h in hits]
        matched = [
            {
                "action_id": h.action.id,
                "score": float(h.score),
                "matched_language": h.matched_language,
                "matched_alias": h.matched_alias,
            }
            for h in hits
        ]
        return {
            "ranked_ids": ranked_ids,
            "top_1": ranked_ids[0] if ranked_ids else None,
            "matched": matched,
            "latency_ms": latency_ms,
        }
