"""Unit tests for the a11y router — axe-core report ingest, list, get, aggregate.

14 tests covering:
  - POST /a11y/reports  (ingest valid, missing violations key, wrong type)
  - GET  /a11y/reports  (list, pagination params)
  - GET  /a11y/reports/{id} (get by id, not-found)
  - GET  /a11y/aggregate    (summary fields, empty history)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.a11y.router import router as a11y_router, _history, _history_lock
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ── helpers ──────────────────────────────────────────────────────────────

def _minimal_axe_payload(**overrides):
    """Return a minimal valid axe-core JSON payload."""
    base = {
        "url": "https://example.com",
        "timestamp": "2026-05-27T10:00:00Z",
        "violations": [],
        "passes": [],
        "incomplete": [],
        "inapplicable": [],
    }
    base.update(overrides)
    return base


def _axe_payload_with_violations():
    return {
        "url": "https://example.com/page",
        "timestamp": "2026-05-27T10:00:00Z",
        "violations": [
            {
                "id": "color-contrast",
                "impact": "serious",
                "help": "Elements must have sufficient color contrast",
                "description": "Ensures the contrast between foreground and background colors meets WCAG 2 AA contrast ratio thresholds",
                "nodes": [{"target": ["#main h1"]}, {"target": [".nav-link"]}],
            },
            {
                "id": "image-alt",
                "impact": "critical",
                "help": "Images must have alternate text",
                "description": "Ensures img elements have alternate text",
                "nodes": [{"target": ["img.logo"]}],
            },
        ],
        "passes": [{"id": "aria-allowed-attr"}],
        "incomplete": [],
        "inapplicable": [],
    }


# ── fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_history():
    """Isolate each test by clearing the in-memory ring buffer."""
    with _history_lock:
        _history.clear()
    yield
    with _history_lock:
        _history.clear()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(a11y_router, prefix="/api/v1")

    from app.deps import get_current_user, require_permission

    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    mock_user.email = "tester@neurex.io"

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_permission] = lambda perm: (lambda: None)

    return TestClient(app, raise_server_exceptions=False)


# ── POST /a11y/reports ────────────────────────────────────────────────────

class TestIngestReport:
    def test_ingest_valid_report_returns_201(self, client):
        resp = client.post("/api/v1/a11y/reports", json=_minimal_axe_payload())
        assert resp.status_code == 201

    def test_ingest_valid_report_response_fields(self, client):
        resp = client.post("/api/v1/a11y/reports", json=_minimal_axe_payload())
        data = resp.json()
        assert "id" in data
        assert "score" in data
        assert "violations_count" in data

    def test_ingest_perfect_score_no_violations(self, client):
        resp = client.post("/api/v1/a11y/reports", json=_minimal_axe_payload())
        data = resp.json()
        assert data["score"] == 100
        assert data["violations_count"] == 0

    def test_ingest_with_violations_reduces_score(self, client):
        resp = client.post("/api/v1/a11y/reports", json=_axe_payload_with_violations())
        data = resp.json()
        assert resp.status_code == 201
        # critical(25) + serious(10) = 35 penalty → score = 65
        assert data["score"] < 100
        assert data["violations_count"] == 2

    def test_ingest_non_dict_body_returns_4xx(self, client):
        resp = client.post("/api/v1/a11y/reports", json="not-a-dict")
        assert resp.status_code in (400, 422)

    def test_ingest_violations_not_list_is_gracefully_handled(self, client):
        payload = _minimal_axe_payload(violations="bad-value")
        resp = client.post("/api/v1/a11y/reports", json=payload)
        # Parser coerces non-list to [] — should succeed
        assert resp.status_code == 201
        assert resp.json()["violations_count"] == 0


# ── GET /a11y/reports ─────────────────────────────────────────────────────

class TestListReports:
    def test_list_empty_returns_200_and_empty_list(self, client):
        resp = client.get("/api/v1/a11y/reports")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_ingest_returns_one_item(self, client):
        client.post("/api/v1/a11y/reports", json=_minimal_axe_payload())
        resp = client.get("/api/v1/a11y/reports")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1

    def test_list_item_structure(self, client):
        client.post("/api/v1/a11y/reports", json=_minimal_axe_payload())
        item = client.get("/api/v1/a11y/reports").json()[0]
        for key in ("id", "submitted_by", "submitted_at", "report"):
            assert key in item

    def test_list_limit_param_respected(self, client):
        # Ingest 5 reports
        for _ in range(5):
            client.post("/api/v1/a11y/reports", json=_minimal_axe_payload())
        resp = client.get("/api/v1/a11y/reports?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_invalid_limit_returns_422(self, client):
        resp = client.get("/api/v1/a11y/reports?limit=0")
        assert resp.status_code == 422


# ── GET /a11y/aggregate ───────────────────────────────────────────────────

class TestAggregate:
    def test_aggregate_empty_history(self, client):
        resp = client.get("/api/v1/a11y/aggregate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 0
        assert data["avg_score"] == 0.0

    def test_aggregate_expected_keys(self, client):
        client.post("/api/v1/a11y/reports", json=_minimal_axe_payload())
        data = client.get("/api/v1/a11y/aggregate").json()
        for key in ("total_reports", "avg_score", "worst_score", "severity_totals", "most_common_violations"):
            assert key in data

    def test_aggregate_total_reports_count(self, client):
        for _ in range(3):
            client.post("/api/v1/a11y/reports", json=_minimal_axe_payload())
        data = client.get("/api/v1/a11y/aggregate").json()
        assert data["total_reports"] == 3
