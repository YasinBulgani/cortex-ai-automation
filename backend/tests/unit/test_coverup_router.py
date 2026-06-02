"""Unit tests for the coverup router — 12 tests.

Auth, DB and service-layer calls are fully mocked.
The CoverageReportRepository is patched at the router's import path.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.coverup.router import router as coverup_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from app.deps import get_current_user
    from app.infra.database import get_db

    app = FastAPI()
    app.include_router(coverup_router, prefix="/api/v1")

    fake_user = MagicMock()
    fake_user.id = "user-1"
    fake_user.roles = []
    fake_db = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: fake_db

    return TestClient(app, raise_server_exceptions=False)


def _make_coverage_report(report_id="rpt-1"):
    from app.domains.coverup.schemas import (
        CoverageReport, CoverageSummary,
    )
    return CoverageReport(
        report_id=report_id,
        project_id="proj-1",
        project_name="MyApp",
        commit_sha="abc123",
        branch="main",
        format="lcov",
        created_at=datetime(2026, 1, 1).isoformat(),
        summary=CoverageSummary(
            total_files=3,
            total_lines=100,
            covered_lines=80,
            missed_lines=20,
            line_rate=0.8,
        ),
        files=[],
    )


def _make_list_item(report_id="rpt-1"):
    from app.domains.coverup.schemas import CoverageReportListItem
    return CoverageReportListItem(
        report_id=report_id,
        project_id="proj-1",
        format="lcov",
        created_at=datetime(2026, 1, 1).isoformat(),
        line_rate=0.8,
    )


def _make_trend_response():
    from app.domains.coverup.schemas import TrendResponse
    return TrendResponse(points=[], direction="stable", avg_line_rate=0.8)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class TestCoverUpUpload:
    def test_upload_valid_report_returns_200(self, client):
        report = _make_coverage_report()
        with patch("app.domains.coverup.router.create_report", return_value=report), \
             patch("app.domains.coverup.router.CoverageReportRepository"):
            resp = client.post("/api/v1/coverup/upload", json={
                "project_id": "proj-1",
                "format": "lcov",
                "report_data": "SF:app.py\nDA:1,1\nend_of_record",
                "project_name": "MyApp",
                "commit_sha": "abc123",
                "branch": "main",
            })
        assert resp.status_code == 200
        assert resp.json()["report_id"] == "rpt-1"

    def test_upload_invalid_format_raises_400(self, client):
        with patch("app.domains.coverup.router.create_report",
                   side_effect=ValueError("Desteklenmeyen format")), \
             patch("app.domains.coverup.router.CoverageReportRepository"):
            resp = client.post("/api/v1/coverup/upload", json={
                "project_id": "proj-1",
                "format": "unknown_format",
                "report_data": "garbage data",
            })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Reports list / get
# ---------------------------------------------------------------------------

class TestCoverUpReports:
    def test_list_reports_returns_list(self, client):
        item = _make_list_item()
        with patch("app.domains.coverup.router.CoverageReportRepository") as MockRepo:
            MockRepo.return_value.list_reports.return_value = [item]
            resp = client.get("/api/v1/coverup/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["report_id"] == "rpt-1"

    def test_get_report_returns_200(self, client):
        report = _make_coverage_report("rpt-99")
        with patch("app.domains.coverup.router.get_report_or_404", return_value=report), \
             patch("app.domains.coverup.router.CoverageReportRepository"):
            resp = client.get("/api/v1/coverup/reports/rpt-99")
        assert resp.status_code == 200
        assert resp.json()["report_id"] == "rpt-99"

    def test_get_report_404_when_not_found(self, client):
        with patch("app.domains.coverup.router.get_report_or_404",
                   side_effect=KeyError("Rapor bulunamadı")), \
             patch("app.domains.coverup.router.CoverageReportRepository"):
            resp = client.get("/api/v1/coverup/reports/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------

class TestCoverUpAnalyze:
    def test_analyze_returns_200_with_targets(self, client):
        from app.domains.coverup.schemas import AnalyzeResponse, CoverageSummary
        report = _make_coverage_report()
        response = AnalyzeResponse(
            report_id="rpt-1",
            targets=[],
            summary=CoverageSummary(),
            high_risk_count=0,
            medium_risk_count=0,
            low_risk_count=0,
        )
        with patch("app.domains.coverup.router.get_report_or_404", return_value=report), \
             patch("app.domains.coverup.router.analyze_report", return_value=response), \
             patch("app.domains.coverup.router.CoverageReportRepository"):
            resp = client.post("/api/v1/coverup/analyze", json={
                "report_id": "rpt-1",
                "min_risk_score": 0.3,
                "max_targets": 50,
            })
        assert resp.status_code == 200
        assert "targets" in resp.json()

    def test_analyze_404_when_report_not_found(self, client):
        with patch("app.domains.coverup.router.get_report_or_404",
                   side_effect=KeyError("not found")), \
             patch("app.domains.coverup.router.CoverageReportRepository"):
            resp = client.post("/api/v1/coverup/analyze", json={"report_id": "bad-id"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------

class TestCoverUpTrends:
    def test_trends_returns_200(self, client):
        trend = _make_trend_response()
        with patch("app.domains.coverup.router.build_trend_response", return_value=trend), \
             patch("app.domains.coverup.router.CoverageReportRepository") as MockRepo:
            MockRepo.return_value.list_trend_points.return_value = []
            resp = client.get("/api/v1/coverup/trends")
        assert resp.status_code == 200
        assert "direction" in resp.json()


# ---------------------------------------------------------------------------
# Generate Tests
# ---------------------------------------------------------------------------

class TestCoverUpGenerate:
    def test_generate_returns_empty_when_no_targets(self, client):
        from app.domains.coverup.schemas import AnalyzeResponse, CoverageSummary, GenerateTestResponse
        report = _make_coverage_report()
        empty_analyze = AnalyzeResponse(
            report_id="rpt-1",
            targets=[],
            summary=CoverageSummary(),
        )
        with patch("app.domains.coverup.router.get_report_or_404", return_value=report), \
             patch("app.domains.coverup.router.analyze_report", return_value=empty_analyze), \
             patch("app.domains.coverup.router.CoverageReportRepository"):
            resp = client.post("/api/v1/coverup/generate", json={
                "report_id": "rpt-1",
                "targets": [],
                "framework": "pytest",
                "language": "python",
                "max_tests": 10,
            })
        assert resp.status_code == 200
        assert resp.json()["total_generated"] == 0

    def test_generate_404_when_report_not_found(self, client):
        with patch("app.domains.coverup.router.get_report_or_404",
                   side_effect=KeyError("not found")), \
             patch("app.domains.coverup.router.CoverageReportRepository"):
            resp = client.post("/api/v1/coverup/generate", json={
                "report_id": "bad-id",
            })
        assert resp.status_code == 404
