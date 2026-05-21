"""
SyntheticBankData — Ana uygulama giriş noktası.

FastAPI uygulamasını başlatır, middleware'leri yapılandırır ve
API yönlendirmelerini kaydeder.

Özellikler:
  - CORS middleware (geliştirme için tüm origin'ler açık)
  - Global exception handler'lar (HTTPException, ValueError, genel)
  - Startup/shutdown lifecycle event'leri
  - API router include (tüm /api/v1/* endpointleri)
  - Swagger UI Türkçe açıklamalar
  - Static file serving (ileride UI için hazır)
"""

import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.qa_routes import router as qa_router
from app.api.enhancement_routes import enhancement_router
from app.api.learning_routes import learning_router
from app.api.test_platform_routes import test_platform_router
from app.config import settings
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware


# ═══════════════════════════════════════════════════════════════════════
# Lifecycle Events (Startup / Shutdown)
# ═══════════════════════════════════════════════════════════════════════


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü yöneticisi.

    Startup:
      - Veritabanı tablolarını oluştur (geliştirme modu)
      - Geçici klasörleri hazırla
      - Başlangıç bilgilerini logla

    Shutdown:
      - Kaynakları temizle
    """
    # ── STARTUP ──────────────────────────────────────────────────
    print(f"[STARTUP] {settings.APP_NAME} v{settings.VERSION} başlatılıyor...")

    # Veritabanı tablolarını oluştur (geliştirme modu)
    if settings.DEBUG:
        try:
            from app.models.database import create_tables
            create_tables()
            print("[STARTUP] Veritabanı tabloları oluşturuldu/kontrol edildi.")
        except Exception as exc:
            print(f"[STARTUP] Veritabanı bağlantı uyarısı: {exc}")
            print("[STARTUP] Uygulama veritabanı olmadan başlatılıyor...")

    # Geçici upload/output klasörlerini oluştur
    import tempfile
    upload_dir = Path(tempfile.gettempdir()) / "syntheticbankdata_uploads"
    output_dir = Path(tempfile.gettempdir()) / "syntheticbankdata_outputs"
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[STARTUP] Upload klasörü: {upload_dir}")
    print(f"[STARTUP] Output klasörü: {output_dir}")

    # LLM durumunu kontrol et
    try:
        from app.services.llm_service import LLMService
        llm = LLMService()
        llm_info = f"provider={llm.provider.value}" if hasattr(llm, "provider") else f"provider={settings.LLM_PROVIDER}"
        print(f"[STARTUP] LLM servisi: {llm_info}")
    except Exception:
        print(f"[STARTUP] LLM servisi: fallback modu (LLM yapılandırılmamış)")

    print(f"[STARTUP] {settings.APP_NAME} hazır! Swagger UI: http://localhost:8000/docs")

    yield  # Uygulama çalışıyor

    # ── SHUTDOWN ─────────────────────────────────────────────────
    print(f"[SHUTDOWN] {settings.APP_NAME} kapatılıyor...")
    print("[SHUTDOWN] Kaynaklar temizlendi. Hoşça kal!")


# ═══════════════════════════════════════════════════════════════════════
# FastAPI Uygulama Tanımı
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Bankacılık alanında AI destekli sentetik veri üretim platformu.\n\n"
        "## Temel Özellikler\n\n"
        "- **Dosya Yükleme:** CSV, Excel, JSON formatlarında veri yükleme\n"
        "- **Şema Analizi:** Kolon tipleri, istatistikler ve pattern tespiti\n"
        "- **PII Tespiti:** KVKK uyumlu kişisel veri tespiti ve maskeleme\n"
        "- **Kural Çıkarımı:** Otomatik iş kuralları (aralık, enum, regex, dağılım)\n"
        "- **İlişki Tespiti:** Tablolar arası yabancı anahtar ve mantıksal ilişkiler\n"
        "- **Sentetik Üretim:** Kurala dayalı, senaryo bazlı ve doğal dil ile üretim\n"
        "- **12 Bankacılık Senaryosu:** Bireysel, premium, riskli, dormant vb.\n"
        "- **LLM Entegrasyonu:** OpenAI, Anthropic, Ollama veya fallback modu\n\n"
        "## Türkiye Bankacılık Domain Desteği\n\n"
        "- TCKN, IBAN (TR), Türk telefon numarası üretimi\n"
        "- KVKK (6698) uyumlu PII tespiti ve maskeleme\n"
        "- Türkçe isim, adres, şehir/ilçe verileri\n"
        "- Gerçek Türk banka BIN numaraları ve şube kodları\n"
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url=None,       # Özel /docs endpoint'i aşağıda tanımlandı (local assets)
    redoc_url=None,      # Özel /redoc endpoint'i aşağıda tanımlandı (local assets)
    openapi_url="/openapi.json",
    contact={
        "name": "SyntheticBankData Ekibi",
        "email": "info@syntheticbankdata.dev",
    },
    license_info={
        "name": "MIT",
    },
)


# ═══════════════════════════════════════════════════════════════════════
# Middleware Yapılandırması
# ═══════════════════════════════════════════════════════════════════════

# CORS — Geliştirme ortamı için tüm origin'ler açık
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Production'da kısıtlanmalı
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # Dosya indirme başlıkları
)

# Rate Limiter Middleware — IP bazlı sliding window
app.add_middleware(RateLimitMiddleware)

# Error Handler Middleware — Structured error responses + X-Request-ID
app.add_middleware(ErrorHandlerMiddleware)


# İstek süre ölçümü middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Her isteğin işlem süresini X-Process-Time başlığında döndür."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# ═══════════════════════════════════════════════════════════════════════
# Global Exception Handler'lar
# ═══════════════════════════════════════════════════════════════════════


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP hata yanıtlarını standart formatta döndür.

    Tüm HTTPException'lar Türkçe hata mesajı ile JSON olarak döner.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "path": str(request.url.path),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Değer doğrulama hatalarını 422 olarak döndür."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": f"Geçersiz değer: {str(exc)}",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Beklenmeyen hataları 500 olarak döndür.

    Production'da detaylı hata bilgisi gizlenir.
    """
    detail = None
    if settings.DEBUG:
        detail = traceback.format_exc()

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Sunucu hatası oluştu. Lütfen tekrar deneyin.",
            "detail": detail,
            "path": str(request.url.path),
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# API Router Kayıtları
# ═══════════════════════════════════════════════════════════════════════

# Ana API router'ı — tüm /api/v1/* endpointleri
app.include_router(api_router)

# QA Engine router'ı — /api/qa/* endpointleri
app.include_router(qa_router)

# Enhancement router'ı — audit, versioning, quality, webhooks, templates, platform
app.include_router(enhancement_router)

# Self-Learning router'ı — öğrenme, geri bildirim, optimizasyon, pattern'ler
app.include_router(learning_router)

# Test Platform router'ı — /api/v1/test-platform/* endpointleri
app.include_router(test_platform_router)


# Kök endpoint — Frontend SPA
@app.get(
    "/",
    summary="Frontend Arayüzü",
    description="SyntheticBankData React SPA arayüzünü serve eder.",
    tags=["Genel"],
    response_class=FileResponse,
)
async def serve_frontend():
    """Frontend index.html'i döndür."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    return FileResponse(str(frontend_path))


# ═══════════════════════════════════════════════════════════════════════
# Static Files — Frontend ve uygulama statik dosyaları
# ═══════════════════════════════════════════════════════════════════════

# Frontend klasörü — /frontend altında
_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(_frontend_dir)), name="frontend")

# App static dosyaları — /static altında
_app_static_dir = Path(__file__).parent / "static"
if _app_static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_app_static_dir)), name="static")


# ═══════════════════════════════════════════════════════════════════════
# Özel Swagger UI — Local Asset'ler (CDN'e bağımlılık yok)
# ═══════════════════════════════════════════════════════════════════════


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Swagger UI — local asset'lerden serve eder, CDN gerektirmez."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} — Swagger UI",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """ReDoc UI."""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} — ReDoc",
    )


# ═══════════════════════════════════════════════════════════════════════
# Dosya İndirme Endpoint'i (Static Files benzeri)
# ═══════════════════════════════════════════════════════════════════════


@app.get(
    "/api/v1/download/{filename:path}",
    summary="Dosya İndir",
    description="Üretilen sentetik veri dosyasını indirir.",
    tags=["İndirme"],
)
async def download_file(filename: str):
    """Üretilen dosyayı indirme endpoint'i."""
    import tempfile
    from fastapi.responses import FileResponse

    output_dir = Path(tempfile.gettempdir()) / "syntheticbankdata_outputs"
    file_path = (output_dir / filename).resolve()

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")

    # Güvenlik: path traversal koruması — dosya OUTPUT_DIR altında olmalı
    if not str(file_path).startswith(str(output_dir.resolve())):
        raise HTTPException(status_code=403, detail="Erişim reddedildi")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )
