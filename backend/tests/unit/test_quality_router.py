"""Unit tests for the quality router (/quality)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.quality.router import router as quality_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(quality_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def _make_quality_metrics():
    """Return a minimal QualityMetrics-compatible MagicMock."""
    from unittest.mock import MagicMock
    metrics = MagicMock()
    metrics.latest_eval = MagicMock(
        available=True,
        mode="grounding-only",
        mapping_accuracy_pct=86.4,
        value_preservation_pct=100.0,
        unknown_rate_pct=13.6,
        gherkin_valid_pct=None,
        p95_latency_ms=44,
        total_fixtures=5,
        total_steps=22,
        llm_errors=0,
        generated_at="2026-04-19T06:53:31+00:00",
    )
    metrics.history = []
    metrics.reports_dir = "/tmp/reports"
    # Make it JSON-serializable by returning a dict from model_dump
    metrics.model_dump.return_value = {
        "latest_eval": {
            "available": True,
            "mode": "grounding-only",
            "mapping_accuracy_pct": 86.4,
            "value_preservation_pct": 100.0,
            "unknown_rate_pct": 13.6,
            "gherkin_valid_pct": None,
            "p95_latency_ms": 44,
            "total_fixtures": 5,
            "total_steps": 22,
            "llm_errors": 0,
            "generated_at": "2026-04-19T06:53:31+00:00",
        },
        "history": [],
        "reports_dir": "/tmp/reports",
    }
    return metrics


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/quality/metrics
# ---------------------------------------------------------------------------

class TestQualityMetrics:
    def test_default_params_returns_200(self, client):
        with patch("app.domains.quality.service.get_quality_metrics") as mock_svc:
            from app.domains.quality.service import QualityMetrics, EvalSnapshotModel
            mock_svc.return_value = QualityMetrics(
                latest_eval=EvalSnapshotModel(available=False),
                history=[],
                reports_dir="/tmp",
            )
            resp = client.get("/api/v1/quality/metrics")
        assert resp.status_code == 200

    def test_default_history_limit_is_10(self, client):
        with patch("app.domains.quality.service.get_quality_metrics") as mock_svc:
            from app.domains.quality.service import QualityMetrics, EvalSnapshotModel
            mock_svc.return_value = QualityMetrics(
                latest_eval=EvalSnapshotModel(available=False),
                history=[],
                reports_dir="/tmp",
            )
            client.get("/api/v1/quality/metrics")
        mock_svc.assert_called_once_with(history_limit=10)

    def test_custom_history_limit_passes_through(self, client):
        with patch("app.domains.quality.service.get_quality_metrics") as mock_svc:
            from app.domains.quality.service import QualityMetrics, EvalSnapshotModel
            mock_svc.return_value = QualityMetrics(
                latest_eval=EvalSnapshotModel(available=False),
                history=[],
                reports_dir="/tmp",
            )
            client.get("/api/v1/quality/metrics?history_limit=25")
        mock_svc.assert_called_once_with(history_limit=25)

    def test_history_limit_min_boundary_1(self, client):
        with patch("app.domains.quality.service.get_quality_metrics") as mock_svc:
            from app.domains.quality.service import QualityMetrics, EvalSnapshotModel
            mock_svc.return_value = QualityMetrics(
                latest_eval=EvalSnapshotModel(available=False),
                history=[],
                reports_dir="/tmp",
            )
            resp = client.get("/api/v1/quality/metrics?history_limit=1")
        assert resp.status_code == 200

    def test_history_limit_max_boundary_50(self, client):
        with patch("app.domains.quality.service.get_quality_metrics") as mock_svc:
            from app.domains.quality.service import QualityMetrics, EvalSnapshotModel
            mock_svc.return_value = QualityMetrics(
                latest_eval=EvalSnapshotModel(available=False),
                history=[],
                reports_dir="/tmp",
            )
            resp = client.get("/api/v1/quality/metrics?history_limit=50")
        assert resp.status_code == 200

    def test_history_limit_below_min_returns_422(self, client):
        resp = client.get("/api/v1/quality/metrics?history_limit=0")
        assert resp.status_code == 422

    def test_history_limit_above_max_returns_422(self, client):
        resp = client.get("/api/v1/quality/metrics?history_limit=51")
        assert resp.status_code == 422

    def test_negative_history_limit_returns_422(self, client):
        resp = client.get("/api/v1/quality/metrics?history_limit=-1")
        assert resp.status_code == 422

    def test_response_has_latest_eval_field(self, client):
        with patch("app.domains.quality.service.get_quality_metrics") as mock_svc:
            from app.domains.quality.service import QualityMetrics, EvalSnapshotModel
            mock_svc.return_value = QualityMetrics(
                latest_eval=EvalSnapshotModel(available=False),
                history=[],
                reports_dir="/tmp",
            )
            resp = client.get("/api/v1/quality/metrics")
        data = resp.json()
        assert "latest_eval" in data
        assert "available" in data["latest_eval"]

    def test_response_has_history_field(self, client):
        with patch("app.domains.quality.service.get_quality_metrics") as mock_svc:
            from app.domains.quality.service import QualityMetrics, EvalSnapshotModel
            mock_svc.return_value = QualityMetrics(
                latest_eval=EvalSnapshotModel(available=False),
                history=[],
                reports_dir="/tmp",
            )
            resp = client.get("/api/v1/quality/metrics")
        data = resp.json()
        assert "history" in data
        assert isinstance(data["history"], list)
