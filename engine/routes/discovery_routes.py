"""
Otonom Test Keşfi (Autonomous Test Discovery) Routes
═══════════════════════════════════════════════════════════════════════════

İnsan senaryo yazmadan hedef uygulamayı gezip kritik akışları test koduna
çeviren uçtan uca endpoint'ler. Çekirdek mantık: ``core.auto_discovery``.

Endpoint'ler:
  POST /api/discovery/run       — Tam pipeline (crawl → akış sentezi → Gherkin + DB)
  POST /api/discovery/crawl     — Sadece crawl (sayfa yapısı döndürür)
  POST /api/discovery/synthesize— Verili sayfalardan sadece akış sentezi
  GET  /api/discovery/health    — Yetenek/erişilebilirlik durumu
"""
import logging
import traceback

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

discovery_bp = Blueprint("discovery", __name__)


@discovery_bp.route("/api/discovery/health", methods=["GET"])
def api_discovery_health():
    """Keşif yeteneğinin hazır olup olmadığını döndürür (LLM erişimi dahil)."""
    try:
        from services import get_llm_gateway

        gw = get_llm_gateway()
        return jsonify({
            "status": "ok",
            "capability": "autonomous-test-discovery",
            "llm_available": bool(gw.available),
            "gateway_proxy": bool(getattr(gw, "use_gateway_proxy", False)),
        })
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e)}), 200


@discovery_bp.route("/api/discovery/run", methods=["POST"])
def api_discovery_run():
    """
    Tam otonom keşif pipeline'ı.

    Body::

        {
          "url": "https://app.example.com",   (zorunlu)
          "max_pages": 12,                      (opsiyonel)
          "max_flows": 8,                       (opsiyonel)
          "persist": true,                      (opsiyonel — DB'ye manuel test yaz)
          "credentials": { login_url, username_selector, username,
                           password_selector, password, submit_selector }
        }

    Üretilen feature'lar doğrudan ``/api/wizard/run-neurex`` ile koşturulabilir.
    """
    data = request.json or {}
    url = str(data.get("url", "")).strip()
    if not url:
        return jsonify({"error": "URL gereklidir"}), 400

    max_pages = int(data.get("max_pages", 12) or 12)
    max_flows = int(data.get("max_flows", 8) or 8)
    persist = bool(data.get("persist", True))
    credentials = data.get("credentials")

    # Aşırı geniş crawl'ı sınırla (kötüye kullanım / zaman aşımı koruması)
    max_pages = max(1, min(max_pages, 40))
    max_flows = max(1, min(max_flows, 20))

    try:
        from core.auto_discovery import run_discovery

        result = run_discovery(
            start_url=url,
            max_pages=max_pages,
            max_flows=max_flows,
            credentials=credentials if isinstance(credentials, dict) else None,
            persist=persist,
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("Discovery run failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@discovery_bp.route("/api/discovery/crawl", methods=["POST"])
def api_discovery_crawl():
    """Sadece crawl adımı — keşfedilen sayfa yapısını döndürür (akış sentezi yok)."""
    data = request.json or {}
    url = str(data.get("url", "")).strip()
    if not url:
        return jsonify({"error": "URL gereklidir"}), 400

    max_pages = max(1, min(int(data.get("max_pages", 12) or 12), 40))
    credentials = data.get("credentials")

    try:
        from core.auto_discovery import discover_pages

        pages = discover_pages(
            url,
            max_pages=max_pages,
            credentials=credentials if isinstance(credentials, dict) else None,
        )
        return jsonify({"status": "ok", "pages_crawled": len(pages), "pages": pages})
    except Exception as e:
        logger.exception("Discovery crawl failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@discovery_bp.route("/api/discovery/synthesize", methods=["POST"])
def api_discovery_synthesize():
    """Verilen sayfa yapısından sadece akış sentezi + Gherkin üretir (crawl'sız).

    Body: ``{ "url": <base_url>, "pages": [...], "max_flows": 8, "persist": false }``
    ``pages`` formatı /api/discovery/crawl çıktısıyla aynıdır.
    """
    data = request.json or {}
    url = str(data.get("url", "")).strip()
    pages = data.get("pages") or []
    if not url or not isinstance(pages, list) or not pages:
        return jsonify({"error": "url ve dolu pages listesi gereklidir"}), 400

    max_flows = max(1, min(int(data.get("max_flows", 8) or 8), 20))
    persist = bool(data.get("persist", False))

    try:
        from core.auto_discovery import (
            synthesize_flows,
            flow_to_gherkin,
            persist_flow,
        )

        flows = synthesize_flows(pages, url, max_flows=max_flows)
        features = []
        for flow in flows:
            flow["feature"] = flow_to_gherkin(flow, url)
            if persist:
                try:
                    flow["test_id"] = persist_flow(flow)
                except Exception as exc:
                    logger.warning("synthesize persist hatası: %s", exc)
                    flow["test_id"] = None
            features.append({"title": flow["title"], "content": flow["feature"]})

        return jsonify({
            "status": "ok",
            "flows": flows,
            "features": features,
            "stats": {"flows": len(flows)},
        })
    except Exception as e:
        logger.exception("Discovery synthesize failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
