"""
Nexus QA — AI Gateway Embedding Route'ları
POST /ai/embed   — Metin listesi için vektör üretir (Ollama /api/embeddings proxy)
GET  /ai/embed/model — Aktif embedding modelinin adı/boyutu

Ollama'nın /api/embeddings endpoint'i OpenAI-compat DEĞİL, native API.
Bu yüzden ayrı bir route tutuyoruz. Varsayılan model `bge-m3` — multilingual,
TR/EN alias corpus'u için yüksek kalite veriyor. Üretilen vektör ortalama
~1024 boyut (bge-m3 için).

Güvenlik: İç servis key ile çağrılır (backend → gateway), X-Internal-Key
header'ı doğrulanır.
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])


# ── Şemalar ────────────────────────────────────────────────────────────────

class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=256)
    model: Optional[str] = Field(
        default=None,
        description="Override embedding modeli. None ise OLLAMA_EMBED_MODEL.",
    )
    # Korelasyon ID'si — backend'ten gelen isteği log'larda takip etmek için
    correlation_id: Optional[str] = None


class EmbedResponse(BaseModel):
    vectors: List[List[float]]
    model: str
    dim: int
    provider: str = "ollama"
    latency_ms: int


class EmbedModelInfo(BaseModel):
    model: str
    provider: str
    base_url: str


# ── Yardımcılar ────────────────────────────────────────────────────────────

def _root_base() -> str:
    """Ollama root URL (`/v1` olmadan) — /api/embeddings için."""
    base = settings.OLLAMA_BASE_URL.rstrip("/")
    if base.endswith("/v1"):
        return base[:-3]
    return base


async def _ollama_embed_one(
    client: httpx.AsyncClient, text: str, model: str
) -> list[float]:
    """Ollama native /api/embeddings — tek metin için tek vektör."""
    resp = await client.post(
        f"{_root_base()}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    vec = data.get("embedding")
    if not isinstance(vec, list) or not vec:
        raise RuntimeError(f"Ollama boş vektör döndü: {data}")
    return [float(x) for x in vec]


# ── Endpoint'ler ───────────────────────────────────────────────────────────

@router.post(
    "/embed",
    response_model=EmbedResponse,
    summary="Metin listesi için embedding vektörleri üret",
)
async def embed(
    body: EmbedRequest,
    x_internal_key: str = Header(default="", alias="X-Internal-Key"),
) -> EmbedResponse:
    if x_internal_key and x_internal_key != settings.INTERNAL_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz internal key")

    model = body.model or settings.OLLAMA_EMBED_MODEL
    start = time.monotonic()

    try:
        # Ollama batch desteklemiyor — paralel N istek (aynı model, sıcak cache)
        async with httpx.AsyncClient() as client:
            import asyncio

            tasks = [_ollama_embed_one(client, t, model) for t in body.texts]
            vectors = await asyncio.gather(*tasks)
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Ollama embed HTTP hatası %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        raise HTTPException(
            status_code=503,
            detail=(
                f"Ollama embed başarısız (HTTP {exc.response.status_code}). "
                f"Modelin pull edildiğinden emin olun: `ollama pull {model}`"
            ),
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Ollama embed bağlantı hatası: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Ollama'ya erişilemiyor ({_root_base()}): {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Embed beklenmeyen hata")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    latency_ms = int((time.monotonic() - start) * 1000)
    dim = len(vectors[0]) if vectors else 0
    logger.info(
        "Embed OK — model=%s count=%d dim=%d latency=%dms cid=%s",
        model,
        len(vectors),
        dim,
        latency_ms,
        body.correlation_id or "-",
    )
    return EmbedResponse(
        vectors=vectors,
        model=model,
        dim=dim,
        provider="ollama",
        latency_ms=latency_ms,
    )


@router.get(
    "/embed/model",
    response_model=EmbedModelInfo,
    summary="Aktif embedding modelinin bilgisi",
)
async def embed_model_info() -> EmbedModelInfo:
    return EmbedModelInfo(
        model=settings.OLLAMA_EMBED_MODEL,
        provider="ollama",
        base_url=_root_base(),
    )
