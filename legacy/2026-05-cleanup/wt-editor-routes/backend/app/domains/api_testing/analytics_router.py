"""Analytics, healing and security endpoints for API testing domain."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.domains.api_testing.models import ApiEndpoint, ApiSpec, ApiTestCase, HealingLog
from app.domains.api_testing.schemas import (
    AssertionStatsResponse,
    AssertionSuggestion,
    AssertionSuggestionsResponse,
    BulkAssertionRequest,
    BulkAssertionSuggestItem,
    BulkAssertionSummary,
    ComplianceStatus,
    CoverageAnalysisResponse,
    CoverageGapItem,
    CoverageGapSuggestionItem,
    CoverageGapSuggestionsResponse,
    CoverageSummary,
    CoverageSummaryBrief,
    EndpointScanResult,
    GenerateSecurityTestsRequest,
    GenerateSecurityTestsResponse,
    HealAndRetryResponse,
    HealingCategoryStats,
    HealingDetailItem,
    HealingLogItem,
    HealingLogResponse,
    HealingStatsResponse,
    HealingTopTest,
    OptimalSuiteRequest,
    OptimalSuiteResponse,
    PrioritizationResponse,
    PrioritizationStatsResponse,
    PrioritizedTestItem,
    PriorityBreakdown,
    RiskDistribution,
    RiskLevelStats,
    SecurityDashboardResponse,
    SecurityFinding,
    SecurityTestScanSummary,
    SecurityTestSuggestion,
    SpecScanResponse,
    SpecScanResult,
    TestCaseOut,
    TestTypeStats,
    VulnerableEndpointItem,
)
from app.infra.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/coverage-analysis", response_model=CoverageAnalysisResponse)
def get_coverage_analysis(
    project_id: str,
    spec_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Return coverage summary + gaps for a project."""
    from app.domains.api_testing.coverage_analyzer import analyze_coverage

    _ = user
    result = analyze_coverage(db, project_id, spec_id=spec_id)
    return CoverageAnalysisResponse(
        summary=CoverageSummary(**result["summary"]),
        gaps=[CoverageGapItem(**g) for g in result["gaps"]],
        by_risk_level={k: RiskLevelStats(**v) for k, v in result["by_risk_level"].items()},
        by_test_type={k: TestTypeStats(**v) for k, v in result["by_test_type"].items()},
    )


@router.get("/coverage-gaps", response_model=List[CoverageGapItem])
def get_coverage_gaps(
    project_id: str,
    spec_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="Filter by gap_severity: critical, high, medium, low"),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Return coverage gaps sorted by severity."""
    from app.domains.api_testing.coverage_analyzer import analyze_coverage

    _ = user
    result = analyze_coverage(db, project_id, spec_id=spec_id)
    gaps = result["gaps"]
    if severity:
        gaps = [g for g in gaps if g["gap_severity"] == severity.lower()]
    return [CoverageGapItem(**g) for g in gaps]


@router.post("/coverage-gaps/suggest", response_model=CoverageGapSuggestionsResponse)
def suggest_coverage_gaps(
    project_id: str,
    max_gaps: int = Query(5, ge=1, le=50, description="Max number of gap suggestions to return"),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Suggest tests for top coverage gaps."""
    from app.domains.api_testing.coverage_analyzer import suggest_tests_for_gaps

    _ = user
    suggestions = suggest_tests_for_gaps(db, project_id, max_gaps=max_gaps)
    return CoverageGapSuggestionsResponse(
        suggestions=[CoverageGapSuggestionItem(**s) for s in suggestions],
    )


@router.get("/prioritize", response_model=PrioritizationResponse)
def get_prioritized_tests(
    project_id: str,
    max_tests: Optional[int] = Query(None, ge=1, description="Max number of tests to return"),
    changed_paths: Optional[str] = Query(None, description="Comma-separated changed paths"),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Return prioritized tests for change-impact and risk."""
    from app.domains.api_testing.test_prioritizer import prioritize_tests

    _ = user
    paths = [p.strip() for p in changed_paths.split(",") if p.strip()] if changed_paths else None
    try:
        items = prioritize_tests(
            db,
            project_id,
            changed_paths=paths,
            max_tests=max_tests,
        )
    except Exception:
        logger.exception("Prioritization failed for project %s", project_id)
        items = []

    return PrioritizationResponse(
        items=[
            PrioritizedTestItem(
                test_case_id=i["test_case_id"],
                title=i["title"],
                test_type=i["test_type"],
                priority_score=i["priority_score"],
                breakdown=PriorityBreakdown(**i["breakdown"]),
                endpoint_method=i["endpoint_method"],
                endpoint_path=i["endpoint_path"],
                risk_level=i["risk_level"],
                last_run_status=i["last_run_status"],
                estimated_duration_ms=i["estimated_duration_ms"],
            )
            for i in items
        ],
        total_count=len(items),
    )


@router.get("/prioritize/stats", response_model=PrioritizationStatsResponse)
def get_prioritization_stats_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Return summary statistics for prioritization."""
    from app.domains.api_testing.test_prioritizer import get_prioritization_stats

    _ = user
    try:
        stats = get_prioritization_stats(db, project_id)
    except Exception:
        logger.exception("Prioritization stats failed for project %s", project_id)
        stats = {
            "total_tests": 0,
            "quarantined_skipped": 0,
            "high_priority_count": 0,
            "medium_priority_count": 0,
            "low_priority_count": 0,
            "avg_score": 0.0,
            "risk_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "estimated_total_duration_ms": 0.0,
        }

    return PrioritizationStatsResponse(
        total_tests=stats["total_tests"],
        quarantined_skipped=stats["quarantined_skipped"],
        high_priority_count=stats["high_priority_count"],
        medium_priority_count=stats["medium_priority_count"],
        low_priority_count=stats["low_priority_count"],
        avg_score=stats["avg_score"],
        risk_distribution=RiskDistribution(**stats["risk_distribution"]),
        estimated_total_duration_ms=stats["estimated_total_duration_ms"],
    )


@router.post("/prioritize/optimal-suite", response_model=OptimalSuiteResponse)
def get_optimal_suite(
    project_id: str,
    body: OptimalSuiteRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Return the best test subset under a time budget."""
    from app.domains.api_testing.test_prioritizer import suggest_optimal_suite

    _ = user
    try:
        result = suggest_optimal_suite(
            db,
            project_id,
            time_budget_ms=body.time_budget_ms,
            changed_paths=body.changed_paths,
        )
    except Exception:
        logger.exception("Optimal suite selection failed for project %s", project_id)
        result = {
            "selected_test_ids": [],
            "selected_count": 0,
            "total_duration_ms": 0.0,
            "time_budget_ms": body.time_budget_ms,
            "coverage_summary": {
                "by_risk_level": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "by_test_type": {},
            },
        }

    return OptimalSuiteResponse(
        selected_test_ids=result["selected_test_ids"],
        selected_count=result["selected_count"],
        total_duration_ms=result["total_duration_ms"],
        time_budget_ms=result["time_budget_ms"],
        coverage_summary=CoverageSummaryBrief(**result["coverage_summary"]),
    )


@router.post("/healing/{run_id}/heal", response_model=HealAndRetryResponse)
def trigger_healing(
    project_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Trigger self-healing retries for failed tests in a run."""
    from app.domains.api_testing.self_healer import heal_and_retry

    _ = user
    result = heal_and_retry(db, project_id, run_id)
    return HealAndRetryResponse(
        run_id=result["run_id"],
        total_failures=result["total_failures"],
        healed=result["healed"],
        still_failing=result["still_failing"],
        quarantined=result["quarantined"],
        skipped=result["skipped"],
        healing_details=[HealingDetailItem(**d) for d in result["healing_details"]],
        total_healing_time_ms=result["total_healing_time_ms"],
    )


@router.get("/healing/stats", response_model=HealingStatsResponse)
def get_healing_stats_endpoint(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Get aggregated healing metrics."""
    from app.domains.api_testing.self_healer import get_healing_stats

    _ = user
    result = get_healing_stats(db, project_id, days=days)
    return HealingStatsResponse(
        total_healing_attempts=result["total_healing_attempts"],
        success_rate=result["success_rate"],
        by_category={k: HealingCategoryStats(**v) for k, v in result["by_category"].items()},
        avg_retries_needed=result["avg_retries_needed"],
        avg_healing_time_ms=result["avg_healing_time_ms"],
        top_healed_tests=[HealingTopTest(**t) for t in result["top_healed_tests"]],
        saved_ci_time_ms=result["saved_ci_time_ms"],
    )


@router.get("/healing/{run_id}/log", response_model=HealingLogResponse)
def get_healing_log(
    project_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Get healing log entries for a specific run."""
    _ = user
    logs = (
        db.query(HealingLog)
        .filter(
            HealingLog.project_id == project_id,
            HealingLog.run_id == run_id,
        )
        .order_by(HealingLog.created_at)
        .all()
    )
    return HealingLogResponse(
        run_id=run_id,
        items=[HealingLogItem.model_validate(log) for log in logs],
        total_count=len(logs),
    )


@router.get("/assertions/stats", response_model=AssertionStatsResponse)
def get_assertion_stats_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Return assertion statistics for the project."""
    from app.domains.api_testing.assertion_suggester import get_assertion_stats

    _ = user
    result = get_assertion_stats(db, project_id)
    return AssertionStatsResponse(
        total_tests=result["total_tests"],
        total_assertions=result["total_assertions"],
        avg_assertions_per_test=result["avg_assertions_per_test"],
        tests_with_no_assertions=result["tests_with_no_assertions"],
        tests_below_threshold=result["tests_below_threshold"],
        assertion_type_distribution=result["assertion_type_distribution"],
        suggestion_potential=result["suggestion_potential"],
    )


@router.post("/assertions/bulk-suggest", response_model=BulkAssertionSummary)
def bulk_suggest_assertions_endpoint(
    project_id: str,
    body: BulkAssertionRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Bulk assertion analysis for selected tests."""
    from app.domains.api_testing.assertion_suggester import bulk_suggest

    _ = user
    result = bulk_suggest(
        db,
        project_id,
        test_case_ids=body.test_case_ids,
        test_type=body.test_type,
    )
    return BulkAssertionSummary(
        total_test_cases=result["total_test_cases"],
        total_suggestions=result["total_suggestions"],
        avg_suggestions_per_test=result["avg_suggestions_per_test"],
        results=[
            BulkAssertionSuggestItem(
                test_case_id=r["test_case_id"],
                title=r["title"],
                test_type=r["test_type"],
                current_assertions=r["current_assertions"],
                suggestion_count=r["suggestion_count"],
                suggestions=[AssertionSuggestion(**s) for s in r["suggestions"]],
            )
            for r in result["results"]
        ],
    )


@router.get("/assertions/{test_case_id}/suggest", response_model=AssertionSuggestionsResponse)
def suggest_assertions_endpoint(
    project_id: str,
    test_case_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Suggest additional assertions for one test case."""
    from app.domains.api_testing.assertion_suggester import suggest_assertions

    _ = user
    tc = db.query(ApiTestCase).filter(
        ApiTestCase.id == test_case_id,
        ApiTestCase.project_id == project_id,
    ).first()
    if not tc:
        raise HTTPException(404, "Test case bulunamadi")

    result = suggest_assertions(db, project_id, test_case_id)
    return AssertionSuggestionsResponse(
        test_case_id=result["test_case_id"],
        current_assertion_count=result["current_assertion_count"],
        suggestions=[AssertionSuggestion(**s) for s in result["suggestions"]],
        coverage_improvement=result["coverage_improvement"],
    )


@router.get("/security/dashboard", response_model=SecurityDashboardResponse)
def security_dashboard_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Security dashboard overview for the project."""
    from app.domains.api_testing.security_scanner import get_security_dashboard

    _ = user
    result = get_security_dashboard(db, project_id)
    compliance = {}
    for reg_key, reg_data in result.get("compliance_status", {}).items():
        compliance[reg_key] = ComplianceStatus(
            passed=reg_data.get("passed", 0),
            failed=reg_data.get("failed", 0),
            checks=reg_data.get("checks", []),
        )

    return SecurityDashboardResponse(
        total_endpoints=result.get("total_endpoints", 0),
        scanned_endpoints=result.get("scanned_endpoints", 0),
        findings_by_severity=result.get("findings_by_severity", {}),
        findings_by_owasp=result.get("findings_by_owasp", {}),
        avg_security_score=result.get("avg_security_score", 0.0),
        top_vulnerable_endpoints=[VulnerableEndpointItem(**ep) for ep in result.get("top_vulnerable_endpoints", [])],
        compliance_status=compliance,
        recommendations=result.get("recommendations", []),
    )


@router.post("/security/scan/endpoint/{endpoint_id}", response_model=EndpointScanResult)
def scan_endpoint_endpoint(
    project_id: str,
    endpoint_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Scan a single endpoint for OWASP API vulnerabilities."""
    from app.domains.api_testing.security_scanner import scan_endpoint

    _ = user
    ep = db.query(ApiEndpoint).filter(ApiEndpoint.id == endpoint_id).first()
    if not ep:
        raise HTTPException(404, "Endpoint bulunamadi")

    spec = db.query(ApiSpec).filter(
        ApiSpec.id == ep.spec_id,
        ApiSpec.project_id == project_id,
    ).first()
    if not spec:
        raise HTTPException(404, "Endpoint bu projeye ait degil")

    result = scan_endpoint(db, endpoint_id)
    return EndpointScanResult(
        endpoint_id=result.get("endpoint_id", endpoint_id),
        method=result.get("method", ""),
        path=result.get("path", ""),
        risk_level=result.get("risk_level", "unknown"),
        findings=[SecurityFinding(**f) for f in result.get("findings", [])],
        security_score=result.get("security_score", 0.0),
        test_suggestions=[SecurityTestSuggestion(**s) for s in result.get("test_suggestions", [])],
        error=result.get("error"),
    )


@router.post("/security/scan/spec/{spec_id}", response_model=SpecScanResponse)
def scan_spec_endpoint(
    project_id: str,
    spec_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Scan all endpoints in a spec and aggregate findings."""
    from app.domains.api_testing.security_scanner import scan_spec

    _ = user
    spec = db.query(ApiSpec).filter(
        ApiSpec.id == spec_id,
        ApiSpec.project_id == project_id,
    ).first()
    if not spec:
        raise HTTPException(404, "Spec bulunamadi")

    result = scan_spec(db, project_id, spec_id)
    endpoint_results = [
        SpecScanResult(
            endpoint_id=er.get("endpoint_id", ""),
            method=er.get("method", ""),
            path=er.get("path", ""),
            risk_level=er.get("risk_level", "unknown"),
            findings=[SecurityFinding(**f) for f in er.get("findings", [])],
            security_score=er.get("security_score", 0.0),
            test_suggestions=[SecurityTestSuggestion(**s) for s in er.get("test_suggestions", [])],
        )
        for er in result.get("endpoint_results", [])
    ]
    return SpecScanResponse(
        spec_id=result.get("spec_id", spec_id),
        spec_name=result.get("spec_name", ""),
        total_endpoints=result.get("total_endpoints", 0),
        scanned_endpoints=result.get("scanned_endpoints", 0),
        findings_by_severity=result.get("findings_by_severity", {}),
        findings_by_owasp=result.get("findings_by_owasp", {}),
        avg_security_score=result.get("avg_security_score", 0.0),
        endpoint_results=endpoint_results,
        error=result.get("error"),
    )


@router.post("/security/generate-tests", response_model=GenerateSecurityTestsResponse)
def generate_security_tests_endpoint(
    project_id: str,
    body: GenerateSecurityTestsRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Generate security tests from scanner findings."""
    from app.domains.api_testing.security_scanner import generate_security_tests

    _ = user
    ep = db.query(ApiEndpoint).filter(ApiEndpoint.id == body.endpoint_id).first()
    if not ep:
        raise HTTPException(404, "Endpoint bulunamadi")

    spec = db.query(ApiSpec).filter(
        ApiSpec.id == ep.spec_id,
        ApiSpec.project_id == project_id,
    ).first()
    if not spec:
        raise HTTPException(404, "Endpoint bu projeye ait degil")

    result = generate_security_tests(
        db,
        project_id,
        body.endpoint_id,
        owasp_categories=body.owasp_categories,
    )

    scan_summary = None
    raw_summary = result.get("scan_summary")
    if raw_summary:
        scan_summary = SecurityTestScanSummary(
            total_findings=raw_summary.get("total_findings", 0),
            security_score=raw_summary.get("security_score", 0.0),
            risk_level=raw_summary.get("risk_level", "unknown"),
        )

    return GenerateSecurityTestsResponse(
        endpoint_id=result.get("endpoint_id", body.endpoint_id),
        generated_count=result.get("generated_count", 0),
        test_cases=[TestCaseOut.model_validate(tc) for tc in result.get("test_cases", [])],
        scan_summary=scan_summary,
        error=result.get("error"),
    )
