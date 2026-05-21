"""
AI analiz endpoint'leri.

POST /api/ai/analyze-anomaly      — Test sonucu anomaly analizi
GET  /api/ai/flaky-report         — Flaky test raporu
POST /api/ai/coverage-gaps        — Coverage gap analizi
POST /api/ai/prioritize           — Test önceliklendirme
GET  /api/ai/stats                — LLM kullanım istatistikleri
POST /api/ai/analyze-assertions   — Test dosyası assertion analizi
POST /api/ai/security-scan        — Güvenlik taraması başlat
"""
from flask import Blueprint, request, jsonify

ai_analysis_bp = Blueprint("ai_analysis", __name__, url_prefix="/api/ai")


def _check_feature(name: str):
    from services import is_feature_enabled
    if not is_feature_enabled(name):
        return jsonify({"error": f"'{name}' özelliği ai_config.yaml'da devre dışı"}), 503
    return None


@ai_analysis_bp.route("/analyze-anomaly", methods=["POST"])
def analyze_anomaly():
    """Test çalışma sonuçlarında anomaly tespit eder."""
    blocked = _check_feature("anomaly_detection")
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    try:
        from services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        anomalies = detector.analyze_test_run(data)
        return jsonify({
            "anomaly_count": len(anomalies),
            "anomalies": [a.to_dict() for a in anomalies],
        })
    except Exception as exc:
        return jsonify({"error": f"Anomaly analizi başarısız: {exc}"}), 500


@ai_analysis_bp.route("/flaky-report", methods=["GET"])
def flaky_report():
    """Flaky test analiz raporunu döndürür."""
    blocked = _check_feature("flaky_detection")
    if blocked:
        return blocked
    try:
        from services.flaky_detector import FlakyDetector
        detector = FlakyDetector()
        results = detector.analyze_all()
        quarantined = [r for r in results if r.recommendation == "quarantine"]
        return jsonify({
            "total_analyzed": len(results),
            "quarantined_count": len(quarantined),
            "tests": [r.to_dict() for r in results],
        })
    except Exception as exc:
        return jsonify({"error": f"Flaky analiz başarısız: {exc}"}), 500


@ai_analysis_bp.route("/coverage-gaps", methods=["POST"])
def coverage_gaps():
    """Coverage raporunu analiz edip gap'leri döndürür."""
    blocked = _check_feature("coverage_analysis")
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    coverage_path = data.get("coverage_path", "reports/coverage.json")
    generate_suggestions = data.get("generate_suggestions", False)

    try:
        from services.coverage_analyzer import CoverageAnalyzer
        gw = None
        if generate_suggestions:
            from services import get_llm_gateway
            gw = get_llm_gateway()
            if not gw.available:
                return jsonify({"error": "LLM API anahtarı yapılandırılmamış (suggestion için gerekli)"}), 503

        analyzer = CoverageAnalyzer(gateway=gw)
        gaps = analyzer.analyze(coverage_json_path=coverage_path, generate_suggestions=generate_suggestions)
        return jsonify({
            "gap_count": len(gaps),
            "gaps": [g.to_dict() for g in gaps],
        })
    except Exception as exc:
        return jsonify({"error": f"Coverage analizi başarısız: {exc}"}), 500


@ai_analysis_bp.route("/prioritize", methods=["POST"])
def prioritize_tests():
    """Kod değişikliklerine göre testleri önceliklendirir."""
    data = request.get_json(silent=True) or {}
    try:
        from services.test_prioritizer import TestPrioritizer
        prioritizer = TestPrioritizer()
        result = prioritizer.prioritize(
            git_diff=data.get("git_diff"),
            time_budget_seconds=data.get("time_budget_seconds", 300),
            min_score_threshold=data.get("min_score_threshold", 0.1),
        )
        return jsonify(result.to_dict())
    except Exception as exc:
        return jsonify({"error": f"Önceliklendirme başarısız: {exc}"}), 500


@ai_analysis_bp.route("/stats", methods=["GET"])
def llm_stats():
    """LLM kullanım istatistiklerini döndürür."""
    try:
        from services import get_llm_gateway
        gw = get_llm_gateway()
        return jsonify(gw.stats.to_dict())
    except Exception as exc:
        return jsonify({"error": f"İstatistik alınamadı: {exc}"}), 500


@ai_analysis_bp.route("/analyze-assertions", methods=["POST"])
def analyze_assertions():
    """Test dosyasındaki eksik assertion'ları analiz eder."""
    from services import get_llm_gateway
    gw = get_llm_gateway()
    if not gw.available:
        return jsonify({"error": "LLM API anahtarı yapılandırılmamış"}), 503

    data = request.get_json(silent=True) or {}
    file_path = data.get("file_path", "").strip()
    if not file_path:
        return jsonify({"error": "file_path alanı zorunlu"}), 400

    try:
        from services.assertion_engine import AssertionEngine
        engine = AssertionEngine(gateway=gw)
        suggestions = engine.analyze_file(file_path)
        return jsonify({
            "file_path": file_path,
            "suggestion_count": len(suggestions),
            "suggestions": [s.to_dict() for s in suggestions],
        })
    except Exception as exc:
        return jsonify({"error": f"Assertion analizi başarısız: {exc}"}), 500


@ai_analysis_bp.route("/security-scan", methods=["POST"])
def security_scan():
    """Güvenlik taraması başlatır."""
    blocked = _check_feature("security_scanning")
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    target_url = data.get("target_url", "http://127.0.0.1:8000")
    scan_type = data.get("scan_type", "quick")

    try:
        from services.security_scanner import SecurityScanner
        scanner = SecurityScanner(target_url=target_url)

        if scan_type == "api" and data.get("openapi_spec_url"):
            findings = scanner.api_scan(data["openapi_spec_url"])
        else:
            findings = scanner.quick_scan()

        scanner.save_report(findings)
        return jsonify({
            "scan_type": scan_type,
            "target_url": target_url,
            "finding_count": len(findings),
            "findings": [f.to_dict() for f in findings],
        })
    except Exception as exc:
        return jsonify({"error": f"Güvenlik taraması başarısız: {exc}"}), 500
