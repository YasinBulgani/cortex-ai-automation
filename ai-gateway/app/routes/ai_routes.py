"""
Nexus QA — AI Gateway Route'ları
POST /ai/complete  — Ana tamamlama endpoint'i
POST /ai/stream    — Streaming (SSE) tamamlama
POST /ai/pipeline  — Çok adımlı agent pipeline (SSE)
GET  /ai/health    — Sağlayıcı durum kontrolü
GET  /ai/providers — Desteklenen sağlayıcılar
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict, deque

import asyncio

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse, StreamingResponse

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.models import AIRequest, AIResponse, HealthResponse, ErrorResponse, ProviderName, TaskType
from app.core.pipeline import run_pipeline, ALL_STEPS
from app.core.router import ai_router
from app.core.prompts import get_system_prompt
from app.core.schema_contracts import SchemaContractError
from app.core.security import require_internal_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])

_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = asyncio.Lock()
_capacity_lock = asyncio.Lock()
_active_requests = 0


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
    Aktif sağlayıcı Ollama ise task_type'a göre doğru modeli seç.
    Böylece analiz → qwen2.5:14b, kod → qwen2.5-coder:7b, chat → llama3.1:8b olur.

    AI_PROVIDER="ollama" ile explicit ya da "auto" modunda zincirim başında
    Ollama varsa her iki durumda da inject edilir.
    """
    if request.model_override is not None:
        return request
    first_provider = settings.PROVIDER_ORDER[0] if settings.PROVIDER_ORDER else None
    if settings.AI_PROVIDER.lower() == "ollama" or first_provider == "ollama":
        model = settings.model_for_task(request.task_type.value)
        request = request.model_copy(update={"model_override": model})
    return request


async def _enforce_rate_limit(request: AIRequest, route: str) -> None:
    limit = int(settings.RATE_LIMIT_PER_MINUTE or 0)
    if limit <= 0:
        return
    tenant = request.tenant_id or "unknown-tenant"
    project = request.project_id or "unknown-project"
    key = f"{tenant}:{project}:{route}"
    now = time.monotonic()
    window_start = now - 60.0
    async with _rate_lock:
        bucket = _rate_buckets[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=429,
                detail="AI gateway rate limit aşıldı",
                headers={"Retry-After": "60"},
            )
        bucket.append(now)


async def _acquire_capacity() -> None:
    global _active_requests
    max_concurrent = int(settings.MAX_CONCURRENT_REQUESTS or 0)
    if max_concurrent <= 0:
        return
    async with _capacity_lock:
        if _active_requests >= max_concurrent:
            raise HTTPException(
                status_code=503,
                detail="AI gateway concurrency kapasitesi dolu",
            )
        _active_requests += 1


async def _release_capacity() -> None:
    global _active_requests
    async with _capacity_lock:
        _active_requests = max(0, _active_requests - 1)


@router.post(
    "/complete",
    response_model=AIResponse,
    summary="AI tamamlama isteği",
    description="Fallback zinciriyle AI yanıtı al: Groq → Gemini → Ollama → g4f",
)
async def complete(
    request: AIRequest,
    x_internal_key: str = Header(default="", alias="X-Internal-Key"),
    x_tenant_id: str = Header(default="", alias="X-Tenant-Id"),
):
    # İç servis key doğrulama (frontend/backend bu key ile çağırır)
    require_internal_key(x_internal_key)

    # correlation_id yoksa üret
    if not request.correlation_id:
        request = request.model_copy(update={"correlation_id": str(uuid.uuid4())[:8]})
    if x_tenant_id and not request.tenant_id:
        request = request.model_copy(update={"tenant_id": x_tenant_id})

    # System prompt + model inject
    request = _inject_system_prompt(request)
    request = _inject_model_override(request)
    await _enforce_rate_limit(request, "complete")
    await _acquire_capacity()

    try:
        response = await ai_router.route(request)
        return response
    except TimeoutError as exc:
        logger.warning(f"AI Gateway timeout: {exc}")
        raise HTTPException(
            status_code=504,
            detail="AI sağlayıcısı yanıt süresini aşırı aştı",
        )
    except SchemaContractError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Structured output contract failed",
                "error_type": exc.kind,
                "task_type": exc.task_type,
                "detail": exc.detail,
            },
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
    finally:
        await _release_capacity()


@router.post(
    "/stream",
    summary="Streaming AI tamamlama (SSE)",
    description=(
        "Server-Sent Events formatında token token yanıt döner. "
        "Her event: `data: {\"token\": \"...\"}\\n\\n`. Bitiş: `data: [DONE]\\n\\n`."
    ),
    response_class=StreamingResponse,
)
async def stream(
    request: AIRequest,
    x_internal_key: str = Header(default="", alias="X-Internal-Key"),
    x_tenant_id: str = Header(default="", alias="X-Tenant-Id"),
):
    require_internal_key(x_internal_key)

    if not request.correlation_id:
        request = request.model_copy(update={"correlation_id": str(uuid.uuid4())[:8]})
    if x_tenant_id and not request.tenant_id:
        request = request.model_copy(update={"tenant_id": x_tenant_id})

    request = _inject_system_prompt(request)
    request = _inject_model_override(request)
    await _enforce_rate_limit(request, "stream")
    await _acquire_capacity()

    async def _sse_generator():
        try:
            async for token in ai_router.stream_route(request):
                payload = json.dumps({"token": token}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except RuntimeError as exc:
            error_payload = json.dumps({"error": str(exc)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"
        except Exception as exc:
            logger.exception(f"Streaming hatası: {exc}")
            error_payload = json.dumps({"error": "Beklenmeyen hata"}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"
        finally:
            await _release_capacity()

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Nginx proxy buffer'ı devre dışı
            "Connection": "keep-alive",
        },
    )


class PipelineRequest(BaseModel):
    document: str = Field(..., description="Analiz edilecek doküman metni (PRD, spec, user story)")
    steps: list[str] | None = Field(
        None,
        description=(
            "Çalıştırılacak adımlar. None → tümü. "
            f"Geçerli adımlar: {ALL_STEPS}"
        ),
    )
    pipeline_id: str | None = Field(None, description="Korelasyon ID (None → otomatik)")


@router.post(
    "/pipeline",
    summary="Çok adımlı AI pipeline (SSE)",
    description=(
        "Doküman → test case → Gherkin → Playwright zincirini adım adım çalıştırır. "
        "Her adım için SSE event stream döner. "
        "Event formatı: `data: {\"step\": \"...\", \"status\": \"started|completed|failed\", \"content\": \"...\"}\\n\\n`"
    ),
    response_class=StreamingResponse,
)
async def pipeline(
    request: PipelineRequest,
    x_internal_key: str = Header(default="", alias="X-Internal-Key"),
):
    require_internal_key(x_internal_key)

    if not request.document.strip():
        raise HTTPException(status_code=422, detail="Doküman boş olamaz")

    async def _pipeline_sse():
        try:
            async for event in run_pipeline(
                document=request.document,
                steps=request.steps,
                pipeline_id=request.pipeline_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception(f"Pipeline SSE hatası: {exc}")
            error_payload = json.dumps({"step": "pipeline", "status": "failed", "error": str(exc)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        _pipeline_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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

    def status_for(
        name: str,
        *,
        enabled: bool = True,
        configured: bool = True,
        disabled_label: str = "disabled",
        unconfigured_label: str = "no_api_key",
        available_label: str = "available",
    ) -> str:
        live = provider_status.get(name)
        if live is True:
            return available_label
        if live is False:
            return "unavailable"
        if not enabled:
            return disabled_label
        if not configured:
            return unconfigured_label
        return "unavailable"

    return {
        "providers": [
            {
                "name": "vllm",
                "model": settings.VLLM_MODEL,
                "free_tier": True,  # self-hosted → bulut faturası yok
                "limits": "Self-host donanım limiti (örn. 2x H100 80GB)",
                "status": status_for("vllm", enabled=settings.VLLM_ENABLED),
                "open_source": True,
            },
            {
                "name": "groq",
                "model": settings.GROQ_MODEL,
                "free_tier": True,
                "limits": f"{settings.GROQ_RPM_LIMIT} RPM, {settings.GROQ_TPM_LIMIT} TPM",
                "status": status_for(
                    "groq",
                    enabled=settings.GROQ_ENABLED,
                    configured=bool(settings.GROQ_API_KEY),
                ),
                "open_source": False,
            },
            {
                "name": "gemini",
                "model": settings.GEMINI_MODEL,
                "free_tier": True,
                "limits": f"{settings.GEMINI_RPM_LIMIT} RPM, {settings.GEMINI_TPD_LIMIT // 1000}K TPD",
                "status": status_for(
                    "gemini",
                    enabled=settings.GEMINI_ENABLED,
                    configured=bool(settings.GEMINI_API_KEY),
                ),
                "open_source": False,
            },
            {
                "name": "ollama",
                "model": settings.OLLAMA_MODEL,
                "free_tier": True,
                "limits": "Sınırsız (local)",
                "status": status_for(
                    "ollama",
                    enabled=settings.OLLAMA_ENABLED,
                    available_label="local",
                ),
                "open_source": True,
            },
            {
                "name": "g4f",
                "model": settings.G4F_MODEL,
                "free_tier": True,
                "limits": "Güvenilmez (son çare)",
                "status": status_for(
                    "g4f",
                    enabled=settings.G4F_ENABLED,
                    available_label="available",
                ),
                "open_source": False,
            },
        ],
        "fallback_order": settings.PROVIDER_ORDER,
        "provider_status": provider_status,
    }
