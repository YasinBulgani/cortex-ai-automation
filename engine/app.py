"""
TestwrightAI Test Automation Engine — Flask backend
Test altyapısını yönetmek için REST API + SSE ile gerçek zamanlı test çıktısı.

Monorepo servisleri:
  - backend/  → FastAPI (Sentetik Veri + TSPM) port 8000
  - engine/   → Flask  (Test Otomasyon Motoru) port 5001
  - apps/web/ → Next.js (Frontend)             port 3000
"""
import logging
import hmac
import os
import sys
import time
from pathlib import Path
from flask import Flask, Response, g, jsonify, redirect, request, send_from_directory, session, url_for
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# .env dosyalarını (engine/.env ve repo root .env) mümkün olduğunca erken yükle
# ki INTERNAL_KEY gibi env değişkenleri process shell'inden ÖNCE .env'den
# okunsun (shell'deki eski değerler override edilmesin).
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    load_dotenv(ROOT.parent / ".env", override=False)
except ImportError:
    # python-dotenv yoksa sessizce geç; kritik env'ler shell'den gelmeli.
    pass

from core.db import init_db

init_db()

UI_DIR = ROOT / "ui"
app = Flask(__name__, static_folder=str(UI_DIR / "static"), template_folder=str(UI_DIR / "templates"))

# ── OpenTelemetry (opsiyonel — SDK kurulu değilse no-op) ────────────────────
try:
    from app.infra.telemetry import init_otel  # type: ignore
    init_otel(
        service_name="neurex-engine",
        instrument_flask=True,
        flask_app=app,
        instrument_sqlalchemy=True,
    )
except ImportError:
    # Monorepo'dan çalıştırılmıyorsa sessizce geç
    try:
        sys.path.insert(0, str(ROOT.parent / "backend"))
        from app.infra.telemetry import init_otel  # type: ignore
        init_otel(service_name="neurex-engine", instrument_flask=True, flask_app=app)
    except ImportError:
        pass
_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000",
).split(",")
CORS(app, supports_credentials=True, origins=_ALLOWED_ORIGINS)

# ── Güvenlik sırları — production doğrulaması ───────────────────────────────
# Engine Flask session ve backend↔engine iç trafik anahtarları. Varsayılan
# string'lerin production'a sızması çok tehlikelidir (session tahmini,
# yetkisiz iç API çağrısı). Bu yüzden `APP_ENV in {production,staging}`
# iken varsayılan değer tespit edilirse startup'ta hata fırlatılır.
_INSECURE_SESSION_DEFAULT = "super_secret_ai_automation_key"
_INSECURE_INTERNAL_KEY_DEFAULT = "bgts-internal-key-change-me"


def _is_prod_env() -> bool:
    env = (os.environ.get("APP_ENV") or os.environ.get("ENV") or "").strip().lower()
    return env in {"production", "prod", "staging"}


_session_key = os.environ.get("ENGINE_SECRET_KEY", _INSECURE_SESSION_DEFAULT)
_internal_key = os.environ.get("ENGINE_INTERNAL_KEY", _INSECURE_INTERNAL_KEY_DEFAULT)

if _is_prod_env():
    _fatal = []
    if _session_key == _INSECURE_SESSION_DEFAULT:
        _fatal.append("ENGINE_SECRET_KEY")
    if _internal_key == _INSECURE_INTERNAL_KEY_DEFAULT:
        _fatal.append("ENGINE_INTERNAL_KEY")
    if _fatal:
        raise RuntimeError(
            "KRİTİK GÜVENLİK: production/staging ortamında aşağıdaki env "
            f"değişkenleri varsayılan değerle çalışıyor: {_fatal}. "
            "Her biri için 'openssl rand -hex 32' ile üretilmiş benzersiz "
            "değerler atayın."
        )

app.secret_key = _session_key
INTERNAL_KEY = _internal_key

# Geliştirme modunda bile varsayılanlar kullanıldığında uyarı logla
if _session_key == _INSECURE_SESSION_DEFAULT or _internal_key == _INSECURE_INTERNAL_KEY_DEFAULT:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "GÜVENLİK UYARISI: Engine sırlarından biri varsayılan değerde "
        "(yalnızca geliştirme modunda kabul edilebilir). Üretime çıkmadan "
        "ENGINE_SECRET_KEY ve ENGINE_INTERNAL_KEY override edin."
    )

ENGINE_PORT = int(os.environ.get("ENGINE_PORT", "5001"))

# ── Metrics helpers ──────────────────────────────────────────────────────────
_app_start_time: float = time.time()


def _active_sessions_ref() -> dict:
    """Late-bound reference to recorder_routes._active_sessions (avoids circular import)."""
    try:
        from routes.recorder_routes import _active_sessions  # noqa: PLC0415
        return _active_sessions
    except Exception:
        return {}

try:
    from prometheus_client import Counter, Histogram, REGISTRY as _PROM_REGISTRY
    try:
        REQUEST_COUNT = Counter(
            "engine_http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )
        REQUEST_LATENCY = Histogram(
            "engine_http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint"],
        )
    except ValueError:
        REQUEST_COUNT = _PROM_REGISTRY._names_to_collectors.get("engine_http_requests_total")
        REQUEST_LATENCY = _PROM_REGISTRY._names_to_collectors.get("engine_http_request_duration_seconds")
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False
    REQUEST_COUNT = None
    REQUEST_LATENCY = None

# Kullanıcı-odaklı (editor/auth/webhook) endpoint'lerde iç key bypass'ı yok.
_INTERNAL_ACCESS_EXCLUDED = ("/api/editor", "/auth", "/config/webhook")


def _has_scoped_internal_access() -> bool:
    """Backend iç servis çağrısı için scoped key doğrulaması."""
    if any(request.path.startswith(p) for p in _INTERNAL_ACCESS_EXCLUDED):
        return False
    key = request.headers.get("X-Internal-Key", "")
    if not key:
        return False
    # Request anında oku — test yeniden yüklemelerinde dotenv override sorununu önler
    current_key = os.environ.get("ENGINE_INTERNAL_KEY", _INSECURE_INTERNAL_KEY_DEFAULT)
    return hmac.compare_digest(key, current_key)


@app.before_request
def require_login():
    # Backend'den gelen iç servis çağrıları için scoped trust:
    # editor/auth/webhook config gibi kullanıcı-odaklı endpoint'lerde bypass yok.
    if _has_scoped_internal_access():
        return

    public_endpoints = [
        'index',
        'auth.auth_login_page', 'auth.register', 'auth.login', 'auth.verify_email',
        'static', 'ui_files', 'health_root',
        'ai_openapi.openapi_spec',
        'webhooks.github_webhook',
        'webhooks.gitlab_webhook',
        'webhooks.generic_webhook',
    ]
    if request.method == "OPTIONS" or request.endpoint in public_endpoints:
        return

    if 'user_id' not in session:
        if (
            request.path.startswith('/api/')
            or request.path == "/metrics"
            or request.path.startswith("/reports/allure-report")
            or request.path.startswith("/reports/allure-results")
        ):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for('auth.auth_login_page'))

    from config.settings import settings
    active_project = session.get('active_project', None)
    settings.set_active_project(active_project)


@app.before_request
def _start_metrics_timer():
    if _HAS_PROMETHEUS:
        g._request_start_time = time.perf_counter()


@app.after_request
def _record_metrics(response: Response):
    if _HAS_PROMETHEUS:
        route_label = request.url_rule.rule if request.url_rule else request.path
        REQUEST_COUNT.labels(request.method, route_label, str(response.status_code)).inc()
        started = getattr(g, "_request_start_time", None)
        if started is not None:
            REQUEST_LATENCY.labels(request.method, route_label).observe(time.perf_counter() - started)
    return response


# ─── Blueprints ──────────────────────────────────────────────────────────────
from routes.auth_routes import auth_bp
from routes.feature_routes import feature_bp
from routes.regression_routes import regression_bp
from routes.manual_routes import manual_bp
from routes.locators_routes import locators_bp
from routes.runner_routes import runner_bp
from routes.ai_routes import ai_bp
from routes.utility_routes import util_bp
from routes.datasim_routes import datasim_bp
from routes.project_routes import project_bp
from routes.lifecycle_routes import lifecycle_bp
from routes.visual_routes import visual_bp
from routes.accessibility_routes import a11y_bp
from routes.recorder_routes import recorder_bp
from routes.registry_routes import registry_bp
from routes.playback_routes import playback_bp
from routes.wizard_routes import wizard_bp
from routes.ai_intelligence_routes import ai_intel_bp
from routes.ai_generation_routes import ai_gen_bp
from routes.ai_analysis_routes import ai_analysis_bp
from routes.ai_healing_routes import ai_healing_bp
from routes.monkey_routes import monkey_bp
from routes.llm_agent_routes import llm_agent_bp
from routes.ai_openapi import ai_openapi_bp
from routes.tm_routes import tm_bp
from routes.jira_routes import jira_bp
from routes.analytics_routes import reporting_bp
from routes.banking_routes import banking_bp
from routes.magic_test_routes import magic_test_bp
from routes.pipeline_routes import pipeline_bp
from routes.scheduler_routes import scheduler_bp
from routes.webhook_routes import webhook_bp

# mobile_routes bağımlılıkları opsiyonel (core.device_profiles repo'da olmayabilir).
# Mobile blueprint'i yüklenemezse diğer servisleri bozmadan atlayalım.
try:
    from routes.mobile_routes import mobile_bp  # type: ignore
except Exception as _mobile_import_err:  # noqa: BLE001
    mobile_bp = None
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "mobile_routes blueprint yüklenemedi, atlanıyor: %s", _mobile_import_err,
    )

try:
    from routes.device_manager_routes import device_mgr_bp  # type: ignore
except Exception as _dm_import_err:  # noqa: BLE001
    device_mgr_bp = None
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "device_manager_routes blueprint yüklenemedi, atlanıyor: %s", _dm_import_err,
    )

_optional_bps = [bp for bp in (mobile_bp, device_mgr_bp) if bp is not None]

for bp in [
    auth_bp, feature_bp, regression_bp, manual_bp, locators_bp,
    runner_bp, ai_bp, util_bp, datasim_bp, project_bp, lifecycle_bp,
    visual_bp, a11y_bp, recorder_bp, registry_bp, playback_bp, wizard_bp,
    ai_intel_bp, ai_gen_bp, ai_analysis_bp, ai_healing_bp, monkey_bp, llm_agent_bp,
    ai_openapi_bp, tm_bp, jira_bp, reporting_bp, banking_bp, magic_test_bp,
    pipeline_bp, scheduler_bp, webhook_bp, *_optional_bps,
]:
    app.register_blueprint(bp)

# editor_routes uses function-based registration (no Blueprint)
from routes.editor_routes import register_editor_routes
register_editor_routes(app)


# ─── Views ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(UI_DIR / "templates"), "index.html")


@app.route("/ui/<path:filename>")
def ui_files(filename):
    return send_from_directory(str(UI_DIR), filename)


@app.route("/reports/allure-report/<path:filename>")
def serve_allure_report(filename):
    return send_from_directory(str(ROOT / "allure-report"), filename)


@app.route("/reports/allure-report/")
def serve_allure_index():
    return send_from_directory(str(ROOT / "allure-report"), "index.html")


@app.route("/api/reports/allure-results/<path:filename>")
def serve_allure_results_static(filename):
    """Allure sonuç dosyalarını statik olarak serve eder."""
    return send_from_directory(str(ROOT / "allure-results"), filename)


@app.route("/metrics")
def metrics_endpoint():
    if not _HAS_PROMETHEUS:
        return jsonify({"error": "Prometheus not available"}), 503
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
    except Exception:
        return jsonify({"error": "Metrics unavailable"}), 503


@app.route("/health")
def health_root():
    return jsonify({
        "status": "running",
        "service": "testwright-ai-automation-engine",
        "port": ENGINE_PORT,
    })


@app.route("/metrics")
def metrics_root():
    """Prometheus-compatible text format metrics (basic counters).

    Exposes enough for a dashboard scrape or ``curl /metrics`` healthcheck.
    Extend with ``prometheus_client`` when a real Prometheus scrape target is needed.
    """
    import time
    import gc

    uptime_seconds = time.time() - _app_start_time
    gc_stats = gc.get_count()
    active_sessions = len(_active_sessions_ref()) if callable(_active_sessions_ref) else 0

    lines = [
        "# HELP engine_uptime_seconds Seconds since engine process started",
        "# TYPE engine_uptime_seconds gauge",
        f"engine_uptime_seconds {uptime_seconds:.1f}",
        "",
        "# HELP engine_active_recording_sessions Number of in-memory recording sessions",
        "# TYPE engine_active_recording_sessions gauge",
        f"engine_active_recording_sessions {active_sessions}",
        "",
        "# HELP engine_gc_generation_0_count Python GC generation 0 object count",
        "# TYPE engine_gc_generation_0_count gauge",
        f"engine_gc_generation_0_count {gc_stats[0]}",
        "",
        "# HELP engine_gc_generation_1_count Python GC generation 1 object count",
        "# TYPE engine_gc_generation_1_count gauge",
        f"engine_gc_generation_1_count {gc_stats[1]}",
        "",
    ]
    from flask import Response  # local import keeps top-level imports clean
    return Response("\n".join(lines), mimetype="text/plain; version=0.0.4; charset=utf-8")


# ─── Deprecated route sunset header'ları (ADR-0002) ────────────────────────
# docs/architecture/engine-backend-contract.md'de tanımlanan emekli route'lar
# için otomatik "Sunset" ve "Deprecation" header'ları. 6 ay sonra (2026-10)
# bu endpoint'ler backend'e delege edilip engine'den silinecek.
_DEPRECATED_ROUTE_PREFIXES = (
    "/api/banking",          # → backend /api/v1/synthetic-data/banking
    "/api/datasim",          # → backend /api/v1/synthetic-data
    "/api/analytics",        # → backend /api/v1/tspm/analytics
    "/api/reporting",        # → backend /api/v1/tspm/reports
)
_SUNSET_DATE = "Sun, 01 Jun 2026 00:00:00 GMT"


@app.after_request
def _mark_deprecated_routes(response):
    path = request.path or ""
    if any(path.startswith(prefix) for prefix in _DEPRECATED_ROUTE_PREFIXES):
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = _SUNSET_DATE
        response.headers["Link"] = (
            '</docs/architecture/engine-backend-contract.md>; '
            'rel="deprecation"; type="text/markdown"'
        )
    return response


def _should_enable_flask_debug() -> bool:
    """CI veya production ortamında debug modunu devre dışı bırakır."""
    if _is_prod_env():
        return False
    if os.environ.get("CI", "").lower() in ("true", "1", "yes"):
        return False
    return os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")


if __name__ == "__main__":
    # threaded=False: Playwright sync API is bound to the thread that created it.
    # Flask's default thread pool assigns each request to a different worker thread,
    # causing "cannot switch to a different thread" errors. Single-threaded mode
    # keeps all requests on the same thread so Playwright objects stay valid.
    app.run(host="0.0.0.0", port=ENGINE_PORT, debug=_should_enable_flask_debug(), threaded=False)
