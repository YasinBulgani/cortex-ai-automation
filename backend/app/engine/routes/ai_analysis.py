from __future__ import annotations
"""
AI analiz endpoint'leri — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/ai_analysis_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/ai_analysis.py — APIRouter, port 8000 (consolidated)

POST /api/ai/analyze-anomaly      — Test sonucu anomaly analizi
GET  /api/ai/flaky-report         — Flaky test raporu
POST /api/ai/coverage-gaps        — Coverage gap analizi
POST /api/ai/prioritize           — Test önceliklendirme
GET  /api/ai/stats                — LLM kullanım istatistikleri
POST /api/ai/analyze-assertions   — Test dosyası assertion analizi
POST /api/ai/security-scan        — Güvenlik taraması başlat
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ai", tags=["engine", "ai-analysis"])


# ─── Schemas ─────────────────────────────────────────────────────────────

class AnomalyAnalyzeRequest(BaseModel):
    pass  # free-form payload; subclasses can extend


class AnomalyAnalyzeBody(BaseModel):
    model_config = {"extra": "allow"}


class CoverageGapsRequest(BaseModel):
    coverage_path: str = "reports/coverage.json"
    generate_suggestions: bool = False


class PrioritizeRequest(BaseModel):
    git_diff: str | None = None
    time_budget_seconds: int = 300
    min_score_threshold: float = 0.1


class AnalyzeAssertionsRequest(BaseModel):
    file_path: str = Field(..., min_length=1, description="Test dosyasının yolu")


class SecurityScanRequest(BaseModel):
    target_url: str = "http://127.0.0.1:8000"
    scan_type: str = "quick"
    openapi_spec_url: str | None = None


# ─── Feature-flag helper ─────────────────────────────────────────────────

def _require_feature(name: str) -> None:
    """Özellik devre dışıysa 503 fırlatır."""
    try:
        from services import is_feature_enabled  # type: ignore[import]
        if not is_feature_enabled(name):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"'{name}' özelliği ai_config.yaml'da devre dışı",
            )
    except ImportError:
        pass  # services paketi henüz yoksa flag kontrolü atla


# ─── Routes ──────────────────────────────────────────────────────────────

@router.post("/analyze-anomaly")
def analyze_anomaly(body: dict = {}):
    """Test çalışma sonuçlarında anomaly tespit eder."""
    _require_feature("anomaly_detection")
    try:
        from services.anomaly_detector import AnomalyDetector  # type: ignore[import]
        detector = AnomalyDetector()
        anomalies = detector.analyze_test_run(body)
        return {
            "anomaly_count": len(anomalies),
            "anomalies": [a.to_dict() for a in anomalies],
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly analizi başarısız: {exc}",
        )


@router.get("/flaky-report")
def flaky_report():
    """Flaky test analiz raporunu döndürür."""
    _require_feature("flaky_detection")
    try:
        from services.flaky_detector import FlakyDetector  # type: ignore[import]
        detector = FlakyDetector()
        results = detector.analyze_all()
        quarantined = [r for r in results if r.recommendation == "quarantine"]
        return {
            "total_analyzed": len(results),
            "quarantined_count": len(quarantined),
            "tests": [r.to_dict() for r in results],
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flaky analiz başarısız: {exc}",
        )


@router.post("/coverage-gaps")
def coverage_gaps(body: CoverageGapsRequest):
    """Coverage raporunu analiz edip gap'leri döndürür."""
    _require_feature("coverage_analysis")
    try:
        from services.coverage_analyzer import CoverageAnalyzer  # type: ignore[import]
        gw = None
        if body.generate_suggestions:
            from services import get_llm_gateway  # type: ignore[import]
            gw = get_llm_gateway()
            if not gw.available:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="LLM API anahtarı yapılandırılmamış (suggestion için gerekli)",
                )
        analyzer = CoverageAnalyzer(gateway=gw)
        gaps = analyzer.analyze(
            coverage_json_path=body.coverage_path,
            generate_suggestions=body.generate_suggestions,
        )
        return {
            "gap_count": len(gaps),
            "gaps": [g.to_dict() for g in gaps],
        }
    except HTTPException:
        raise
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coverage analizi başarısız: {exc}",
        )


@router.post("/prioritize")
def prioritize_tests(body: PrioritizeRequest):
    """Kod değişikliklerine göre testleri önceliklendirir."""
    try:
        from services.test_prioritizer import TestPrioritizer  # type: ignore[import]
        prioritizer = TestPrioritizer()
        result = prioritizer.prioritize(
            git_diff=body.git_diff,
            time_budget_seconds=body.time_budget_seconds,
            min_score_threshold=body.min_score_threshold,
        )
        return result.to_dict()
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Önceliklendirme başarısız: {exc}",
        )


@router.get("/stats")
def llm_stats():
    """LLM kullanım istatistiklerini döndürür."""
    try:
        from services import get_llm_gateway  # type: ignore[import]
        gw = get_llm_gateway()
        return gw.stats.to_dict()
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"İstatistik alınamadı: {exc}",
        )


@router.post("/analyze-assertions")
def analyze_assertions(body: AnalyzeAssertionsRequest):
    """Test dosyasındaki eksik assertion'ları analiz eder."""
    try:
        from services import get_llm_gateway  # type: ignore[import]
        gw = get_llm_gateway()
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))

    if not gw.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM API anahtarı yapılandırılmamış",
        )

    try:
        from services.assertion_engine import AssertionEngine  # type: ignore[import]
        engine = AssertionEngine(gateway=gw)
        suggestions = engine.analyze_file(body.file_path)
        return {
            "file_path": body.file_path,
            "suggestion_count": len(suggestions),
            "suggestions": [s.to_dict() for s in suggestions],
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assertion analizi başarısız: {exc}",
        )


@router.post("/security-scan")
def security_scan(body: SecurityScanRequest):
    """Güvenlik taraması başlatır."""
    _require_feature("security_scanning")
    try:
        from services.security_scanner import SecurityScanner  # type: ignore[import]
        scanner = SecurityScanner(target_url=body.target_url)

        if body.scan_type == "api" and body.openapi_spec_url:
            findings = scanner.api_scan(body.openapi_spec_url)
        else:
            findings = scanner.quick_scan()

        scanner.save_report(findings)
        return {
            "scan_type": body.scan_type,
            "target_url": body.target_url,
            "finding_count": len(findings),
            "findings": [f.to_dict() for f in findings],
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Güvenlik taraması başarısız: {exc}",
        )
