"""
Self-healing route'ları — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/ai_healing_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/ai_healing.py — APIRouter, port 8000 (consolidated)

Endpoint'ler:
  POST /api/ai/self-heal       — Kırık locator'ı heal et
  POST /api/ai/find-element    — Accessibility tree'den element bul
  GET  /api/ai/healing-log     — Healing geçmişini döndür
"""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["engine", "ai-healing"])

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_HEALING_LOG = _REPO_ROOT / "reports" / "healing-log.json"


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SelfHealRequest(BaseModel):
    failed_locator: str = Field(..., min_length=1, description="Kırık locator string'i")
    accessibility_tree: str = Field("", description="Sayfanın accessibility tree metni")
    error_message: str = Field("", description="Locator hatasının mesajı")
    page_url: str = Field("", description="Test edilen sayfanın URL'i")


class FindElementRequest(BaseModel):
    element_intent: str = Field(..., min_length=1, description="Hedef elementin açıklaması")
    accessibility_tree: str = Field("", description="Sayfanın accessibility tree metni")


class FindElementResponse(BaseModel):
    locator: str
    model: str
    cached: bool


class HealingLogResponse(BaseModel):
    total: int
    entries: list[dict]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_gateway():
    """LLM gateway örneğini döndürür."""
    try:
        from services import get_llm_gateway  # type: ignore[import]
        return get_llm_gateway()
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM gateway servisine erişilemiyor: {exc}",
        )


def _check_feature(name: str) -> None:
    """Feature flag kontrolü; devre dışıysa 503 fırlatır."""
    try:
        from services import is_feature_enabled  # type: ignore[import]
        if not is_feature_enabled(name):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"'{name}' özelliği ai_config.yaml'da devre dışı",
            )
    except ImportError:
        logger.warning(
            "Opsiyonel bağımlılık 'services.is_feature_enabled' yüklenemedi, "
            "feature flag kontrolü atlanıyor (ai_healing)."
        )


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/self-heal")
def self_heal(body: SelfHealRequest) -> dict:
    """Kırık locator için yeni locator önerisi üretir."""
    _check_feature("self_healing")
    gw = _get_gateway()
    if not gw.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM API anahtarı yapılandırılmamış",
        )

    try:
        from services.self_healer import SelfHealer  # type: ignore[import]
        healer = SelfHealer(gateway=gw)
        result = healer.heal(
            failed_locator=body.failed_locator,
            accessibility_tree=body.accessibility_tree,
            error_message=body.error_message,
            page_url=body.page_url,
        )
        return result.to_dict()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Self-heal başarısız: {exc}",
        )


@router.post("/find-element", response_model=FindElementResponse)
def find_element(body: FindElementRequest) -> FindElementResponse:
    """Accessibility tree'den hedef elementi bulmak için locator üretir."""
    gw = _get_gateway()
    if not gw.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM API anahtarı yapılandırılmamış",
        )

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Verilen accessibility tree'den hedef elementi bul ve Playwright locator string'i döndür. "
                    "Sadece locator string döndür, başka bir şey yazma."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Hedef: {body.element_intent}\n\n"
                    f"Accessibility Tree:\n{body.accessibility_tree[:6000]}"
                ),
            },
        ]
        resp = gw.complete(messages, model="gpt-4o-mini", temperature=0.1, max_tokens=150)
        locator = resp.content.strip().strip("`").strip('"').strip("'")
        return FindElementResponse(locator=locator, model=resp.model, cached=resp.cached)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Element arama başarısız: {exc}",
        )


@router.get("/healing-log", response_model=HealingLogResponse)
def healing_log() -> HealingLogResponse:
    """Healing geçmişini döndürür. Son 50 kayıt döner."""
    try:
        logs: list = []
        if _HEALING_LOG.exists():
            try:
                raw = json.loads(_HEALING_LOG.read_text(errors="replace"))
                logs = raw if isinstance(raw, list) else []
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                logger.debug("Healing log dosyası parse edilemedi: %s", exc)
                logs = []
        return HealingLogResponse(total=len(logs), entries=logs[-50:])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Healing log okunamadı: {exc}",
        )
