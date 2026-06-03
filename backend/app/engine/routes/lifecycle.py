"""
Lifecycle routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/lifecycle_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/lifecycle.py — APIRouter, port 8000 (consolidated)

Endpointler:
  POST /api/lifecycle/process-analyst — Analist metnini AI ile analiz et
  POST /api/lifecycle/save            — Akışı kaydet (simüle)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lifecycle", tags=["engine", "lifecycle"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AnalystRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Analiz edilecek analist metni veya dökümanı")


class AnalystResponse(BaseModel):
    summary: str
    steps: list[str]


class SaveFlowRequest(BaseModel):
    flow_id: Optional[str] = None
    name: Optional[str] = None
    data: Optional[dict] = None


class SaveFlowResponse(BaseModel):
    status: str
    message: str


# ─── In-memory AI client placeholder ─────────────────────────────────────────

class _SimpleAIClient:
    """
    Geçici in-memory AI client stub.
    Gerçek engine AIClient'i (core.ai_client) entegre edilince kaldırılacak.
    """

    def ask(self, prompt: str) -> str:
        return json.dumps({
            "summary": "AI istemcisi henüz bağlanmadı",
            "steps": ["Gerçek AI client entegre edilince bu adımlar doldurulacak."],
        })


_ai_client = _SimpleAIClient()


def _try_import_ai_client():
    """
    Engine'in gerçek AIClient'ini dinamik olarak import etmeye çalışır.
    Başarısız olursa stub'ı döndürür.
    """
    try:
        from core.ai_client import AIClient  # type: ignore[import]
        return AIClient()
    except Exception:
        return _ai_client


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/process-analyst", response_model=AnalystResponse)
def process_analyst(body: AnalystRequest) -> AnalystResponse:
    """
    Analist metnini/dökümanını AI ile analiz eder.
    Özet (max 10 kelime) ve manuel test adımları döndürür.
    """
    ai = _try_import_ai_client()

    prompt = f"""
    Aşağıdaki analist maddesini/dökümanını analiz et:
    "{body.text}"

    Lütfen şunları çıkar:
    1. Kısa bir özet (max 10 kelime).
    2. Manuel test için gerekli adımlar (liste halinde).

    Yanıtı şu JSON formatında ver:
    {{
      "summary": "Özet buraya",
      "steps": ["Adım 1", "Adım 2", ...]
    }}
    """

    try:
        response_text: str = ai.ask(prompt)

        # JSON temizleme — markdown kod bloğu varsa sıyrıl
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)
        return AnalystResponse(
            summary=result.get("summary", ""),
            steps=result.get("steps", []),
        )
    except Exception as e:
        logger.error("process_analyst hatası: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analizi başarısız: {e}",
        )


@router.post("/save", response_model=SaveFlowResponse)
def save_flow(body: SaveFlowRequest) -> SaveFlowResponse:
    """
    Lifecycle akışını kaydeder.
    Şu an simüle edilmektedir; ileride DB'ye yazılacak.
    """
    logger.info("save_flow çağrıldı: flow_id=%s name=%s", body.flow_id, body.name)
    return SaveFlowResponse(status="ok", message="Akış kaydedildi (Simüle edildi)")
