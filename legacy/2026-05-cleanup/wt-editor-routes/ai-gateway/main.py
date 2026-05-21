"""
Nexus QA — AI Gateway Ana Uygulama
FastAPI mikroservisi, port 8080

Başlatmak için:
  uvicorn main:app --host 0.0.0.0 --port 8080 --reload
  veya:
  make gateway-dev
"""
from __future__ import annotations

import logging
import sys
import time

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes.ai_routes import router as ai_router

# ── Loglama Ayarları ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("nexusqa.gateway")

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    _HAS_PROMETHEUS = True
    REQUEST_COUNT = Counter(
        "bgts_ai_gateway_http_requests_total",
        "Total HTTP requests handled by the AI gateway.",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "bgts_ai_gateway_http_request_duration_seconds",
        "HTTP request latency for the AI gateway.",
        ["method", "path"],
    )
except ImportError:
    _HAS_PROMETHEUS = False


# ── Lifespan (startup / shutdown) ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} başlatıldı (port {settings.PORT})")
    logger.info(f"   Fallback zinciri: {' → '.join(settings.PROVIDER_ORDER)}")
    logger.info(f"   Groq API key: {'✓' if settings.GROQ_API_KEY else '✗ (eksik)'}")
    logger.info(f"   Gemini API key: {'✓' if settings.GEMINI_API_KEY else '✗ (eksik)'}")
    logger.info(f"   Ollama URL: {settings.OLLAMA_BASE_URL}")
    yield
    # shutdown
    logger.info("AI Gateway kapatılıyor...")


# ── FastAPI Uygulaması ──────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Nexus QA AI Gateway — Groq / Gemini / Ollama / g4f fallback zinciri. "
        "Tüm AI istekleri bu mikroservis üzerinden geçer."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da backend/frontend URL'leriyle sınırla
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Loglama Middleware ───────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    if _HAS_PROMETHEUS:
        route_label = request.scope.get("route").path if request.scope.get("route") else request.url.path
        REQUEST_COUNT.labels(request.method, route_label, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, route_label).observe(elapsed_ms / 1000)
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({elapsed_ms}ms)"
    )
    return response


# ── Route'lar ────────────────────────────────────────────────────────────────
app.include_router(ai_router)


# ── Kök endpoint ────────────────────────────────────────────────────────────
@app.get("/", tags=["Meta"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/ai/health",
        "providers": "/ai/providers",
    }


@app.get("/ping", tags=["Meta"])
async def ping():
    return {"pong": True}


@app.get("/metrics", tags=["Meta"])
async def metrics():
    if not _HAS_PROMETHEUS:
        return Response('{"error":"prometheus_client kurulu degil"}', media_type="application/json", status_code=503)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
