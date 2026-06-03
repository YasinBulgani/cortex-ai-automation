"""
Analytics / Reporting routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/analytics_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/analytics.py — APIRouter, port 8000 (consolidated)

Bu pattern her route file için takip edilir. Bir Python developer kopyala-yapıştır + dönüştür yapar.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reporting", tags=["engine", "analytics"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class TestStepIn(BaseModel):
    name: str | None = None
    status: str | None = None
    duration_ms: int = 0
    timestamp: str | None = None
    error_message: str | None = None
    screenshot_path: str | None = None
    logs: list[str] = Field(default_factory=list)


class TestCaseIn(BaseModel):
    test_id: str | None = None
    name: str | None = None
    status: str | None = None
    duration_ms: int = 0
    timestamp: str | None = None
    feature: str | None = None
    tags: list[str] = Field(default_factory=list)
    steps: list[TestStepIn] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    error_message: str | None = None


class TestRunIn(BaseModel):
    run_id: str | None = None
    environment: str | None = None
    browser: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0
    test_cases: list[TestCaseIn] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class GenerateReportBody(BaseModel):
    test_run: TestRunIn
    formats: list[str] = Field(default_factory=lambda: ["html", "json"])
    include_charts: bool = True


class RecordRunBody(BaseModel):
    run_id: str = Field(..., min_length=1)
    environment: str | None = None
    browser: str | None = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0


class RecordFailureBody(BaseModel):
    test_name: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    error_message: str | None = None
    duration_ms: int = 0


# ─── Engine stubs (geçici — gerçek core import'ları ile değiştirilecek) ──────

def _get_report_generator():
    """
    Gerçek implementasyonda:
      from core.reporting_engine import get_report_generator
      return get_report_generator()
    """
    raise NotImplementedError("Reporting engine entegrasyonu henüz tamamlanmadı")


def _get_analytics_engine():
    """
    Gerçek implementasyonda:
      from core.analytics_engine import get_analytics_engine
      return get_analytics_engine()
    """
    raise NotImplementedError("Analytics engine entegrasyonu henüz tamamlanmadı")


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    """Reporting servisi sağlık kontrolü."""
    return {"status": "healthy", "service": "reporting", "version": "1.0.0"}


@router.post("/generate-report", status_code=status.HTTP_201_CREATED)
def generate_report(body: GenerateReportBody):
    """
    Kapsamlı test raporu üretir.

    test_run objesi içinde run_id, environment, browser, zaman damgaları,
    sayaçlar ve test_cases listesi beklenir.
    formats: ["html", "json"] gibi çıktı formatları.
    """
    try:
        generator = _get_report_generator()

        # Pydantic modeli → engine dataclass'larına dönüşüm
        # (engine sözleşmesi değişince bu mapping güncellenecek)
        from core.reporting_engine import TestRun, TestCase, TestStep  # type: ignore[import]

        test_cases = [
            TestCase(
                test_id=tc.test_id,
                name=tc.name,
                status=tc.status,
                duration_ms=tc.duration_ms,
                timestamp=tc.timestamp,
                feature=tc.feature,
                tags=tc.tags,
                steps=[
                    TestStep(
                        name=s.name,
                        status=s.status,
                        duration_ms=s.duration_ms,
                        timestamp=s.timestamp,
                        error_message=s.error_message,
                        screenshot_path=s.screenshot_path,
                        logs=s.logs,
                    )
                    for s in tc.steps
                ],
                attachments=tc.attachments,
                error_message=tc.error_message,
            )
            for tc in body.test_run.test_cases
        ]

        run = TestRun(
            run_id=body.test_run.run_id,
            environment=body.test_run.environment,
            browser=body.test_run.browser,
            start_time=body.test_run.start_time,
            end_time=body.test_run.end_time,
            total_tests=body.test_run.total_tests,
            passed=body.test_run.passed,
            failed=body.test_run.failed,
            skipped=body.test_run.skipped,
            duration_ms=body.test_run.duration_ms,
            test_cases=test_cases,
            metrics=body.test_run.metrics,
        )

        report_paths = generator.generate_report(
            run,
            formats=body.formats,
            include_charts=body.include_charts,
        )

        return {
            "success": True,
            "run_id": run.run_id,
            "reports": report_paths,
            "summary": {
                "total_tests": run.total_tests,
                "passed": run.passed,
                "failed": run.failed,
                "skipped": run.skipped,
                "success_rate": f"{run.success_rate:.2f}%",
                "duration_seconds": run.duration_ms / 1000,
            },
        }
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Rapor üretimi başarısız: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/record-run")
def record_test_run(body: RecordRunBody):
    """Test koşumu metriklerini analitik için kaydeder."""
    try:
        analytics = _get_analytics_engine()
        analytics.record_test_run(
            run_id=body.run_id,
            environment=body.environment,
            browser=body.browser,
            total_tests=body.total_tests,
            passed=body.passed,
            failed=body.failed,
            skipped=body.skipped,
            duration_ms=body.duration_ms,
        )
        success_rate = (body.passed / max(1, body.total_tests)) * 100
        return {
            "success": True,
            "run_id": body.run_id,
            "success_rate": f"{success_rate:.2f}%",
            "message": "Test run recorded successfully",
        }
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Test run kaydı başarısız: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/record-failure")
def record_failed_test(body: RecordFailureBody):
    """Başarısız test kaydeder."""
    try:
        analytics = _get_analytics_engine()
        analytics.record_failed_test(
            test_name=body.test_name,
            run_id=body.run_id,
            error_message=body.error_message,
            duration_ms=body.duration_ms,
        )
        return {"success": True, "test_name": body.test_name, "message": "Failed test recorded"}
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Başarısız test kaydı başarısız: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/trends")
def get_trends(
    metric_name: str | None = Query(None),
    hours: int = Query(24, ge=1),
):
    """Metrik trendlerini döndürür."""
    try:
        analytics = _get_analytics_engine()
        trends = analytics.analyze_trends(metric_name, hours)
        trends_data = {
            metric: {
                "current_value": trend.current_value,
                "previous_value": trend.previous_value,
                "direction": trend.direction,
                "change_percentage": f"{trend.change_percentage:.2f}%",
                "data_points": [
                    {"timestamp": p.timestamp, "value": p.value, "run_id": p.run_id}
                    for p in trend.data_points
                ],
            }
            for metric, trend in trends.items()
        }
        return {"success": True, "lookback_hours": hours, "trends": trends_data}
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Trend verisi alınamadı: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/risk-assessment")
def get_risk_assessment(hours: int = Query(24, ge=1)):
    """Test suite için risk değerlendirmesi döndürür."""
    try:
        analytics = _get_analytics_engine()
        risk = analytics.assess_risk(hours)
        return {
            "success": True,
            "risk_assessment": {
                "level": risk.level,
                "score": risk.score,
                "failing_tests": risk.failing_tests,
                "unstable_tests": risk.unstable_tests,
                "regression_risk": f"{risk.regression_risk:.2f}%",
                "recommendations": risk.recommendations,
            },
        }
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Risk değerlendirmesi başarısız: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/predictions")
def get_predictions(days: int = Query(7, ge=1)):
    """Hata tahminlerini döndürür."""
    try:
        analytics = _get_analytics_engine()
        predictions = analytics.predict_failures(days)
        return {"success": True, "lookback_days": days, "predictions": predictions}
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Tahmin üretimi başarısız: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/performance")
def get_performance_trends(hours: int = Query(24, ge=1)):
    """Performans trendlerini döndürür."""
    try:
        analytics = _get_analytics_engine()
        performance = analytics.get_performance_trends(hours)
        return {"success": True, "lookback_hours": hours, "performance": performance}
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Performans trendi alınamadı: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/report")
def get_analytics_report(export: str = Query("json")):
    """Kapsamlı analitik raporu döndürür."""
    try:
        analytics = _get_analytics_engine()
        report = analytics.generate_analytics_report()
        filepath = analytics.export_analytics(report, export)
        return {
            "success": True,
            "report_id": report.run_id,
            "timestamp": report.timestamp,
            "export_path": filepath,
            "risk_level": report.risk_assessment.level,
            "trends_summary": {
                metric: {
                    "direction": trend.direction,
                    "change": f"{trend.change_percentage:.2f}%",
                }
                for metric, trend in report.trends.items()
            },
            "recommendations": report.risk_assessment.recommendations,
        }
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Analitik raporu üretimi başarısız: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
