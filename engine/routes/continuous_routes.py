"""
Sürekli Arka Plan Test Üretimi Routes (Checksum tarzı)
═══════════════════════════════════════════════════════════════════════════

Çekirdek: ``core.continuous_discovery``. Periyodik keşif + dedup.

  POST /api/continuous/start    — Always-on döngüyü başlat
  POST /api/continuous/stop     — Durdur
  POST /api/continuous/run-once — Tek tur çalıştır (senkron; test/CI için)
  GET  /api/continuous/status   — Çalışma durumu + son tur + registry boyutu
  GET  /api/continuous/health
"""
import logging
import traceback

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

continuous_bp = Blueprint("continuous", __name__)


@continuous_bp.route("/api/continuous/health", methods=["GET"])
def api_continuous_health():
    return jsonify({"status": "ok", "capability": "continuous-test-generation"})


@continuous_bp.route("/api/continuous/start", methods=["POST"])
def api_continuous_start():
    """Always-on keşif döngüsünü başlatır.

    Body: ``{ "targets": ["https://app..."], "interval_minutes": 60,
              "max_pages": 8, "max_flows": 6 }``
    """
    data = request.json or {}
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        return jsonify({"error": "dolu 'targets' listesi gereklidir"}), 400
    try:
        from core.continuous_discovery import get_manager

        result = get_manager().start(
            targets=[str(t) for t in targets],
            interval_minutes=int(data.get("interval_minutes", 60) or 60),
            max_pages=int(data.get("max_pages", 8) or 8),
            max_flows=int(data.get("max_flows", 6) or 6),
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("continuous start failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@continuous_bp.route("/api/continuous/stop", methods=["POST"])
def api_continuous_stop():
    try:
        from core.continuous_discovery import get_manager

        return jsonify({"status": "ok", **get_manager().stop()})
    except Exception as e:
        logger.exception("continuous stop failed")
        return jsonify({"error": str(e)}), 500


@continuous_bp.route("/api/continuous/status", methods=["GET"])
def api_continuous_status():
    try:
        from core.continuous_discovery import get_manager

        return jsonify({"status": "ok", **get_manager().status()})
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e)}), 200


@continuous_bp.route("/api/continuous/run-once", methods=["POST"])
def api_continuous_run_once():
    """Tek bir keşif turunu senkron çalıştırır (dedup dahil). Test/CI için.

    Body: ``{ "targets": [...], "max_pages": 8, "max_flows": 6 }``
    """
    data = request.json or {}
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        return jsonify({"error": "dolu 'targets' listesi gereklidir"}), 400
    try:
        from core.continuous_discovery import run_cycle

        result = run_cycle(
            [str(t) for t in targets],
            max_pages=int(data.get("max_pages", 8) or 8),
            max_flows=int(data.get("max_flows", 6) or 6),
            cycle_index=int(data.get("cycle_index", 0) or 0),
            persist=bool(data.get("persist", True)),
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("continuous run-once failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
