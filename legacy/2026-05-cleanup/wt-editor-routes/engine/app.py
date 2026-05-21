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

    load_dotenv(ROOT / ".env", override=True)
    load_dotenv(ROOT.parent / ".env", override=False)
except ImportError:
    # python-dotenv yoksa sessizce geç; kritik env'ler shell'den gelmeli.
    pass

from core.db import init_db

init_db()

UI_DIR = ROOT / "ui"
app = Flask(__name__, static_folder=str(UI_DIR / "static"), template_folder=str(UI_DIR / "templates"))
CORS(
    app,
    supports_credentials=True,
    origins=_cors_origin_list(),
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Internal-Key", "X-Requested-With"],
)
app.secret_key = _resolve_secret("ENGINE_SECRET_KEY", dev_fallback="dev-engine-session-secret")

ENGINE_PORT = int(os.environ.get("ENGINE_PORT", "5001"))
INTERNAL_KEY = _resolve_secret("ENGINE_INTERNAL_KEY", dev_fallback="dev-engine-internal-key")
INTERNAL_KEY_BLOCKED_PREFIXES = ("/api/editor", "/api/auth", "/api/webhooks/config")


def _has_scoped_internal_access() -> bool:
    provided = request.headers.get("X-Internal-Key", "")
    if not INTERNAL_KEY or not provided:
        return False
    if not hmac.compare_digest(provided, INTERNAL_KEY):
        return False
    return not any(request.path.startswith(prefix) for prefix in INTERNAL_KEY_BLOCKED_PREFIXES)

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    _HAS_PROMETHEUS = True
    REQUEST_COUNT = Counter(
        "bgts_engine_http_requests_total",
        "Total HTTP requests handled by the engine.",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "bgts_engine_http_request_duration_seconds",
        "HTTP request latency for the engine.",
        ["method", "path"],
    )
except ImportError:
    _HAS_PROMETHEUS = False


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

_optional_bps = [bp for bp in (mobile_bp,) if bp is not None]

for bp in [
    auth_bp, feature_bp, regression_bp, manual_bp, locators_bp,
    runner_bp, ai_bp, util_bp, datasim_bp, project_bp, lifecycle_bp,
    visual_bp, a11y_bp, recorder_bp, registry_bp, playback_bp, wizard_bp,
    ai_intel_bp, ai_gen_bp, ai_analysis_bp, ai_healing_bp, monkey_bp,
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


@app.route("/health")
def health_root():
    return jsonify({
        "status": "running",
        "service": "testwright-ai-automation-engine",
        "port": ENGINE_PORT,
    })


@app.route("/metrics")
def metrics_root():
    if not _HAS_PROMETHEUS:
        return jsonify({"error": "prometheus_client kurulu degil"}), 503
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=ENGINE_PORT, debug=_should_enable_flask_debug())
