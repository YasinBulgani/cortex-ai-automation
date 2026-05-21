"""Accessibility AI Analyzer HTTP endpoint'leri — UX-F3-306.

Frontend test execution sonrası "AI ile açıklat" akışının backend'i.
PR #52'deki analyzer core'unu HTTP üzerinden açar.

Yol:
    POST /api/v1/accessibility/analyze     → TR remediation üret
    GET  /api/v1/accessibility/status      → feature flag + telemetri
"""

from __future__ import annotations

from fastapi import APIRouter

from app.domains.accessibility.analyzer import accessibility_analyzer
from app.domains.accessibility.schemas import (
    AnalyzeA11yRequest,
    AnalyzeA11yResponse,
)

router = APIRouter(prefix="/accessibility", tags=["accessibility"])


@router.post(
    "/analyze",
    response_model=AnalyzeA11yResponse,
    summary="WCAG violation'ları Türkçe remediation'a çevir",
    response_description="ok=true + remediations veya ok=false + error",
)
def analyze(request: AnalyzeA11yRequest) -> AnalyzeA11yResponse:
    """axe-core / Pa11y / Lighthouse çıktısından violation listesi alır,
    AI Gateway üzerinden (vLLM/Ollama/Groq/Gemini fallback) Türkçe
    açıklama + somut fix önerisi döndürür.

    Davranış:
        * ``AI_ACCESSIBILITY_ENABLED=false`` → ok=true, remediations=[]
          (sessiz no-op — frontend bu durumu "kapalı" göstermeli)
        * Gateway erişilemez → ok=false, error, remediations=[]
        * LLM parse hatası → ok=false, error="parse..."
        * Başarılı → ok=true, remediations dolu, latency_ms
    """
    return accessibility_analyzer.analyze(request)


@router.get(
    "/status",
    summary="A11y analyzer durumu (feature flag + telemetri)",
)
def status():
    """Frontend "AI ile açıklat" butonunu gösterip göstermemek için.

    enabled=false ise buton gizlenmeli veya disabled gösterilmeli.
    """
    return accessibility_analyzer.info()
