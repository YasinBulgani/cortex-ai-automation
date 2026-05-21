
from flask import Blueprint, request, jsonify, current_app, send_from_directory, send_file
from pathlib import Path
import io
import zipfile
import requests as req
import time
from core.db import get_run_history, get_run_stats, get_comprehensive_reports
from config.settings import settings, BASE_DIR

util_bp = Blueprint('util', __name__)

@util_bp.route("/api/settings", methods=["GET"])
def get_settings():
    env_file = BASE_DIR / ".env"
    env_data = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env_data[k.strip()] = v.strip()
    return jsonify({
        "BASE_URL": env_data.get("BASE_URL", settings.BASE_URL),
        "BROWSER": env_data.get("BROWSER", settings.BROWSER),
        "HEADLESS": env_data.get("HEADLESS", str(settings.HEADLESS).lower()),
        "OPENAI_MODEL": env_data.get("OPENAI_MODEL", settings.OPENAI_MODEL),
        "OPENAI_API_BASE": env_data.get("OPENAI_API_BASE", settings.OPENAI_BASE_URL),
        "has_api_key": bool(env_data.get("OPENAI_API_KEY", "")),
    })

@util_bp.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.json or {}
    env_file = BASE_DIR / ".env"
    existing = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    
    mapping = {
        "BASE_URL": "BASE_URL",
        "BROWSER": "BROWSER",
        "HEADLESS": "HEADLESS",
        "OPENAI_MODEL": "OPENAI_MODEL",
        "OPENAI_API_KEY": "OPENAI_API_KEY",
        "OPENAI_API_BASE": "OPENAI_API_BASE"
    }
    for key, env_key in mapping.items():
        if key in data and data[key] is not None:
             existing[env_key] = str(data[key])
             
    content = "\n".join([f"{k}={v}" for k, v in existing.items()])
    env_file.write_text(content, encoding="utf-8")
    return jsonify({"ok": True})

@util_bp.route("/api/stats")
def stats():
    return jsonify({"totals": get_run_stats(), "history": get_run_history()})

@util_bp.route("/api/reports/comprehensive")
def reports_comprehensive():
    return jsonify(get_comprehensive_reports())

@util_bp.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})

@util_bp.route("/api/request", methods=["POST"])
def proxy_request():
    data = request.json or {}
    url = data.get("url")
    method = data.get("method", "GET").upper()
    headers_list = data.get("headers", [])
    body = data.get("body", "")
    if not url: return jsonify({"error": "URL yok"}), 400
    if not url.startswith("http"): url = "http://" + url
    req_headers = {h['key']: h['value'] for h in headers_list if h.get('key') and h.get('value')}
    try:
        start = time.time()
        response = req.request(method, url, headers=req_headers, data=body.encode('utf-8') if body else None, timeout=30)
        duration = (time.time() - start) * 1000
        return jsonify({
            "status": response.status_code, 
            "headers": dict(response.headers), 
            "body": response.text,
            "time": duration
        })
    except Exception as e: return jsonify({"error": str(e)}), 500

@util_bp.route("/api/export", methods=["GET"])
def export_data():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        if settings.FEATURES_DIR.exists():
            for f in settings.FEATURES_DIR.rglob("*.feature"):
                rel_path = f.relative_to(settings.FEATURES_DIR)
                zf.write(f, arcname=f"features/{rel_path}")
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"test_automation_export_{int(time.time())}.zip", as_attachment=True)
