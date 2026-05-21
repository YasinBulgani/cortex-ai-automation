"""DSL Sözlüğü HTTP API'si.

`packages/dsl/catalog/*.yaml` altındaki test cümleciklerini REST üzerinden
sunar. Cache `service.py` katmanının arkasında — router salt HTTP sözleşmesi.

Tüm endpoint'ler oturum açmış kullanıcıya açık; yazma işlemi şu an yok
(katalog diske elle eklenir). `/reload` admin değil ama rate-limit
tarafında korunur (ileride require_permission eklenebilir).
"""
from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.domains.dsl import service as dsl_service
from app.domains.dsl import feedback_service
from app.domains.dsl.schemas import (
    DslAction,
    DslActionListResponse,
    DslReloadResponse,
    DslSearchHit,
    DslSearchResponse,
    DslStats,
)
from app.infra.database import get_db
from app.infra.models import User

router = APIRouter(prefix="/dsl", tags=["dsl"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


# ── Schemas (router-local) ──────────────────────────────────────────────────

class SuggestRequest(BaseModel):
    description: str = Field(..., min_length=2, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)
    # UI'dan gelen aramanın modu: "auto" → indeks varsa hybrid, yoksa lexical.
    # "lexical" → eski davranış, "hybrid" → zorla embed+lex, "semantic" → sadece
    # embedding indeksi üzerinden.
    mode: str = Field(default="auto", pattern="^(auto|lexical|hybrid|semantic)$")


class SemanticSearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=500)
    lang: Optional[str] = Field(default=None, pattern="^(tr|en)$")
    limit: int = Field(default=20, ge=1, le=100)
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)


class FeedbackRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    action_id: str = Field(..., min_length=1, max_length=128)
    vote: str = Field(..., pattern="^(up|down|ignored)$")
    search_mode: Optional[str] = Field(
        default=None, pattern="^(lexical|semantic|hybrid|llm_rerank)$"
    )
    rank: Optional[int] = Field(default=None, ge=0, le=200)
    raw_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class FeedbackResponse(BaseModel):
    id: str
    recorded_at: str
    bonus_applied: float = 0.0


class IndexInfo(BaseModel):
    ready: bool
    rows: int
    dim: int
    model: str
    built_at: Optional[float] = None
    corpus_hash: str


class IndexRebuildResponse(BaseModel):
    status: str
    rows: int = 0
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class CategoryNodeOut(BaseModel):
    id: str
    label: str
    count: int
    children: List["CategoryNodeOut"] = Field(default_factory=list)


CategoryNodeOut.model_rebuild()


# ── Endpoint'ler ────────────────────────────────────────────────────────────

@router.get("/actions", response_model=DslActionListResponse)
def list_actions(
    _: CurrentUser,
    category: Optional[str] = Query(None, description="Üst ya da tam kategori"),
    lang: Optional[str] = Query(None, pattern="^(tr|en)$"),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> DslActionListResponse:
    """Cümlecik listesi — sayfalandırılmış, filtrelenebilir."""
    return dsl_service.list_actions(
        category=category,
        lang=lang,
        tag=tag,
        page=page,
        page_size=page_size,
    )


@router.get("/actions/{action_id}", response_model=DslAction)
def get_action(
    action_id: str,
    _: CurrentUser,
) -> DslAction:
    """Tek bir cümleciğin detayı (TR/EN alias + tüm dil implementasyonları)."""
    action = dsl_service.get_action(action_id)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DSL action bulunamadı: {action_id}",
        )
    return action


@router.get("/search", response_model=DslSearchResponse)
def search_actions(
    _: CurrentUser,
    q: str = Query(..., min_length=1, max_length=200),
    lang: Optional[str] = Query(None, pattern="^(tr|en)$"),
    limit: int = Query(50, ge=1, le=200),
) -> DslSearchResponse:
    """Alias + description'da serbest metin arama."""
    return dsl_service.search_actions(q, lang=lang, limit=limit)


@router.get("/stats", response_model=DslStats)
def get_stats(_: CurrentUser) -> DslStats:
    """Toplam cümlecik sayısı, kategori/dil/implementation dağılımı."""
    return dsl_service.get_stats()


@router.get("/categories", response_model=list[CategoryNodeOut])
def get_categories(_: CurrentUser) -> list[CategoryNodeOut]:
    """UI sol paneli için 2 seviyeli kategori ağacı."""
    tree = dsl_service.category_tree()
    return [
        CategoryNodeOut(
            id=n.id,
            label=n.label,
            count=n.count,
            children=[
                CategoryNodeOut(id=c.id, label=c.label, count=c.count, children=[])
                for c in n.children
            ],
        )
        for n in tree
    ]


@router.post("/suggest", response_model=DslSearchResponse)
def suggest(
    body: SuggestRequest,
    db: DbSession,
    _: CurrentUser,
) -> DslSearchResponse:
    """Serbest metin açıklama → en uygun cümlecik önerileri.

    Modlar:
    - `auto`     → indeks varsa hybrid, yoksa lexical'e düşer (varsayılan)
    - `lexical`  → eski token bazlı davranış
    - `hybrid`   → lexical + semantic ağırlıklı toplam
    - `semantic` → sadece embedding cosine

    Döngü: sonuçların üstüne son 30 günlük kullanıcı feedback'i skor bonusu
    olarak uygulanır (±0.15), sıralama güncellenir.
    """
    if body.mode == "lexical":
        response = dsl_service.suggest_actions(
            body.description, limit=body.limit, force_lexical=True
        )
    elif body.mode == "semantic":
        response = dsl_service.semantic_search(body.description, limit=body.limit)
    elif body.mode == "hybrid":
        response = dsl_service.hybrid_search(body.description, limit=body.limit)
    else:
        response = dsl_service.suggest_actions(body.description, limit=body.limit)

    return _apply_feedback_rerank(db, response)


@router.post("/search/semantic", response_model=DslSearchResponse)
def search_semantic(
    body: SemanticSearchRequest,
    db: DbSession,
    _: CurrentUser,
) -> DslSearchResponse:
    """Embedding tabanlı anlamsal arama.

    Index hazır değilse lexical aramaya düşer; bu durumda `mode` alanı
    `lexical_fallback` olur.
    """
    response = dsl_service.semantic_search(
        body.q, lang=body.lang, limit=body.limit, min_score=body.min_score
    )
    return _apply_feedback_rerank(db, response)


@router.post("/feedback", response_model=FeedbackResponse)
def record_feedback(
    body: FeedbackRequest,
    db: DbSession,
    current: CurrentUser,
) -> FeedbackResponse:
    """Kullanıcının arama sonucuna verdiği 👍 / 👎 kaydı."""
    entry = feedback_service.record_feedback(
        db,
        user_id=getattr(current, "id", None),
        query=body.query,
        action_id=body.action_id,
        vote=body.vote,
        search_mode=body.search_mode,
        rank=body.rank,
        raw_score=body.raw_score,
    )
    # Anında geri dönüş: bu action için uygulanacak bonusu hesapla
    bonus = feedback_service.feedback_bonus_for(
        db, query=body.query, action_ids=[body.action_id]
    ).get(body.action_id, 0.0)
    return FeedbackResponse(
        id=entry.id,
        recorded_at=entry.created_at.isoformat(),
        bonus_applied=bonus,
    )


@router.get("/index/info", response_model=IndexInfo)
def index_info(_: CurrentUser) -> IndexInfo:
    """Aktif embedding indeksinin durumu."""
    info = dsl_service.embedding_index_info()
    return IndexInfo(
        ready=bool(info.get("ready")),
        rows=int(info.get("rows", 0)),
        dim=int(info.get("dim", 0)),
        model=str(info.get("model", "")),
        built_at=info.get("built_at"),
        corpus_hash=str(info.get("corpus_hash", "")),
    )


@router.post("/index/rebuild", response_model=IndexRebuildResponse)
def index_rebuild(
    _: CurrentUser,
    force: bool = Query(default=False, description="Hash aynı olsa bile yeniden üret"),
) -> IndexRebuildResponse:
    """Embedding indeksini gateway üzerinden yeniden üret.

    Katalog YAML'leri değiştikten sonra `/reload` çağırmak index'i arka planda
    zaten tetikler; bu endpoint senkron çağrı isteyen CI/admin için.
    """
    result = dsl_service.rebuild_embedding_index(force=force)
    return IndexRebuildResponse(
        status=str(result.get("status", "unknown")),
        rows=int(result.get("rows", 0)),
        latency_ms=result.get("latency_ms"),
        error=result.get("error"),
    )


@router.post("/reload", response_model=DslReloadResponse)
def reload_catalog(_: CurrentUser) -> DslReloadResponse:
    """Disk'ten katalog'u yeniden yükle.

    YAML dosyaları değiştikten sonra pod'u restart etmeden cache'i
    tazelemek için kullanılır. Katalog değişirse embedding indeksi de
    arka planda yeniden inşa edilir.
    """
    return dsl_service.reload_catalog()


# ── Yardımcılar ────────────────────────────────────────────────────────────

def _apply_feedback_rerank(
    db: Session, response: DslSearchResponse
) -> DslSearchResponse:
    """Arama sonucuna feedback bonusu uygulayıp yeniden sıralar.

    Feedback tablosu yoksa (migration çalıştırılmamışsa) sessizce atlar —
    aramaya devam edilmesi geri bildirim kaydedilmesinden daha önemli.
    """
    if not response.items:
        return response
    try:
        ids = [it.action.id for it in response.items]
        bonuses = feedback_service.feedback_bonus_for(
            db, query=response.query, action_ids=ids
        )
    except Exception:  # noqa: BLE001
        return response
    if not bonuses:
        return response

    reranked: list[DslSearchHit] = []
    for it in response.items:
        base = it.score if it.score is not None else 0.5
        bonus = bonuses.get(it.action.id, 0.0)
        new_score = max(0.0, min(1.0, base + bonus))
        reranked.append(
            it.model_copy(update={"score": round(new_score, 4)})
        )
    reranked.sort(key=lambda h: h.score or 0.0, reverse=True)
    return response.model_copy(update={"items": reranked})
