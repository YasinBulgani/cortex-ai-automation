"""
Gereksinim Connector Routes — Dış kaynaktan test üretimi (içe-dönük)
═══════════════════════════════════════════════════════════════════════════

Jira ticket / Confluence PRD / ham metin → test case + Gherkin.
Çekirdek: ``core.requirement_ingest``. (Jira'ya bug PUSH eden dışa-dönük
entegrasyon ``routes/jira_routes.py``'de ayrı durur.)

  POST /api/connectors/text-to-tests        — Ham metin → test
  POST /api/connectors/jira/issue-to-tests  — Jira issue → test
  POST /api/connectors/confluence/page-to-tests — Confluence sayfası → test
  GET  /api/connectors/health
"""
import logging
import traceback

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

connector_bp = Blueprint("connectors", __name__)


@connector_bp.route("/api/connectors/health", methods=["GET"])
def api_connectors_health():
    jira_ready = False
    try:
        from routes.jira_routes import get_jira_client
        jira_ready = get_jira_client() is not None
    except Exception:
        jira_ready = False
    try:
        import httpx  # noqa: F401
        confluence_ready = True
    except Exception:
        confluence_ready = False
    return jsonify({
        "status": "ok",
        "capability": "requirement-ingest",
        "sources": {"text": True, "jira": jira_ready, "confluence": confluence_ready},
    })


@connector_bp.route("/api/connectors/text-to-tests", methods=["POST"])
def api_text_to_tests():
    """Ham gereksinim metninden test üretir.

    Body: ``{ "text": ..., "title": "", "target_url": null, "persist": false, "gherkin": true }``
    """
    data = request.json or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"error": "text gereklidir"}), 400
    try:
        from core.requirement_ingest import text_to_tests

        result = text_to_tests(
            text,
            title=str(data.get("title", "")),
            target_url=data.get("target_url"),
            persist=bool(data.get("persist", False)),
            gherkin=bool(data.get("gherkin", True)),
            source=str(data.get("source", "manual")),
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("text-to-tests failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@connector_bp.route("/api/connectors/jira/issue-to-tests", methods=["POST"])
def api_jira_issue_to_tests():
    """Jira issue'sundan test üretir. Body: ``{ "issue_key": "PROJ-123", ... }``"""
    data = request.json or {}
    issue_key = str(data.get("issue_key", "")).strip()
    if not issue_key:
        return jsonify({"error": "issue_key gereklidir"}), 400
    try:
        from core.requirement_ingest import jira_issue_to_tests

        result = jira_issue_to_tests(
            issue_key,
            persist=bool(data.get("persist", False)),
            gherkin=bool(data.get("gherkin", True)),
            target_url=data.get("target_url"),
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("jira issue-to-tests failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@connector_bp.route("/api/connectors/confluence/page-to-tests", methods=["POST"])
def api_confluence_page_to_tests():
    """Confluence sayfasından test üretir.

    Body: ``{ "base_url": "https://x.atlassian.net", "page_id": "12345",
              "email": ..., "api_token": ..., "persist": false }``
    """
    data = request.json or {}
    required = ("base_url", "page_id", "email", "api_token")
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"error": f"eksik alanlar: {', '.join(missing)}"}), 400
    try:
        from core.requirement_ingest import confluence_page_to_tests

        result = confluence_page_to_tests(
            base_url=str(data["base_url"]),
            page_id=str(data["page_id"]),
            email=str(data["email"]),
            api_token=str(data["api_token"]),
            persist=bool(data.get("persist", False)),
            gherkin=bool(data.get("gherkin", True)),
            target_url=data.get("target_url"),
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.exception("confluence page-to-tests failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
