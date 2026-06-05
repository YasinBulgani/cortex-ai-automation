"""
Reporting & Analytics routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/reporting_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/reporting.py — APIRouter, port 8000 (consolidated)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reporting", tags=["engine", "reporting"])


# ─── Schemas ─────────────────────────────────────────────────────────────────


class TestStepIn(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    duration_ms: int = 0
    timestamp: Optional[str] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    logs: list[str] = Field(default_factory=list)


class TestCaseIn(BaseModel):
    test_id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    duration_ms: int = 0
    timestamp: Optional[str] = None
    feature: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    steps: list[TestStepIn] = Field(default_factory=list)
    attachments: list[Any] = Field(default_factory=list)
    error_message: Optional[str] = None


class TestRunIn(BaseModel):
    run_id: Optional[str] = None
    environment: Optional[str] = None
    browser: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0
    test_cases: list[TestCaseIn] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class GenerateReportRequest(BaseModel):
    test_run: Optional[TestRunIn] = None
    formats: list[str] = Field(default_factory=lambda: ["html", "json"])
    include_charts: bool = True


class RecordRunRequest(BaseModel):
    run_id: Optional[str] = None
    environment: Optional[str] = None
    browser: Optional[str] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0


class RecordFailureRequest(BaseModel):
    test_name: Optional[str] = None
    run_id: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: int = 0


# ─── Helpers — lazy imports so missing core.python deps don't break startup ───


def _get_report_generator():
    from core.python.reporting_engine import get_report_generator  # type: ignore
    return get_report_generator()


def _get_analytics_engine():
    from core.python.analytics_engine import get_analytics_engine  # type: ignore
    return get_analytics_engine()


def _build_test_run(data: TestRunIn):
    from core.python.reporting_engine import TestCase, TestRun, TestStep  # type: ignore

    test_cases = []
    for tc in data.test_cases:
        steps = [
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
        ]
        test_cases.append(
            TestCase(
                test_id=tc.test_id,
                name=tc.name,
                status=tc.status,
                duration_ms=tc.duration_ms,
                timestamp=tc.timestamp,
                feature=tc.feature,
                tags=tc.tags,
                steps=steps,
                attachments=tc.attachments,
                error_message=tc.error_message,
            )
        )

    return TestRun(
        run_id=data.run_id,
        environment=data.environment,
        browser=data.browser,
        start_time=data.start_time,
        end_time=data.end_time,
        total_tests=data.total_tests,
        passed=data.passed,
        failed=data.failed,
        skipped=data.skipped,
        duration_ms=data.duration_ms,
        test_cases=test_cases,
        metrics=data.metrics,
    )


# ─── Routes ──────────────────────────────────────────────────────────────────


@router.get("/health")
def health():
    """Health check for reporting service."""
    return {"status": "healthy", "service": "reporting", "version": "1.0.0"}


@router.post("/generate-report")
def generate_report(body: GenerateReportRequest):
    """Generate comprehensive test report."""
    if not body.test_run:
        return JSONResponse({"error": "test_run object required", "success": False}, status_code=400)

    try:
        test_run = _build_test_run(body.test_run)
        generator = _get_report_generator()
        report_paths = generator.generate_report(
            test_run,
            formats=body.formats,
            include_charts=body.include_charts,
        )
        return {
            "success": True,
            "run_id": test_run.run_id,
            "reports": report_paths,
            "summary": {
                "total_tests": test_run.total_tests,
                "passed": test_run.passed,
                "failed": test_run.failed,
                "skipped": test_run.skipped,
                "success_rate": f"{test_run.success_rate:.2f}%",
                "duration_seconds": test_run.duration_ms / 1000,
            },
        }
    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        return JSONResponse({"error": str(exc), "success": False}, status_code=500)


@router.post("/record-run")
def record_test_run(body: RecordRunRequest):
    """Record test run metrics for analytics."""
    if not body.run_id:
        return JSONResponse({"error": "run_id required", "success": False}, status_code=400)

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
    except Exception as exc:
        logger.error("Failed to record test run: %s", exc, exc_info=True)
        return JSONResponse({"error": str(exc), "success": False}, status_code=500)


@router.post("/record-failure")
def record_failed_test(body: RecordFailureRequest):
    """Record a failed test."""
    if not body.test_name or not body.run_id:
        return JSONResponse(
            {"error": "test_name and run_id required", "success": False}, status_code=400
        )

    try:
        analytics = _get_analytics_engine()
        analytics.record_failed_test(
            test_name=body.test_name,
            run_id=body.run_id,
            error_message=body.error_message,
            duration_ms=body.duration_ms,
        )
        return {"success": True, "test_name": body.test_name, "message": "Failed test recorded"}
    except Exception as exc:
        logger.error("Failed to record failure: %s", exc, exc_info=True)
        return JSONResponse({"error": str(exc), "success": False}, status_code=500)


@router.get("/analytics/trends")
def get_trends(metric_name: Optional[str] = None, hours: int = 24):
    """Get metric trends."""
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
    except Exception as exc:
        logger.error("Failed to get trends: %s", exc, exc_info=True)
        return JSONResponse({"error": str(exc), "success": False}, status_code=500)


@router.get("/analytics/risk-assessment")
def get_risk_assessment(hours: int = 24):
    """Get risk assessment for test suite."""
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
    except Exception as exc:
        logger.error("Failed to assess risk: %s", exc, exc_info=True)
        return JSONResponse({"error": str(exc), "success": False}, status_code=500)


@router.get("/analytics/predictions")
def get_predictions(days: int = 7):
    """Get failure predictions."""
    try:
        analytics = _get_analytics_engine()
        predictions = analytics.predict_failures(days)
        return {"success": True, "lookback_days": days, "predictions": predictions}
    except Exception as exc:
        logger.error("Failed to generate predictions: %s", exc, exc_info=True)
        return JSONResponse({"error": str(exc), "success": False}, status_code=500)


@router.get("/analytics/performance")
def get_performance_trends(hours: int = 24):
    """Get performance trends."""
    try:
        analytics = _get_analytics_engine()
        performance = analytics.get_performance_trends(hours)
        return {"success": True, "lookback_hours": hours, "performance": performance}
    except Exception as exc:
        logger.error("Failed to get performance trends: %s", exc, exc_info=True)
        return JSONResponse({"error": str(exc), "success": False}, status_code=500)


@router.get("/analytics/report")
def get_analytics_report(export: str = "json"):
    """Get comprehensive analytics report."""
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
    except Exception as exc:
        logger.error("Failed to generate analytics report: %s", exc, exc_info=True)
        return JSONResponse({"error": str(exc), "success": False}, status_code=500)
