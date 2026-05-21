"""DSL katalog iş mantığı.

`loader.CatalogCache` singleton'unu sarmalayıp HTTP router'ına domain
seviyesinde bir servis yüzü sunar. Router doğrudan cache'e değil, buradaki
fonksiyonlara çağırır — böylece:

  * İleride AI destekli `suggest` için extra mantık eklenebilir
  * Test edilebilir (cache'i mock edebiliriz)
  * Pagination / filtreleme kuralları tek yerde
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from app.domains.dsl.embedding_index import SemanticHit, alias_index
from app.domains.dsl.loader import catalog_cache
from app.domains.dsl.schemas import (
    DslAction,
    DslActionListResponse,
    DslReloadResponse,
    DslSearchHit,
    DslSearchResponse,
    DslStats,
)

logger = logging.getLogger(__name__)


# ── Listeleme & Filtreleme ──────────────────────────────────────────────────

_STEP_TYPE_PREFIXES: dict[str, list[str]] = {
    "given": ["(Ön koşul)", "(On kosul)", "Given "],
    "when":  ["Eylem:", "When ", "Action:"],
    "then":  ["Doğrulama:", "Dogrulama:", "Then ", "Assert:"],
}


def list_actions(
    *,
    category: Optional[str] = None,
    lang: Optional[str] = None,
    tag: Optional[str] = None,
    step_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> DslActionListResponse:
    """Kataloğu filtreleyip sayfalandırılmış sonuç döner."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 500:
        page_size = 50

    filtered = catalog_cache.filter(category=category, lang=lang, tag=tag)

    if step_type and step_type in _STEP_TYPE_PREFIXES:
        prefixes = _STEP_TYPE_PREFIXES[step_type]
        filtered = [
            a for a in filtered
            if a.description and any(a.description.startswith(p) for p in prefixes)
        ]

    filtered.sort(key=lambda a: (a.category or "zzz", a.id or ""))

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return DslActionListResponse(
        items=filtered[start:end],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_action(action_id: str) -> Optional[DslAction]:
    return catalog_cache.get(action_id)


# ── Arama ───────────────────────────────────────────────────────────────────

def search_actions(
    query: str,
    *,
    lang: Optional[str] = None,
    limit: int = 50,
) -> DslSearchResponse:
    hits_raw = catalog_cache.search(query=query, lang=lang)
    hits = [
        DslSearchHit(
            action=a,
            matched_language=ln,
            matched_alias=alias,
            source="lexical",
        )
        for a, ln, alias in hits_raw[:limit]
    ]
    return DslSearchResponse(
        query=query, total=len(hits_raw), items=hits, mode="lexical"
    )


# ── Semantik Arama (AI destekli) ────────────────────────────────────────────

def semantic_search(
    query: str,
    *,
    lang: Optional[str] = None,
    limit: int = 20,
    min_score: float = 0.3,
) -> DslSearchResponse:
    """Embedding tabanlı anlamsal arama.

    Index hazır değilse otomatik olarak lexical aramaya düşer — UI'ın `mode`
    alanına bakarak kullanıcıya uygun mesajı gösterebilir.
    """
    if not alias_index.is_ready():
        try:
            alias_index.ensure_loaded()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Semantic index lazy load hatası: %s", exc)

    if not alias_index.is_ready():
        # Index yok — lexical'e düş
        fallback = search_actions(query, lang=lang, limit=limit)
        fallback.mode = "lexical_fallback"
        fallback.index_info = alias_index.info()
        return fallback

    hits: list[SemanticHit] = alias_index.search(
        query, lang=lang, k=limit, min_score=min_score
    )
    items = [
        DslSearchHit(
            action=h.action,
            matched_language=h.matched_language,
            matched_alias=h.matched_alias,
            score=round(h.score, 4),
            source="semantic",
        )
        for h in hits
    ]
    return DslSearchResponse(
        query=query,
        total=len(items),
        items=items,
        mode="semantic",
        index_info=alias_index.info(),
    )


# ── Hybrid Arama ────────────────────────────────────────────────────────────

def hybrid_search(
    query: str,
    *,
    lang: Optional[str] = None,
    limit: int = 20,
    lexical_weight: float = 0.35,
    semantic_weight: float = 0.65,
) -> DslSearchResponse:
    """Lexical + semantic skorlarını birleştirip tek sıralama üretir.

    Lexical hit'ler için skor = 1.0, semantic hit'ler için embedding score.
    Aynı action her ikisinde de varsa ağırlıklı toplam alınır.
    """
    lex = catalog_cache.search(query=query, lang=lang)
    sem_hits: list[SemanticHit] = []
    if alias_index.is_ready():
        sem_hits = alias_index.search(query, lang=lang, k=limit * 2, min_score=0.25)

    # action_id → (best_lang, best_alias, combined_score, sources)
    scored: dict[str, dict] = {}
    for action, ln, alias in lex:
        scored[action.id] = {
            "action": action,
            "lang": ln,
            "alias": alias,
            "lex": 1.0,
            "sem": 0.0,
        }
    for h in sem_hits:
        cur = scored.get(h.action.id)
        if cur is None:
            scored[h.action.id] = {
                "action": h.action,
                "lang": h.matched_language,
                "alias": h.matched_alias,
                "lex": 0.0,
                "sem": h.score,
            }
        else:
            cur["sem"] = max(cur["sem"], h.score)
            # Lexical alias zaten set edildi, override etme

    if not scored:
        return DslSearchResponse(
            query=query,
            total=0,
            items=[],
            mode="hybrid_empty",
            index_info=alias_index.info(),
        )

    ranked = sorted(
        scored.values(),
        key=lambda r: r["lex"] * lexical_weight + r["sem"] * semantic_weight,
        reverse=True,
    )[:limit]

    items = [
        DslSearchHit(
            action=r["action"],
            matched_language=r["lang"],
            matched_alias=r["alias"],
            score=round(r["lex"] * lexical_weight + r["sem"] * semantic_weight, 4),
            source="hybrid",
        )
        for r in ranked
    ]
    return DslSearchResponse(
        query=query,
        total=len(items),
        items=items,
        mode="hybrid",
        index_info=alias_index.info(),
    )


# ── İstatistikler ───────────────────────────────────────────────────────────

def get_stats() -> DslStats:
    return catalog_cache.stats()


# ── Yönetim ────────────────────────────────────────────────────────────────

def reload_catalog(*, rebuild_index: bool = True) -> DslReloadResponse:
    before = len(catalog_cache.all())
    total_after = catalog_cache.load()
    # Katalog değiştiğinde embedding indeksini de tazele — arka plan thread'ine
    # at, çünkü gateway yavaş olabilir ve router bloke olmasın.
    if rebuild_index:
        try:
            import threading

            threading.Thread(
                target=_safe_rebuild_index,
                name="dsl-embed-rebuild",
                daemon=True,
            ).start()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embed index rebuild thread başlatılamadı: %s", exc)
    return DslReloadResponse(
        status="ok",
        total_before=before,
        total_after=total_after,
        loaded_at=catalog_cache.loaded_at or "",
    )


def _safe_rebuild_index() -> None:
    try:
        result = alias_index.rebuild()
        logger.info("DSL embed index rebuild: %s", result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DSL embed index rebuild hata: %s", exc)


def rebuild_embedding_index(*, force: bool = False) -> dict:
    """Embedding indeksini senkron olarak yeniden oluştur (HTTP tarafı için)."""
    return alias_index.rebuild(force=force)


def embedding_index_info() -> dict:
    alias_index.ensure_loaded()
    return alias_index.info()


# ── Kategori özeti (UI için) ────────────────────────────────────────────────

@dataclass
class CategoryNode:
    """UI'ın sol panelinde gösterilecek kategori ağacı düğümü."""

    id: str
    label: str
    count: int
    children: List["CategoryNode"]


def category_tree() -> List[CategoryNode]:
    """Kategorileri 2-seviyeli ağaç olarak döner.

    `ui.click` → üst: `ui`, alt: `ui.click`. `bgts.project.create` gibi 3
    seviyeli olanlar en fazla 2. seviyeye indirgenir (daha derin kırılma
    listelemede gereksiz gürültü yaratır).
    """
    stats = catalog_cache.stats()
    full = stats.by_full_category or {}

    roots: dict[str, CategoryNode] = {}
    for full_id, count in full.items():
        if not full_id:
            continue
        top = full_id.split(".", 1)[0]
        root = roots.get(top)
        if root is None:
            root = CategoryNode(id=top, label=top, count=0, children=[])
            roots[top] = root
        root.count += count
        if full_id != top:
            root.children.append(
                CategoryNode(id=full_id, label=full_id, count=count, children=[])
            )

    ordered = sorted(roots.values(), key=lambda n: (-n.count, n.id))
    for node in ordered:
        node.children.sort(key=lambda c: (-c.count, c.id))
    return ordered


# ── AI-destekli öneri ───────────────────────────────────────────────────────

def suggest_actions(
    description: str,
    *,
    limit: int = 10,
    force_lexical: bool = False,
) -> DslSearchResponse:
    """Serbest metin açıklama → en uygun cümlecik önerileri.

    `force_lexical=True` olduğunda eski davranış (kelime bazlı) kullanılır.
    Varsayılan: embedding indeksi hazırsa hybrid, değilse lexical'e düşer.
    """
    text = (description or "").strip()
    if not text:
        return DslSearchResponse(query=description, total=0, items=[], mode="empty")

    if not force_lexical and alias_index.is_ready():
        result = hybrid_search(text, limit=limit)
        if result.items:
            return result

    return _lexical_suggest_fallback(text, limit=limit)


def _lexical_suggest_fallback(text: str, *, limit: int) -> DslSearchResponse:
    """Embedding yoksa / hybrid boş döndüyse: token bazlı skorlama."""
    stop = {"ve", "ile", "bir", "bu", "the", "a", "an", "is", "to", "of"}
    tokens = [t for t in _tokenize(text.lower()) if len(t) > 2 and t not in stop]
    if not tokens:
        tokens = [text.lower()]

    scored: dict[str, tuple[DslAction, int, str, str]] = {}
    for token in tokens:
        for a, ln, alias in catalog_cache.search(token):
            current = scored.get(a.id)
            score = 1 + (2 if token in (alias or "").lower() else 0)
            if current is None or score > current[1]:
                scored[a.id] = (a, score, ln, alias)

    ranked = sorted(scored.values(), key=lambda t: (-t[1], t[0].id))[:limit]
    items = [
        DslSearchHit(
            action=a,
            matched_language=ln,
            matched_alias=alias,
            score=round(float(score) / 3.0, 4),  # Normalize
            source="lexical",
        )
        for a, score, ln, alias in ranked
    ]
    return DslSearchResponse(
        query=text, total=len(ranked), items=items, mode="lexical"
    )


def _tokenize(text: str) -> List[str]:
    buf: list[str] = []
    current: list[str] = []
    for ch in text:
        if ch.isalnum() or ch in {"-", "_"}:
            current.append(ch)
        else:
            if current:
                buf.append("".join(current))
                current = []
    if current:
        buf.append("".join(current))
    return buf
