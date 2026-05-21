"""
Self-healing endpoint'leri.

POST /api/ai/self-heal       — Kırık locator'ı heal et
POST /api/ai/find-element    — Accessibility tree'den element bul
GET  /api/ai/healing-log     — Healing geçmişini döndür
"""
import json
import logging
from pathlib import Path

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

ai_healing_bp = Blueprint("ai_healing", __name__, url_prefix="/api/ai")

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HEALING_LOG = _REPO_ROOT / "reports" / "healing-log.json"


def _check_feature(name: str):
    from services import is_feature_enabled
    if not is_feature_enabled(name):
        return jsonify({"error": f"'{name}' özelliği ai_config.yaml'da devre dışı"}), 503
    return None


@ai_healing_bp.route("/self-heal", methods=["POST"])
def self_heal():
    """Kırık locator için yeni locator önerisi üretir."""
    blocked = _check_feature("self_healing")
    if blocked:
        return blocked
    from services import get_llm_gateway
    gw = get_llm_gateway()
    if not gw.available:
        return jsonify({"error": "LLM API anahtarı yapılandırılmamış"}), 503

    data = request.get_json(silent=True) or {}
    failed_locator = data.get("failed_locator", "")
    if not failed_locator:
        return jsonify({"error": "failed_locator alanı zorunlu"}), 400

    try:
        from services.self_healer import SelfHealer
        healer = SelfHealer(gateway=gw)
        result = healer.heal(
            failed_locator=failed_locator,
            accessibility_tree=data.get("accessibility_tree", ""),
            error_message=data.get("error_message", ""),
            page_url=data.get("page_url", ""),
        )
        return jsonify(result.to_dict())
    except Exception as exc:
        return jsonify({"error": f"Self-heal başarısız: {exc}"}), 500


@ai_healing_bp.route("/find-element", methods=["POST"])
def find_element():
    """Accessibility tree'den hedef elementi bulmak için locator üretir."""
    from services import get_llm_gateway
    gw = get_llm_gateway()
    if not gw.available:
        return jsonify({"error": "LLM API anahtarı yapılandırılmamış"}), 503

    data = request.get_json(silent=True) or {}
    element_intent = data.get("element_intent", "")
    if not element_intent:
        return jsonify({"error": "element_intent alanı zorunlu"}), 400

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Verilen accessibility tree'den hedef elementi bul ve Playwright locator string'i döndür. "
                    "Sadece locator string döndür, başka bir şey yazma."
                ),
            },
            {
                "role": "user",
                "content": f"Hedef: {element_intent}\n\nAccessibility Tree:\n{data.get('accessibility_tree', '')[:6000]}",
            },
        ]
        resp = gw.complete(messages, model="gpt-4o-mini", temperature=0.1, max_tokens=150)
        locator = resp.content.strip().strip("`").strip('"').strip("'")
        return jsonify({"locator": locator, "model": resp.model, "cached": resp.cached})
    except Exception as exc:
        return jsonify({"error": f"Element arama başarısız: {exc}"}), 500


@ai_healing_bp.route("/healing-log", methods=["GET"])
def healing_log():
    """Healing geçmişini döndürür."""
    try:
        logs: list = []
        if _HEALING_LOG.exists():
            try:
                raw = json.loads(_HEALING_LOG.read_text(errors="replace"))
                logs = raw if isinstance(raw, list) else []
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                logger.debug("Healing log dosyası parse edilemedi: %s", exc)
                logs = []
        return jsonify({"total": len(logs), "entries": logs[-50:]})
    except Exception as exc:
        return jsonify({"error": f"Healing log okunamadı: {exc}"}), 500
