"""
AI Intelligence Routes — core/ katmanına ait ek AI yeteneklerini REST API olarak sunar.

Unique endpoints (services/ route'larında OLMAYAN):
  POST /api/ai/generate-locators — AI locator üretimi
  POST /api/ai/audit-locators    — Locator sağlık denetimi
  POST /api/ai/map-steps         — Step definition eşleme
  GET  /api/ai/feedback-insights — Feedback loop insight'ları
  GET  /api/ai/quality-score     — Genel kalite skoru
  POST /api/ai/security-analyze  — AI güvenlik analizi (header tabanlı)
  POST /api/ai/perf-analyze      — Performans darboğaz analizi
  POST /api/ai/optimize-suite    — Test suite optimizasyonu
"""
from flask import Blueprint, request, jsonify

ai_intel_bp = Blueprint("ai_intelligence", __name__, url_prefix="/api/ai")


@ai_intel_bp.route("/generate-locators", methods=["POST"])
def generate_locators():
    """AI ile locator üret."""
    data = request.json or {}
    element_desc = data.get("element_description", "")
    page_content = data.get("page_content", "")

    if not element_desc:
        return jsonify({"error": "element_description required"}), 400

    try:
        from core.ai_locator import AILocatorGenerator
        generator = AILocatorGenerator()
        suggestions = generator.generate_for_element(
            element_description=element_desc,
            page_content=page_content,
        )
        return jsonify({
            "suggestions": [
                {
                    "strategy": s.strategy,
                    "selector": s.selector,
                    "confidence": s.confidence,
                    "stability": s.stability,
                    "reason": s.reason,
                }
                for s in suggestions
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_intel_bp.route("/audit-locators", methods=["POST"])
def audit_locators():
    """Locator sağlık denetimi."""
    try:
        data = request.json or {}
        json_path = data.get("json_path", "")

        from core.ai_locator import LocatorAuditor
        auditor = LocatorAuditor()

        if json_path:
            report = auditor.audit_from_json(json_path)
            return jsonify(report.to_dict())

        results = auditor.audit_all_json_files()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_intel_bp.route("/map-steps", methods=["POST"])
def map_steps():
    """Gherkin step'lerini mevcut definition'larla eşle."""
    data = request.json or {}
    feature_content = data.get("feature_content", "")

    if not feature_content:
        return jsonify({"error": "feature_content required"}), 400

    try:
        from core.ai_bdd import StepDefinitionMapper
        mapper = StepDefinitionMapper()
        mappings = mapper.map_feature(feature_content)

        return jsonify({
            "total_steps": len(mappings),
            "mapped": sum(1 for m in mappings if not m.is_new),
            "new": sum(1 for m in mappings if m.is_new),
            "mappings": [
                {
                    "step": m.gherkin_step,
                    "mapped_to": m.mapped_definition,
                    "is_new": m.is_new,
                    "suggested_code": m.suggested_code if m.is_new else "",
                }
                for m in mappings
            ],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_intel_bp.route("/feedback-insights", methods=["GET"])
def feedback_insights():
    """Feedback loop insight'ları."""
    try:
        from core.feedback_loop.collector import ResultCollector
        from core.feedback_loop.analyzer import PatternAnalyzer

        collector = ResultCollector()
        analyzer = PatternAnalyzer()
        history = collector.get_history()
        insights = analyzer.analyze(history)

        return jsonify({
            "history_count": len(history),
            "insights": [
                {
                    "type": i.type,
                    "severity": i.severity,
                    "description": i.description,
                    "suggestion": i.suggestion,
                    "affected_tests": i.affected_tests,
                    "confidence": i.confidence,
                }
                for i in insights
            ],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_intel_bp.route("/quality-score", methods=["GET"])
def quality_score():
    """Genel kalite skoru."""
    try:
        from core.feedback_loop.collector import ResultCollector
        from core.feedback_loop.optimizer import SuiteOptimizer

        collector = ResultCollector()
        optimizer = SuiteOptimizer()
        history = collector.get_history()

        report = optimizer.optimize(history)

        return jsonify({
            "quality_score": report.quality_score,
            "quarantined_tests": optimizer.get_quarantined(),
            "optimization_actions": len(report.actions),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_intel_bp.route("/security-analyze", methods=["POST"])
def security_analyze():
    """AI güvenlik analizi (header tabanlı)."""
    data = request.json or {}
    url = data.get("url", "")
    headers = data.get("headers", {})

    if not url:
        return jsonify({"error": "url required"}), 400

    try:
        from core.ai_security import VulnerabilityAnalyzer
        analyzer = VulnerabilityAnalyzer()

        if headers:
            report = analyzer.analyze_headers(headers, url)
            return jsonify(report.to_dict())

        import requests as req_lib
        resp = req_lib.get(url, timeout=10, verify=False)
        report = analyzer.analyze_headers(dict(resp.headers), url)
        return jsonify(report.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_intel_bp.route("/perf-analyze", methods=["POST"])
def perf_analyze():
    """Performans darboğaz analizi."""
    data = request.json or {}
    results = data.get("results", {})

    if not results:
        return jsonify({"error": "results required"}), 400

    try:
        from core.ai_performance import BottleneckAnalyzer, ThresholdOptimizer
        bn_analyzer = BottleneckAnalyzer()
        bottlenecks = bn_analyzer.analyze(results)

        th_optimizer = ThresholdOptimizer()
        th_optimizer.record_results(results)
        regressions = th_optimizer.detect_regression(results)

        return jsonify({
            "bottlenecks": [
                {
                    "component": b.component,
                    "metric": b.metric,
                    "value": b.value,
                    "severity": b.severity,
                    "description": b.description,
                    "recommendation": b.recommendation,
                }
                for b in bottlenecks
            ],
            "regressions": regressions,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_intel_bp.route("/optimize-suite", methods=["POST"])
def optimize_suite():
    """Test suite optimizasyonu."""
    try:
        from core.feedback_loop.collector import ResultCollector
        from core.feedback_loop.optimizer import SuiteOptimizer

        collector = ResultCollector()
        optimizer = SuiteOptimizer()
        history = collector.get_history()

        report = optimizer.optimize(history)
        return jsonify(report.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
