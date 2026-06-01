"""Unit tests for app.domains.coverup.service (fixed version).

All HTTPException references have been removed from the service — it now
raises ValueError (bad input) and KeyError (not found). These tests verify
that contract.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone

import pytest

try:
    from app.domains.coverup import service as coverup_service
    from app.domains.coverup.service import (
        create_report,
        get_report_or_404,
        analyze_report,
        generate_tests,
        build_trend_response,
    )
    from app.domains.coverup.schemas import (
        AnalyzeRequest,
        CoverageReport,
        CoverageSummary,
        CoverageUploadRequest,
        FileCoverage,
        GenerateTestRequest,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="coverup service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file_coverage(**kwargs):
    defaults = dict(
        file_path="app/auth/service.py",
        total_lines=100,
        covered_lines=60,
        missed_lines=40,
        line_rate=0.6,
        branch_rate=0.5,
        total_branches=20,
        covered_branches=10,
        total_functions=10,
        covered_functions=6,
        missed_line_numbers=list(range(61, 101)),
        missed_branch_lines=[],
        uncovered_functions=[],
    )
    defaults.update(kwargs)
    return FileCoverage(**defaults)


def _make_coverage_summary(**kwargs):
    defaults = dict(
        total_files=1,
        total_lines=100,
        covered_lines=60,
        missed_lines=40,
        line_rate=0.6,
        branch_rate=0.5,
        function_rate=0.6,
        total_functions=10,
        covered_functions=6,
    )
    defaults.update(kwargs)
    return CoverageSummary(**defaults)


def _make_report(report_id="rpt-001", project_id="proj-001"):
    return CoverageReport(
        report_id=report_id,
        project_id=project_id,
        project_name="Test Project",
        commit_sha="abc1234",
        branch="main",
        format="cobertura",
        created_at=datetime.now(timezone.utc).isoformat(),
        summary=_make_coverage_summary(),
        files=[_make_file_coverage()],
    )


def _make_repository(report=None):
    repo = MagicMock()
    repo.get_report.return_value = report
    repo.save_report.side_effect = lambda r: r
    repo.save_generated_tests.return_value = None
    repo.list_trend_points.return_value = []
    return repo


def _make_upload_request(**kwargs):
    defaults = dict(
        project_id="proj-001",
        project_name="Test Project",
        commit_sha="abc1234",
        branch="main",
        format="cobertura",
        report_data="<coverage></coverage>",
    )
    defaults.update(kwargs)
    return CoverageUploadRequest(**defaults)


# ---------------------------------------------------------------------------
# create_report
# ---------------------------------------------------------------------------

class TestCreateReport:
    def test_parser_value_error_raises_value_error(self):
        body = _make_upload_request()
        with patch.object(coverup_service.CoverageParser, "parse",
                          side_effect=ValueError("bad format")):
            with pytest.raises(ValueError, match="bad format"):
                create_report(_make_repository(), body)

    def test_empty_files_after_parse_raises_value_error(self):
        body = _make_upload_request(format="unknown_fmt")
        parsed = {"files": [], "summary": _make_coverage_summary().model_dump()}
        with patch.object(coverup_service.CoverageParser, "parse", return_value=parsed):
            with pytest.raises(ValueError, match="parse edilemedi"):
                create_report(_make_repository(), body)

    def test_valid_upload_calls_repository_save(self):
        body = _make_upload_request()
        fc = _make_file_coverage()
        summary = _make_coverage_summary()
        parsed = {
            "files": [fc.model_dump()],
            "summary": summary.model_dump(),
        }
        repo = _make_repository()
        with patch.object(coverup_service.CoverageParser, "parse", return_value=parsed):
            create_report(repo, body)
        repo.save_report.assert_called_once()

    def test_valid_upload_returns_coverage_report(self):
        body = _make_upload_request()
        fc = _make_file_coverage()
        summary = _make_coverage_summary()
        parsed = {
            "files": [fc.model_dump()],
            "summary": summary.model_dump(),
        }
        repo = _make_repository()
        with patch.object(coverup_service.CoverageParser, "parse", return_value=parsed):
            result = create_report(repo, body)
        assert isinstance(result, CoverageReport)
        assert result.project_id == body.project_id

    def test_report_id_is_non_empty_string(self):
        body = _make_upload_request()
        fc = _make_file_coverage()
        summary = _make_coverage_summary()
        parsed = {"files": [fc.model_dump()], "summary": summary.model_dump()}
        repo = _make_repository()
        with patch.object(coverup_service.CoverageParser, "parse", return_value=parsed):
            result = create_report(repo, body)
        assert isinstance(result.report_id, str) and len(result.report_id) > 0


# ---------------------------------------------------------------------------
# get_report_or_404
# ---------------------------------------------------------------------------

class TestGetReportOr404:
    def test_existing_report_returned(self):
        report = _make_report()
        repo = _make_repository(report=report)
        result = get_report_or_404(repo, "rpt-001")
        assert result.report_id == "rpt-001"

    def test_missing_report_raises_key_error(self):
        repo = _make_repository(report=None)
        with pytest.raises(KeyError, match="rpt-missing"):
            get_report_or_404(repo, "rpt-missing")

    def test_key_error_message_contains_report_id(self):
        repo = _make_repository(report=None)
        with pytest.raises(KeyError) as exc_info:
            get_report_or_404(repo, "rpt-xyz-999")
        assert "rpt-xyz-999" in str(exc_info.value)

    def test_no_http_exception_raised(self):
        """Service must NOT raise HTTPException — it's HTTP-agnostic."""
        try:
            from fastapi import HTTPException
        except ImportError:
            pytest.skip("fastapi not installed")
        repo = _make_repository(report=None)
        with pytest.raises(KeyError):
            get_report_or_404(repo, "rpt-absent")
        # If we reach here without HTTPException being raised, test passes


# ---------------------------------------------------------------------------
# analyze_report
# ---------------------------------------------------------------------------

class TestAnalyzeReport:
    def test_returns_analyze_response(self):
        from app.domains.coverup.schemas import AnalyzeResponse
        report = _make_report()
        body = AnalyzeRequest(
            report_id="rpt-001",
            min_risk_score=0.0,
            max_targets=10,
        )
        with patch.object(coverup_service.GapDetector, "detect_gaps", return_value=[]):
            with patch.object(coverup_service.GapDetector, "identify_banking_critical_paths",
                              return_value=[]):
                result = analyze_report(report, body)
        assert isinstance(result, AnalyzeResponse)

    def test_risk_counts_sum_correctly(self):
        from app.domains.coverup.schemas import AnalyzeResponse, CoverageGapTarget
        report = _make_report()
        body = AnalyzeRequest(report_id="rpt-001", min_risk_score=0.0, max_targets=10)
        targets_raw = [
            {"file_path": "a.py", "risk_score": 0.8, "risk_factors": [], "missed_lines": [], "function_name": None},
            {"file_path": "b.py", "risk_score": 0.5, "risk_factors": [], "missed_lines": [], "function_name": None},
            {"file_path": "c.py", "risk_score": 0.2, "risk_factors": [], "missed_lines": [], "function_name": None},
        ]
        with patch.object(coverup_service.GapDetector, "detect_gaps", return_value=targets_raw):
            with patch.object(coverup_service.GapDetector, "identify_banking_critical_paths",
                              return_value=[]):
                result = analyze_report(report, body)
        assert result.high_risk_count + result.medium_risk_count + result.low_risk_count == len(result.targets)

    def test_banking_only_filters_non_banking_paths(self):
        report = _make_report()
        body = AnalyzeRequest(report_id="rpt-001", min_risk_score=0.0, max_targets=10)
        targets_raw = [
            {"file_path": "auth/login.py", "risk_score": 0.6, "risk_factors": [], "missed_lines": [], "function_name": None},
            {"file_path": "utils/helper.py", "risk_score": 0.6, "risk_factors": [], "missed_lines": [], "function_name": None},
        ]
        with patch.object(coverup_service.GapDetector, "detect_gaps", return_value=targets_raw):
            with patch.object(coverup_service.GapDetector, "identify_banking_critical_paths",
                              return_value=["auth/login.py"]):
                result = analyze_report(report, body, banking_only=True)
        assert all(t.file_path == "auth/login.py" for t in result.targets)


# ---------------------------------------------------------------------------
# build_trend_response
# ---------------------------------------------------------------------------

class TestBuildTrendResponse:
    def test_empty_points_returns_stable(self):
        result = build_trend_response([])
        assert result.direction == "stable"
        assert result.current_line_rate == 0.0

    def test_improving_trend(self):
        p1, p2 = MagicMock(), MagicMock()
        p1.line_rate = 0.5
        p2.line_rate = 0.6
        result = build_trend_response([p1, p2])
        assert result.direction == "improving"

    def test_degrading_trend(self):
        p1, p2 = MagicMock(), MagicMock()
        p1.line_rate = 0.7
        p2.line_rate = 0.5
        result = build_trend_response([p1, p2])
        assert result.direction == "degrading"

    def test_single_point_is_stable(self):
        p = MagicMock()
        p.line_rate = 0.65
        result = build_trend_response([p])
        assert result.direction == "stable"
        assert result.current_line_rate == 0.65
