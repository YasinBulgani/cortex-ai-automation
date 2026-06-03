"""
Semantik Görsel AI Routes
═══════════════════════════════════════════════════════════════════════════

Çekirdek: ``core.semantic_visual``. Pixel farkını DOM bileşenlerine atfeder,
dinamik bölgeleri otomatik eler.

  POST /api/visual-semantic/attribute — Saf atıf (browser'sız; değişen kutular → bileşenler)
  POST /api/visual-semantic/snapshot  — URL'den png + layout + dinamik bölgeler
  POST /api/visual-semantic/compare   — İki png + layout → semantik fark
  GET  /api/visual-semantic/health
"""
import base64
import logging
import traceback

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

visual_semantic_bp = Blueprint("visual_semantic", __name__)


@visual_semantic_bp.route("/api/visual-semantic/health", methods=["GET"])
def api_vs_health():
    deps = {}
    try:
        import numpy  # noqa: F401
        deps["numpy"] = True
    except Exception:
        deps["numpy"] = False
    try:
        import PIL  # noqa: F401
        deps["pillow"] = True
    except Exception:
        deps["pillow"] = False
    return jsonify({"status": "ok", "capability": "semantic-visual-ai", "deps": deps})


@visual_semantic_bp.route("/api/visual-semantic/attribute", methods=["POST"])
def api_vs_attribute():
    """Saf atıf — değişen bölgeleri DOM bileşenlerine eşler (browser gerektirmez).

    Body: ``{ "changed_boxes": [{x,y,w,h}], "layout_boxes": [{selector,role,text,x,y,w,h}],
              "dynamic_boxes": [{x,y,w,h}] }``
    """
    data = request.json or {}
    changed = data.get("changed_boxes") or []
    layout = data.get("layout_boxes") or []
    dynamic = data.get("dynamic_boxes") or []
    if not isinstance(changed, list) or not isinstance(layout, list):
        return jsonify({"error": "changed_boxes ve layout_boxes liste olmalı"}), 400
    try:
        from core.semantic_visual import attribute_to_components, subtract_dynamic

        real, noise = subtract_dynamic(changed, dynamic)
        components = attribute_to_components(real, layout)
        return jsonify({
            "status": "ok",
            "verdict": "changed" if components else "match",
            "changed_components": components,
            "noise_filtered": len(noise),
            "real_changed_regions": len(real),
        })
    except Exception as e:
        logger.exception("visual-semantic attribute failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@visual_semantic_bp.route("/api/visual-semantic/snapshot", methods=["POST"])
def api_vs_snapshot():
    """URL için png (base64) + DOM layout + dinamik bölgeler döndürür."""
    data = request.json or {}
    url = str(data.get("url", "")).strip()
    if not url:
        return jsonify({"error": "url gereklidir"}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    detect_dynamic = bool(data.get("detect_dynamic", True))

    try:
        from playwright.sync_api import sync_playwright
        from core.semantic_visual import capture_with_layout, detect_dynamic_regions

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(viewport={"width": 1280, "height": 800}).new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(800)
            cap = capture_with_layout(page)
            dynamic = detect_dynamic_regions(page) if detect_dynamic else []
            browser.close()

        return jsonify({
            "status": "ok",
            "png_b64": base64.b64encode(cap["png"]).decode(),
            "layout": cap["layout"],
            "dynamic_regions": dynamic,
        })
    except Exception as e:
        logger.exception("visual-semantic snapshot failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@visual_semantic_bp.route("/api/visual-semantic/compare", methods=["POST"])
def api_vs_compare():
    """İki png'yi (base64) semantik karşılaştırır.

    Body: ``{ "baseline_png_b64": ..., "current_png_b64": ...,
              "layout_boxes": [...], "dynamic_boxes": [...] }``
    """
    data = request.json or {}
    b_png = data.get("baseline_png_b64")
    c_png = data.get("current_png_b64")
    if not b_png or not c_png:
        return jsonify({"error": "baseline_png_b64 ve current_png_b64 gereklidir"}), 400
    try:
        from core.semantic_visual import semantic_compare

        result = semantic_compare(
            base64.b64decode(b_png),
            base64.b64decode(c_png),
            layout_boxes=data.get("layout_boxes") or [],
            dynamic_boxes=data.get("dynamic_boxes") or [],
            px_threshold=int(data.get("px_threshold", 25) or 25),
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("visual-semantic compare failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
