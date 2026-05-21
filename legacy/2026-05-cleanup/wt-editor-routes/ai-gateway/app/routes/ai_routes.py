"""
Nexus QA — AI Gateway Route'ları
POST /ai/complete  — Ana tamamlama endpoint'i
GET  /ai/health    — Sağlayıcı durum kontrolü
GET  /ai/providers — Desteklenen sağlayıcılar
"""
from __future__ import annotations

import hmac
import logging
import uuid

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.models import AIRequest, AIResponse, HealthResponse, ProviderName, TaskType
from app.core.router import ai_router
from app.core.prompts import get_system_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])


def _require_internal_key(x_internal_key: str) -> None:
    if not settings.INTERNAL_KEY:
        logger.error("INTERNAL_KEY ayari eksik, /ai/complete servisi kullanilamaz.")
        raise HTTPException(status_code=503, detail="Internal servis anahtari ayarlanamadi")
    if not x_internal_key:
        raise HTTPException(status_code=401, detail="X-Internal-Key header'i zorunludur")
    if not hmac.compare_digest(x_internal_key, settings.INTERNAL_KEY):
        raise HTTPException(status_code=403, detail="Gecersiz internal key")


def _inject_system_prompt(request: AIRequest) -> AIRequest:
    """
    Task type'a göre uygun system prompt'u inject et.
    Zaten system message varsa değiştirme.
    """
    has_system = any(m.role == "system" for m in request.messages)
    if not has_system and request.task_type != TaskType.CHAT:
        from app.core.models import Message
        system_msg = Message(role="system", content=get_system_prompt(request.task_type))
        request = request.model_copy(
            update={"messages": [system_msg] + list(request.messages)}
        )
    return request


def _inject_model_override(request: AIRequest) -> AIRequest:
    """
    AI_PROVIDER=ollama ve model_override verilmemişse task_type'a göre model seç.
    Böylece analiz → qwen2.5:14b, kod → qwen2.5-coder:7b, chat → llama3.1:8b olur.
    """
    if settings.AI_PROVIDER.lower() == "ollama" and request.model_override is None:
        model = settings.model_for_task(request.task_type.value)
        request = request.model_copy(update={"model_override": model})
    return request


@router.post(
    "/complete",
    response_model=AIResponse,
    summary="AI tamamlama isteği",
    description="Fallback zinciriyle AI yanıtı al: Groq → Gemini → Ollama → g4f",
)
async def complete(
    request: AIRequest,
    x_internal_key: str = Header(default="", alias="X-Internal-Key"),
):
    # İç servis key doğrulama (frontend/backend bu key ile çağırır)
    _require_internal_key(x_internal_key)

    # correlation_id yoksa üret
    if not request.correlation_id:
        request = request.model_copy(update={"correlation_id": str(uuid.uuid4())[:8]})

    # System prompt + model inject
    request = _inject_system_prompt(request)
    request = _inject_model_override(request)

    try:
        response = await ai_router.route(request)
        return response
    except TimeoutError as exc:
        logger.warning(f"AI Gateway timeout: {exc}")
        raise HTTPException(
            status_code=504,
            detail="AI sağlayıcısı yanıt süresini aşırı aştı",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        logger.error(f"AI Gateway hata: {exc}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Tüm AI sağlayıcıları başarısız oldu",
                "detail": str(exc),
            },
        )
    except Exception as exc:
        logger.exception(f"Beklenmeyen hata: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Sağlayıcı durum kontrolü",
)
async def health():
    provider_status = await ai_router.health_check()
    overall = any(provider_status.values())
    payload = HealthResponse(
        status="healthy" if overall else "degraded",
        providers=provider_status,
        version=settings.APP_VERSION,
    )
    if not overall:
        return JSONResponse(
            status_code=503,
            content=payload.model_dump(),
        )
    return payload


@router.get(
    "/providers",
    summary="Desteklenen sağlayıcılar listesi",
)
async def providers():
    provider_status = await ai_router.health_check()
    return {
        "providers": [
            {
                "name": "vllm",
                "model": settings.VLLM_MODEL,
                "free_tier": True,  # self-hosted → bulut faturası yok
                "limits": "Self-host donanım limiti (örn. 2x H100 80GB)",
                "status": "available" if settings.VLLM_ENABLED else "disabled",
                "open_source": True,
            },
            {
                "name": "groq",
                "model": settings.GROQ_MODEL,
                "free_tier": True,
                "limits": f"{settings.GROQ_RPM_LIMIT} RPM, {settings.GROQ_TPM_LIMIT} TPM",
                "status": "available" if settings.GROQ_API_KEY else "no_api_key",
                "open_source": False,
            },
            {
                "name": "gemini",
                "model": settings.GEMINI_MODEL,
                "free_tier": True,
                "limits": f"{settings.GEMINI_RPM_LIMIT} RPM, {settings.GEMINI_TPD_LIMIT // 1000}K TPD",
                "status": "available" if settings.GEMINI_API_KEY else "no_api_key",
                "open_source": False,
            },
            {
                "name": "ollama",
                "model": settings.OLLAMA_MODEL,
                "free_tier": True,
                "limits": "Sınırsız (local)",
                "status": "local",
                "open_source": True,
            },
            {
                "name": "g4f",
                "model": settings.G4F_MODEL,
                "free_tier": True,
                "limits": "Güvenilmez (son çare)",
                "status": "fallback" if settings.G4F_ENABLED else "disabled",
                "open_source": False,
            },
        ],
        "fallback_order": settings.PROVIDER_ORDER,
        "provider_status": provider_status,
    }
