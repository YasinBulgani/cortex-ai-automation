"""
Çok-Sinyalli Self-Healing Routes
═══════════════════════════════════════════════════════════════════════════

mabl tarzı çok-sinyalli locator iyileştirme. Çekirdek: ``core.self_healing.multi_signal``.

  POST /api/self-heal/fingerprint — Canlı URL+selector'dan zengin parmak izi yakala
  POST /api/self-heal/heal        — Canlı sayfada en iyi çok-sinyalli eşleşmeyi bul
  POST /api/self-heal/score       — Saf skorlama (browser'sız; CI/test için)
  GET  /api/self-heal/health      — Yetenek durumu
"""
import logging
import traceback

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

self_heal_bp = Blueprint("self_heal", __name__)


@self_heal_bp.route("/api/self-heal/health", methods=["GET"])
def api_self_heal_health():
    from core.self_healing.multi_signal import _WEIGHTS, _DEFAULT_THRESHOLD

    return jsonify({
        "status": "ok",
        "capability": "multi-signal-self-healing",
        "signals": list(_WEIGHTS.keys()),
        "default_threshold": _DEFAULT_THRESHOLD,
    })


@self_heal_bp.route("/api/self-heal/score", methods=["POST"])
def api_self_heal_score():
    """Saf çok-sinyalli skorlama — browser gerektirmez.

    Body: ``{ "fingerprint": {...}, "candidates": [{...}] }``
    Dönüş: adaylar skora göre sıralı.
    """
    data = request.json or {}
    fp = data.get("fingerprint")
    candidates = data.get("candidates")
    if not isinstance(fp, dict) or not isinstance(candidates, list):
        return jsonify({"error": "fingerprint (dict) ve candidates (list) gereklidir"}), 400

    try:
        from core.self_healing.multi_signal import rank_candidates, best_selector

        ranked = rank_candidates(fp, candidates)
        top = ranked[0] if ranked else None
        return jsonify({
            "status": "ok",
            "ranked": ranked,
            "best": {"selector": best_selector(top), "score": top["score"]} if top else None,
        })
    except Exception as e:
        logger.exception("self-heal score failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@self_heal_bp.route("/api/self-heal/fingerprint", methods=["POST"])
def api_self_heal_fingerprint():
    """Canlı sayfadaki bir selector'dan zengin parmak izi yakalar.

    Body: ``{ "url": ..., "selector": "#login-btn" }``
    """
    data = request.json or {}
    url = str(data.get("url", "")).strip()
    selector = str(data.get("selector", "")).strip()
    if not url or not selector:
        return jsonify({"error": "url ve selector gereklidir"}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from playwright.sync_api import sync_playwright
        from core.self_healing.multi_signal import capture_fingerprint

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(viewport={"width": 1280, "height": 800}).new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(800)
            fp = capture_fingerprint(page, selector)
            browser.close()

        if fp is None:
            return jsonify({"status": "not_found", "selector": selector}), 200
        return jsonify({"status": "ok", "fingerprint": fp})
    except Exception as e:
        logger.exception("self-heal fingerprint failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@self_heal_bp.route("/api/self-heal/heal", methods=["POST"])
def api_self_heal_heal():
    """Kırılan locator için canlı sayfada en iyi çok-sinyalli eşleşmeyi bulur.

    Body: ``{ "url": ..., "fingerprint": {...}, "threshold": 0.55 }``
    """
    data = request.json or {}
    url = str(data.get("url", "")).strip()
    fp = data.get("fingerprint")
    if not url or not isinstance(fp, dict):
        return jsonify({"error": "url ve fingerprint (dict) gereklidir"}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    threshold = float(data.get("threshold", 0.55) or 0.55)

    try:
        from playwright.sync_api import sync_playwright
        from core.self_healing.multi_signal import heal

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(viewport={"width": 1280, "height": 800}).new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(800)
            result = heal(page, fp, threshold=threshold)
            browser.close()

        if result is None:
            return jsonify({"status": "no_match", "threshold": threshold}), 200
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("self-heal heal failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
