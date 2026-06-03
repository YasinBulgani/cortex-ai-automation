"""
AI Root-Cause Analizi (RCA) Routes
═══════════════════════════════════════════════════════════════════════════

Başarısız testlerin kök nedenini AI ile sınıflandıran endpoint'ler.
Çekirdek mantık: ``core.root_cause``.

  POST /api/rca/analyze        — Tek başarısızlık analizi
  POST /api/rca/analyze-batch  — Çoklu başarısızlık + kategori dağılımı
  GET  /api/rca/health         — Yetenek durumu
"""
import logging
import traceback

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

rca_bp = Blueprint("rca", __name__)


@rca_bp.route("/api/rca/health", methods=["GET"])
def api_rca_health():
    try:
        from services import get_llm_gateway

        gw = get_llm_gateway()
        return jsonify({
            "status": "ok",
            "capability": "ai-root-cause-analysis",
            "categories": ["PRODUCT_BUG", "TEST_ISSUE", "ENVIRONMENT", "AUTOMATION_DEBT", "UNKNOWN"],
            "llm_available": bool(gw.available),
            "heuristic_fallback": True,
        })
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e)}), 200


@rca_bp.route("/api/rca/analyze", methods=["POST"])
def api_rca_analyze():
    """
    Tek bir başarısızlığın kök nedenini üretir.

    Body::

        {
          "test_name": "test_login",
          "error_message": "TimeoutError: waiting for selector #submit",
          "stack_trace": "...",          (opsiyonel)
          "failed_step": "Giriş Yap'a tıkla",  (opsiyonel)
          "html_snippet": "<form>...",   (opsiyonel)
          "console_logs": ["..."],       (opsiyonel)
          "use_llm": true                 (opsiyonel — false ise sadece heuristik)
        }
    """
    data = request.json or {}
    if not data.get("error_message") and not data.get("failed_step"):
        return jsonify({"error": "error_message veya failed_step gereklidir"}), 400

    try:
        from core.root_cause import analyze_failure

        result = analyze_failure(
            test_name=str(data.get("test_name", "")),
            error_message=str(data.get("error_message", "")),
            stack_trace=str(data.get("stack_trace", "")),
            failed_step=str(data.get("failed_step", "")),
            html_snippet=str(data.get("html_snippet", "")),
            console_logs=data.get("console_logs"),
            use_llm=bool(data.get("use_llm", True)),
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("RCA analyze failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@rca_bp.route("/api/rca/analyze-batch", methods=["POST"])
def api_rca_analyze_batch():
    """Çoklu başarısızlık analizi + kategori dağılımı.

    Body: ``{ "failures": [ {test_name, error_message, ...}, ... ], "use_llm": true }``
    """
    data = request.json or {}
    failures = data.get("failures")
    if not isinstance(failures, list) or not failures:
        return jsonify({"error": "dolu 'failures' listesi gereklidir"}), 400

    # Aşırı yük / maliyet koruması
    if len(failures) > 50:
        failures = failures[:50]

    try:
        from core.root_cause import analyze_batch

        result = analyze_batch(failures, use_llm=bool(data.get("use_llm", True)))
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("RCA batch failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
