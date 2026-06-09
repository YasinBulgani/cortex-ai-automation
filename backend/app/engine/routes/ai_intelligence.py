"""
AI Intelligence Routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/ai_intelligence_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/ai_intelligence.py — APIRouter, port 8000 (consolidated)

core/ katmanına ait ek AI yeteneklerini REST API olarak sunar.
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

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ai", tags=["engine", "ai-intelligence"])


# ─── Schemas ─────────────────────────────────────────────────────────────

class GenerateLocatorsRequest(BaseModel):
    element_description: str = Field(..., min_length=1)
    page_content: str = ""


class AuditLocatorsRequest(BaseModel):
    json_path: str = ""


class MapStepsRequest(BaseModel):
    feature_content: str = Field(..., min_length=1)


class SecurityAnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1)
    headers: dict[str, str] = {}


class PerfAnalyzeRequest(BaseModel):
    results: dict = Field(..., description="Performans test sonuçları")


# ─── Routes ──────────────────────────────────────────────────────────────

@router.post("/generate-locators")
def generate_locators(body: GenerateLocatorsRequest):
    """AI ile locator üret."""
    try:
        from core.ai_locator import AILocatorGenerator  # type: ignore[import]
        generator = AILocatorGenerator()
        suggestions = generator.generate_for_element(
            element_description=body.element_description,
            page_content=body.page_content,
        )
        return {
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
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/audit-locators")
def audit_locators(body: AuditLocatorsRequest):
    """Locator sağlık denetimi."""
    try:
        from core.ai_locator import LocatorAuditor  # type: ignore[import]
        auditor = LocatorAuditor()

        if body.json_path:
            report = auditor.audit_from_json(body.json_path)
            return report.to_dict()

        return auditor.audit_all_json_files()
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/map-steps")
def map_steps(body: MapStepsRequest):
    """Gherkin step'lerini mevcut definition'larla eşle."""
    try:
        from core.ai_bdd import StepDefinitionMapper  # type: ignore[import]
        mapper = StepDefinitionMapper()
        mappings = mapper.map_feature(body.feature_content)

        return {
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
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/feedback-insights")
def feedback_insights():
    """Feedback loop insight'ları."""
    try:
        from core.feedback_loop.analyzer import PatternAnalyzer  # type: ignore[import]
        from core.feedback_loop.collector import ResultCollector  # type: ignore[import]

        collector = ResultCollector()
        analyzer = PatternAnalyzer()
        history = collector.get_history()
        insights = analyzer.analyze(history)

        return {
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
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/quality-score")
def quality_score():
    """Genel kalite skoru."""
    try:
        from core.feedback_loop.collector import ResultCollector  # type: ignore[import]
        from core.feedback_loop.optimizer import SuiteOptimizer  # type: ignore[import]

        collector = ResultCollector()
        optimizer = SuiteOptimizer()
        history = collector.get_history()
        report = optimizer.optimize(history)

        return {
            "quality_score": report.quality_score,
            "quarantined_tests": optimizer.get_quarantined(),
            "optimization_actions": len(report.actions),
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/security-analyze")
def security_analyze(body: SecurityAnalyzeRequest):
    """AI güvenlik analizi (header tabanlı)."""
    try:
        from core.ai_security import VulnerabilityAnalyzer  # type: ignore[import]
        analyzer = VulnerabilityAnalyzer()

        if body.headers:
            report = analyzer.analyze_headers(body.headers, body.url)
            return report.to_dict()

        import requests as req_lib  # type: ignore[import]
        resp = req_lib.get(body.url, timeout=10, verify=True)
        report = analyzer.analyze_headers(dict(resp.headers), body.url)
        return report.to_dict()
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/perf-analyze")
def perf_analyze(body: PerfAnalyzeRequest):
    """Performans darboğaz analizi."""
    try:
        from core.ai_performance import BottleneckAnalyzer, ThresholdOptimizer  # type: ignore[import]
        bn_analyzer = BottleneckAnalyzer()
        bottlenecks = bn_analyzer.analyze(body.results)

        th_optimizer = ThresholdOptimizer()
        th_optimizer.record_results(body.results)
        regressions = th_optimizer.detect_regression(body.results)

        return {
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
        }
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/optimize-suite")
def optimize_suite():
    """Test suite optimizasyonu."""
    try:
        from core.feedback_loop.collector import ResultCollector  # type: ignore[import]
        from core.feedback_loop.optimizer import SuiteOptimizer  # type: ignore[import]

        collector = ResultCollector()
        optimizer = SuiteOptimizer()
        history = collector.get_history()
        report = optimizer.optimize(history)
        return report.to_dict()
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
