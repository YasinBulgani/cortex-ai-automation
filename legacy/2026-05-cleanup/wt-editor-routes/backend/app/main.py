"""Sentetik veri platformu API."""

from fastapi import FastAPI

from app.config import settings
from app.core.http import (
    configure_middlewares,
    register_probe_routes,
    register_request_tracing,
)
from app.core.openapi_config import custom_openapi_schema
from app.core.router_registry import register_api_routers
from app.core.security_middleware import (
    AuditLogMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.domains.artifacts.router import router as artifacts_router
from app.domains.auth.router import router as auth_router
from app.domains.catalog.router import router as catalog_router
from app.domains.jobs.router import router as jobs_router
from app.domains.rules.router import router as rules_router
from app.domains.notifications.router import router as notifications_router
from app.domains.tspm.router import router as tspm_router
from app.domains.automation.router import router as automation_router
from app.domains.audit.router import router as audit_router
from app.domains.ai.router import router as ai_router
from app.domains.agents.router import router as agents_router
from app.domains.api_testing.router import router as api_testing_router
from app.domains.ai_synthetic_data.router import router as synthetic_router
from app.domains.playwright_mcp.router import router as playwright_mcp_router
from app.domains.coverup.router import router as coverup_router
from app.domains.agents.v2.router import router as agents_v2_router
from app.domains.dsl.router import router as dsl_router
from app.domains.dsl.edit_router import router as dsl_edit_router
from app.domains.automation_suite.router import router as automation_suite_router

# Mobile modülü commit 77f5303'te main.py'a eklendi ancak kaynak dosyaları
# git add edilmemiş — import'u savunmacı yap, dizin gerçekten var olduğunda
# otomatik aktifleşsin. Modül eklenince bu guard kaldırılabilir.
try:
    from app.domains.mobile.router import router as mobile_router  # type: ignore
    _HAS_MOBILE_ROUTER = True
except ImportError:
    mobile_router = None  # type: ignore[assignment]
    _HAS_MOBILE_ROUTER = False

from app.domains.tspm.scheduler import shutdown_scheduler, start_scheduler
from app.infra.database import engine

initialize_sentry()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    fastapi_kwargs = {
        "title": settings.app_name,
        "lifespan": app_lifespan,
    }
    if settings.is_production_like:
        fastapi_kwargs.update(
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
        )

    app = FastAPI(**fastapi_kwargs)
    app.openapi = lambda: custom_openapi_schema(app)

    configure_prometheus(app)
    configure_middlewares(
        app,
        limiter=limiter,
        has_rate_limit=has_rate_limit,
        rate_limit_exception=rate_limit_exception,
        rate_limit_handler=rate_limit_handler,
    )
    register_request_tracing(app)
    register_probe_routes(app, has_rate_limit=has_rate_limit)
    register_api_routers(app)
    return app


def _startup_index_project() -> None:
    """
    Background: Proje kaynaklarını KnowledgeStore'a indexle.
    Startup'ta bir kez çalışır — feature files, docs, git log, e2e specs.
    """
    import time
    time.sleep(5)  # DB bağlantısının hazır olmasını bekle
    try:
        from app.domains.ai.knowledge_store import KnowledgeStore
        store = KnowledgeStore()

        # Zaten yeterli kayıt varsa tekrar indexleme
        stats = store.stats()
        total = stats.get("total", 0)
        if total > 100:
            _logger.info("KnowledgeStore zaten %d kayıt içeriyor, startup indexleme atlanıyor.", total)
            return

        import subprocess
        from pathlib import Path as _P

        project_root = _P(__file__).resolve().parent.parent.parent
        _logger.info("Startup proje indexleme başlıyor... (root: %s)", project_root)
        count = 0

        # 1. Feature dosyaları
        for base in [project_root / "engine" / "features", project_root / "e2e"]:
            if not base.exists():
                continue
            for f in sorted(base.rglob("*.feature")):
                text = f.read_text(encoding="utf-8", errors="ignore")
                if len(text.strip()) > 20:
                    store.ingest(text=text[:4000], source="feature_file", metadata={"file": str(f.relative_to(project_root))})
                    count += 1

        # 2. Docs
        docs_dir = project_root / "docs"
        if docs_dir.exists():
            for f in sorted(docs_dir.rglob("*.md")):
                text = f.read_text(encoding="utf-8", errors="ignore")
                if len(text.strip()) > 30:
                    store.ingest(text=text[:4000], source="docs", metadata={"file": str(f.relative_to(project_root))})
                    count += 1

        # 3. Git log (son 30 commit)
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-30", "--no-merges", "--format=%h %s"],
                cwd=str(project_root), capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                store.ingest(
                    text="Son commit'ler:\n" + result.stdout.strip(),
                    source="code_change",
                    metadata={"type": "startup_git_log"},
                )
                count += 1
        except Exception:
            pass

        _logger.info("Startup indexleme tamamlandı: %d kayıt eklendi.", count)
    except Exception as e:
        _logger.warning("Startup indexleme hatası: %s", e)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path(settings.artifacts_dir).mkdir(parents=True, exist_ok=True)
    start_scheduler()

    # Banking QA Ekibi — nightly scheduler otomatik başlat
    try:
        from app.domains.agents.banking_team.scheduler_agent import start_scheduler as start_banking_scheduler
        start_banking_scheduler()
    except Exception as _e:
        _logger.warning("Banking scheduler başlatılamadı: %s", _e)

    # Background: proje bilgisini KnowledgeStore'a indexle
    threading.Thread(target=_startup_index_project, daemon=True).start()

    # File watcher: feature/doc dosyalarını izle, değişince indexle
    try:
        from app.domains.ai.file_watcher import start_file_watcher, stop_file_watcher
        start_file_watcher()
    except Exception as _e:
        _logger.warning("File watcher başlatılamadı: %s", _e)

    yield

    # Shutdown
    try:
        from app.domains.ai.file_watcher import stop_file_watcher
        stop_file_watcher()
    except Exception:
        pass
    shutdown_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.openapi = lambda: custom_openapi_schema(app)

# ── Prometheus Metrikleri ─────────────────────────────────────────────────────
if _os.getenv("PROMETHEUS_ENABLED", "false").lower() in ("1", "true", "yes"):
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/ready", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics")
        _logger.info("Prometheus metrikleri aktif: /metrics")
    except ImportError:
        _logger.info("prometheus-fastapi-instrumentator kurulu değil, /metrics devre dışı.")

# Rate limiting middleware
if _HAS_RATE_LIMIT and limiter is not None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept", "Origin"],
)

# ── Security Middleware (OWASP headers, body-size limit, audit log) ───────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=10 * 1024 * 1024)
app.add_middleware(AuditLogMiddleware)


# ── Request ID Tracing Middleware ─────────────────────────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """Her request'e benzersiz ID ata — log tracing icin."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
    request.state.request_id = request_id
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health():
    """Temel canlılık kontrolü — yük dengeleyici için."""
    return {"status": "ok", "service": "testwright-ai-backend"}


@app.get("/ready")
def ready(request: Request):
    """
    Hazırlık kontrolü — DB + engine bağlantı durumunu döndürür.
    Kubernetes readinessProbe ve Uptime izleme için kullanılır.
    """
    result: dict = {"ready": True, "checks": {}}

    # ── DB bağlantı kontrolü ──────────────────────────────────────────
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        result["checks"]["database"] = {"status": "ok"}
    except Exception as exc:
        result["checks"]["database"] = {"status": "error", "detail": str(exc)[:120]}
        result["ready"] = False

    # ── Engine bağlantı kontrolü ──────────────────────────────────────
    try:
        import httpx as _httpx
        resp = _httpx.get(f"{settings.engine_base_url}/health", timeout=3.0)
        if resp.status_code == 200:
            result["checks"]["engine"] = {"status": "ok"}
        else:
            result["checks"]["engine"] = {"status": "degraded", "http": resp.status_code}
    except Exception as exc:
        result["checks"]["engine"] = {"status": "unreachable", "detail": str(exc)[:80]}
        # Engine erişilemezhsa backend çalışmaya devam eder — ready=False yapma

    # ── Rate limiter ──────────────────────────────────────────────────
    result["checks"]["rate_limiter"] = {"status": "ok" if _HAS_RATE_LIMIT else "disabled"}

    from fastapi.responses import JSONResponse
    status_code = 200 if result["ready"] else 503
    return JSONResponse(content=result, status_code=status_code)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(artifacts_router, prefix="/api/v1")
app.include_router(tspm_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(automation_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(api_testing_router)
app.include_router(synthetic_router, prefix="/api/v1")
app.include_router(playwright_mcp_router, prefix="/api/v1")
app.include_router(coverup_router, prefix="/api/v1")
app.include_router(agents_v2_router, prefix="/api/v1")
app.include_router(dsl_router, prefix="/api/v1")
app.include_router(dsl_edit_router, prefix="/api/v1")
app.include_router(automation_suite_router, prefix="/api/v1")
if _HAS_MOBILE_ROUTER and mobile_router is not None:
    app.include_router(mobile_router, prefix="/api/v1")
else:
    _logger.warning(
        "mobile_router yüklenemedi (app/domains/mobile/ modülü eksik); "
        "Mobile endpoint'leri devre dışı. Modül kaynak dosyalarının git add "
        "edildiğinden emin olun."
    )
