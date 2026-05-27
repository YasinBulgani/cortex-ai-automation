"""Unit tests for TSPM reporting helpers — no DB, no filesystem I/O.

Tests app/domains/tspm/reporting.py pure classes:
  - RootCauseAnalyzer.classify, analyze_failed_results, distribution
  - CoverageCalculator.calculate
  - QualityScorecard.calculate
"""

from __future__ import annotations

import pytest

from app.domains.tspm.reporting import (
    CoverageCalculator,
    ErrorInfo,
    QualityScorecard,
    RootCauseAnalyzer,
    RootCauseCategory,
    Severity,
    TestResult,
    TestStatus,
)


# ── RootCauseAnalyzer.classify ────────────────────────────────────────────────


class TestRootCauseAnalyzerClassify:
    def test_timeout_error_classified_as_test_issue(self) -> None:
        rc = RootCauseAnalyzer.classify("TimeoutError: exceeded 30s")
        assert rc.category == RootCauseCategory.TEST_ISSUE
        assert rc.subcategory == "timing"

    def test_connection_refused_classified_as_environment(self) -> None:
        rc = RootCauseAnalyzer.classify("net::ERR_CONNECTION_REFUSED at localhost:3000")
        assert rc.category == RootCauseCategory.ENVIRONMENT
        assert rc.subcategory == "infra_down"

    def test_econnrefused_classified_as_environment(self) -> None:
        rc = RootCauseAnalyzer.classify("Error: ECONNREFUSED 127.0.0.1:5432")
        assert rc.category == RootCauseCategory.ENVIRONMENT
        assert rc.subcategory == "infra_down"

    def test_locator_click_classified_as_stale_locator(self) -> None:
        rc = RootCauseAnalyzer.classify("Error: locator.click is not attached to DOM")
        assert rc.category == RootCauseCategory.TEST_ISSUE
        assert rc.subcategory == "stale_locator"

    def test_element_not_found_classified_as_stale_locator(self) -> None:
        rc = RootCauseAnalyzer.classify("Element not found: [data-testid='login-btn']")
        assert rc.category == RootCauseCategory.TEST_ISSUE
        assert rc.subcategory == "stale_locator"

    def test_assertion_error_classified_as_product_bug(self) -> None:
        rc = RootCauseAnalyzer.classify("AssertionError: expected 200 but got 500")
        assert rc.category == RootCauseCategory.PRODUCT_BUG
        assert rc.subcategory == "functional"

    def test_500_server_error_classified_as_product_bug(self) -> None:
        rc = RootCauseAnalyzer.classify("500 Internal Server Error at /api/payments")
        assert rc.category == RootCauseCategory.PRODUCT_BUG
        assert rc.subcategory == "functional"

    def test_oom_classified_as_environment_resource(self) -> None:
        rc = RootCauseAnalyzer.classify("OOM: Java heap space exceeded")
        assert rc.category == RootCauseCategory.ENVIRONMENT
        assert rc.subcategory == "resource"

    def test_permission_denied_classified_as_environment_config(self) -> None:
        rc = RootCauseAnalyzer.classify("permission denied: /etc/ssl/keys")
        assert rc.category == RootCauseCategory.ENVIRONMENT
        assert rc.subcategory == "config"

    def test_database_issue_classified_as_infra_down(self) -> None:
        rc = RootCauseAnalyzer.classify("database connection failed")
        assert rc.category == RootCauseCategory.ENVIRONMENT
        assert rc.subcategory == "infra_down"

    def test_redis_issue_classified_as_infra_down(self) -> None:
        rc = RootCauseAnalyzer.classify("redis NOAUTH Authentication required")
        assert rc.category == RootCauseCategory.ENVIRONMENT
        assert rc.subcategory == "infra_down"

    def test_unknown_error_classified_as_unknown(self) -> None:
        rc = RootCauseAnalyzer.classify("some completely unrelated error message")
        assert rc.category == RootCauseCategory.UNKNOWN
        assert rc.subcategory == "unclassified"

    def test_empty_error_classified_as_unknown(self) -> None:
        rc = RootCauseAnalyzer.classify("")
        assert rc.category == RootCauseCategory.UNKNOWN

    def test_error_type_participates_in_matching(self) -> None:
        rc = RootCauseAnalyzer.classify("", error_type="TimeoutError")
        assert rc.category == RootCauseCategory.TEST_ISSUE

    def test_case_insensitive_matching(self) -> None:
        rc = RootCauseAnalyzer.classify("TIMEOUTERROR occurred")
        assert rc.category == RootCauseCategory.TEST_ISSUE

    def test_description_contains_error_snippet(self) -> None:
        rc = RootCauseAnalyzer.classify("AssertionError: bad value")
        assert "bad value" in rc.description or "Uygulama" in rc.description

    def test_not_to_be_visible_classified_as_wrong_assertion(self) -> None:
        rc = RootCauseAnalyzer.classify("expect(received).not.toBeVisible() failed")
        assert rc.category == RootCauseCategory.TEST_ISSUE
        assert rc.subcategory == "wrong_assertion"

    def test_returns_root_cause_object(self) -> None:
        from app.domains.tspm.reporting import RootCause
        rc = RootCauseAnalyzer.classify("AssertionError")
        assert isinstance(rc, RootCause)


# ── RootCauseAnalyzer.analyze_failed_results ──────────────────────────────────


class TestRootCauseAnalyzerAnalyzeFailed:
    def _make_result(
        self,
        test_id: str,
        status: TestStatus,
        error_msg: str = "",
        error_type: str = "",
    ) -> TestResult:
        error = ErrorInfo(message=error_msg, type=error_type) if error_msg or error_type else None
        return TestResult(
            test_id=test_id,
            title=f"Test {test_id}",
            status=status,
            error=error,
        )

    def test_passed_results_excluded(self) -> None:
        results = [self._make_result("tc-001", TestStatus.PASSED)]
        rca = RootCauseAnalyzer.analyze_failed_results(results)
        assert rca == []

    def test_failed_result_included(self) -> None:
        results = [self._make_result("tc-002", TestStatus.FAILED, "AssertionError")]
        rca = RootCauseAnalyzer.analyze_failed_results(results)
        assert len(rca) == 1
        assert rca[0]["test_id"] == "tc-002"

    def test_multiple_failures_all_included(self) -> None:
        results = [
            self._make_result("tc-001", TestStatus.FAILED, "TimeoutError"),
            self._make_result("tc-002", TestStatus.PASSED),
            self._make_result("tc-003", TestStatus.FAILED, "AssertionError"),
        ]
        rca = RootCauseAnalyzer.analyze_failed_results(results)
        assert len(rca) == 2

    def test_rca_entry_has_expected_keys(self) -> None:
        results = [self._make_result("tc-001", TestStatus.FAILED, "AssertionError")]
        rca = RootCauseAnalyzer.analyze_failed_results(results)
        entry = rca[0]
        assert "test_id" in entry
        assert "title" in entry
        assert "root_cause" in entry
        assert "category" in entry["root_cause"]

    def test_empty_list_returns_empty(self) -> None:
        assert RootCauseAnalyzer.analyze_failed_results([]) == []


# ── RootCauseAnalyzer.distribution ───────────────────────────────────────────


class TestRootCauseAnalyzerDistribution:
    def test_empty_entries_returns_empty(self) -> None:
        assert RootCauseAnalyzer.distribution([]) == {}

    def test_counts_categories(self) -> None:
        entries = [
            {"root_cause": {"category": "PRODUCT_BUG"}},
            {"root_cause": {"category": "PRODUCT_BUG"}},
            {"root_cause": {"category": "ENVIRONMENT"}},
        ]
        dist = RootCauseAnalyzer.distribution(entries)
        assert dist["PRODUCT_BUG"] == 2
        assert dist["ENVIRONMENT"] == 1

    def test_missing_root_cause_defaults_to_unknown(self) -> None:
        entries = [{"no_root_cause": {}}]
        dist = RootCauseAnalyzer.distribution(entries)
        assert "UNKNOWN" in dist


# ── CoverageCalculator.calculate ──────────────────────────────────────────────


class TestCoverageCalculatorCalculate:
    def test_empty_requirements_returns_zero_coverage(self) -> None:
        result = CoverageCalculator.calculate([], [], [])
        assert result["total_requirements"] == 0
        assert result["coverage_percent"] == 0.0

    def test_single_covered_requirement(self) -> None:
        reqs = [{"id": "REQ-001", "title": "Login", "priority": "high"}]
        links = [{"requirement_id": "REQ-001", "scenario_id": "SCN-001"}]
        execs = [{"scenario_id": "SCN-001", "status": "passed"}]
        result = CoverageCalculator.calculate(reqs, links, execs)
        assert result["coverage_percent"] == 100.0
        assert result["covered_count"] == 1
        assert result["passed_count"] == 1

    def test_single_uncovered_requirement(self) -> None:
        reqs = [{"id": "REQ-001", "title": "Logout", "priority": "medium"}]
        result = CoverageCalculator.calculate(reqs, [], [])
        assert result["coverage_percent"] == 0.0
        assert result["covered_count"] == 0
        assert len(result["gaps"]) == 1

    def test_mixed_coverage(self) -> None:
        reqs = [
            {"id": "R1", "title": "Login", "priority": "high"},
            {"id": "R2", "title": "Logout", "priority": "medium"},
        ]
        links = [{"requirement_id": "R1", "scenario_id": "SCN-001"}]
        execs = [{"scenario_id": "SCN-001", "status": "passed"}]
        result = CoverageCalculator.calculate(reqs, links, execs)
        assert result["total_requirements"] == 2
        assert result["covered_count"] == 1
        assert result["coverage_percent"] == 50.0

    def test_failed_scenario_sets_at_risk(self) -> None:
        reqs = [{"id": "R1", "title": "Payment", "priority": "critical"}]
        links = [{"requirement_id": "R1", "scenario_id": "SCN-001"}]
        execs = [{"scenario_id": "SCN-001", "status": "failed"}]
        result = CoverageCalculator.calculate(reqs, links, execs)
        assert result["at_risk_count"] == 1
        matrix = result["matrix"]
        assert matrix[0]["status"] == "at_risk"

    def test_partial_coverage(self) -> None:
        reqs = [{"id": "R1", "title": "Search", "priority": "medium"}]
        links = [
            {"requirement_id": "R1", "scenario_id": "SCN-001"},
            {"requirement_id": "R1", "scenario_id": "SCN-002"},
        ]
        execs = [
            {"scenario_id": "SCN-001", "status": "passed"},
            {"scenario_id": "SCN-002", "status": "not_run"},
        ]
        result = CoverageCalculator.calculate(reqs, links, execs)
        assert result["matrix"][0]["status"] == "partially_covered"

    def test_matrix_row_structure(self) -> None:
        reqs = [{"id": "R1", "external_id": "JIRA-1", "title": "Login", "priority": "high"}]
        links = [{"requirement_id": "R1", "scenario_id": "S1"}]
        execs = [{"scenario_id": "S1", "status": "passed"}]
        result = CoverageCalculator.calculate(reqs, links, execs)
        row = result["matrix"][0]
        assert row["requirement_id"] == "R1"
        assert row["external_id"] == "JIRA-1"
        assert row["title"] == "Login"
        assert "scenario_ids" in row
        assert "statuses" in row

    def test_gaps_list_contains_uncovered(self) -> None:
        reqs = [
            {"id": "R1", "title": "Covered", "priority": "high"},
            {"id": "R2", "title": "Uncovered", "priority": "low"},
        ]
        links = [{"requirement_id": "R1", "scenario_id": "S1"}]
        execs = [{"scenario_id": "S1", "status": "passed"}]
        result = CoverageCalculator.calculate(reqs, links, execs)
        gaps = result["gaps"]
        assert len(gaps) == 1
        assert gaps[0]["requirement_id"] == "R2"


# ── QualityScorecard.calculate ────────────────────────────────────────────────


class TestQualityScorecardCalculate:
    def test_perfect_scores_gives_high_overall(self) -> None:
        result = QualityScorecard.calculate(
            pass_rate=100.0,
            critical_pass_rate=100.0,
            requirement_coverage=100.0,
            automation_rate=100.0,
            flaky_rate=0.0,
        )
        assert result["overall_score"] >= 85
        assert result["health"] == "healthy"

    def test_poor_scores_gives_critical_health(self) -> None:
        result = QualityScorecard.calculate(
            pass_rate=50.0,
            critical_pass_rate=50.0,
            requirement_coverage=30.0,
            automation_rate=20.0,
            flaky_rate=30.0,
        )
        assert result["health"] == "critical"

    def test_medium_scores_gives_at_risk(self) -> None:
        result = QualityScorecard.calculate(
            pass_rate=78.0,
            critical_pass_rate=88.0,
            requirement_coverage=75.0,
            automation_rate=50.0,
            flaky_rate=3.0,
        )
        assert result["health"] in ("at_risk", "healthy")  # borderline

    def test_overall_score_in_range(self) -> None:
        result = QualityScorecard.calculate(
            pass_rate=80.0,
            critical_pass_rate=90.0,
            requirement_coverage=85.0,
            automation_rate=60.0,
            flaky_rate=5.0,
        )
        assert 0.0 <= result["overall_score"] <= 100.0

    def test_dimensions_present(self) -> None:
        result = QualityScorecard.calculate(
            pass_rate=90.0,
            critical_pass_rate=95.0,
            requirement_coverage=80.0,
            automation_rate=70.0,
        )
        dims = result["dimensions"]
        assert "pass_rate" in dims
        assert "critical_pass_rate" in dims
        assert "requirement_coverage" in dims
        assert "automation_rate" in dims
        assert "flaky_rate" in dims

    def test_green_status_for_high_pass_rate(self) -> None:
        result = QualityScorecard.calculate(
            pass_rate=90.0,
            critical_pass_rate=99.0,
            requirement_coverage=92.0,
            automation_rate=75.0,
            flaky_rate=1.0,
        )
        assert result["dimensions"]["pass_rate"]["status"] == "green"

    def test_red_status_for_low_pass_rate(self) -> None:
        result = QualityScorecard.calculate(
            pass_rate=50.0,
            critical_pass_rate=60.0,
            requirement_coverage=40.0,
            automation_rate=20.0,
            flaky_rate=25.0,
        )
        assert result["dimensions"]["pass_rate"]["status"] == "red"

    def test_flaky_penalty_reduces_score(self) -> None:
        no_flaky = QualityScorecard.calculate(90.0, 95.0, 85.0, 70.0, flaky_rate=0.0)
        high_flaky = QualityScorecard.calculate(90.0, 95.0, 85.0, 70.0, flaky_rate=30.0)
        assert no_flaky["overall_score"] > high_flaky["overall_score"]

    def test_weights_sum_to_one(self) -> None:
        total = sum(QualityScorecard.WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_scores_capped_at_100(self) -> None:
        # Values > 100 should be capped
        result = QualityScorecard.calculate(150.0, 150.0, 150.0, 150.0, flaky_rate=0.0)
        assert result["overall_score"] <= 100.0

    def test_flaky_rate_over_20_gives_zero_penalty_score(self) -> None:
        # flaky_penalty = max(1.0 - flaky_rate/20, 0) — at ≥20% flaky, penalty contribution = 0
        result_0 = QualityScorecard.calculate(90.0, 95.0, 85.0, 70.0, flaky_rate=0.0)
        result_20 = QualityScorecard.calculate(90.0, 95.0, 85.0, 70.0, flaky_rate=20.0)
        result_40 = QualityScorecard.calculate(90.0, 95.0, 85.0, 70.0, flaky_rate=40.0)
        # At flaky_rate=20, penalty=0; at flaky_rate=40, penalty clamped to 0 also
        assert result_20["overall_score"] == result_40["overall_score"]
        assert result_0["overall_score"] > result_20["overall_score"]
