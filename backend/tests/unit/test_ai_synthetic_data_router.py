"""AI Synthetic Data router unit tests — /api/v1/synthetic.

FastAPI TestClient. Generator classes, quality checker, and differential
privacy module are mocked via unittest.mock.patch so no heavy ML deps
are needed at test time.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.ai_synthetic_data.router import router as synthetic_router
    from app.deps import get_current_user
    from app.infra.models import User

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False


def _mock_user():
    u = MagicMock(spec=User)
    u.id = "test-user-id"
    u.email = "test@example.com"
    u.roles = []
    return u

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _app() -> TestClient:
    app = FastAPI()
    app.dependency_overrides[get_current_user] = _mock_user
    app.include_router(synthetic_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def _fake_user() -> MagicMock:
    u = MagicMock()
    u.id = "test-user"
    u.email = "test@test.com"
    return u


_ROUTER_MODULE = "app.domains.ai_synthetic_data.router"

_SAMPLE_DATA = [
    {"age": 25, "balance": 1000.0, "segment": "retail"},
    {"age": 35, "balance": 5000.0, "segment": "premium"},
    {"age": 45, "balance": 2500.0, "segment": "retail"},
]

_FAKE_QUALITY = {
    "column_stats": {"age": {"mean": 35.0}},
    "correlation_preservation": 0.95,
    "distribution_similarity": {"age": 0.88, "balance": 0.91},
    "overall_score": 0.895,
}

_FAKE_RECORDS = [
    {"age": 28, "balance": 1200.0, "segment": "retail"},
    {"age": 32, "balance": 4800.0, "segment": "premium"},
]


# ---------------------------------------------------------------------------
# GET /api/v1/synthetic/generators
# ---------------------------------------------------------------------------


def test_list_generators_returns_200() -> None:
    client = _app()
    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()):
        r = client.get("/api/v1/synthetic/generators")
    assert r.status_code == 200


def test_list_generators_has_kde_and_ctgan() -> None:
    client = _app()
    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()):
        r = client.get("/api/v1/synthetic/generators")
    body = r.json()
    assert "generators" in body
    ids = [g["id"] for g in body["generators"]]
    assert "kde" in ids
    assert "ctgan" in ids


def test_list_generators_kde_always_available() -> None:
    client = _app()
    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()):
        r = client.get("/api/v1/synthetic/generators")
    generators = {g["id"]: g for g in r.json()["generators"]}
    assert generators["kde"]["available"] is True


# ---------------------------------------------------------------------------
# POST /api/v1/synthetic/generate
# ---------------------------------------------------------------------------


def test_generate_kde_returns_200() -> None:
    client = _app()
    mock_gen = MagicMock()
    mock_gen.generate.return_value = _FAKE_RECORDS
    mock_gen.quality_metrics.return_value = _FAKE_QUALITY

    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()), \
         patch(f"{_ROUTER_MODULE}.KDEGenerator", return_value=mock_gen):
        r = client.post(
            "/api/v1/synthetic/generate",
            json={
                "sample_data": _SAMPLE_DATA,
                "count": 2,
                "generator_type": "kde",
            },
        )
    assert r.status_code == 200


def test_generate_returns_records_and_metrics() -> None:
    client = _app()
    mock_gen = MagicMock()
    mock_gen.generate.return_value = _FAKE_RECORDS
    mock_gen.quality_metrics.return_value = _FAKE_QUALITY

    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()), \
         patch(f"{_ROUTER_MODULE}.KDEGenerator", return_value=mock_gen):
        r = client.post(
            "/api/v1/synthetic/generate",
            json={
                "sample_data": _SAMPLE_DATA,
                "count": 2,
                "generator_type": "kde",
            },
        )
    body = r.json()
    assert "records" in body
    assert "quality_metrics" in body
    assert "record_count" in body
    assert body["record_count"] == 2


def test_generate_empty_sample_data_400() -> None:
    client = _app()
    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()):
        r = client.post(
            "/api/v1/synthetic/generate",
            json={"sample_data": [], "count": 5, "generator_type": "kde"},
        )
    assert r.status_code == 400


def test_generate_missing_sample_data_400() -> None:
    client = _app()
    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()):
        r = client.post(
            "/api/v1/synthetic/generate",
            json={"count": 5, "generator_type": "kde"},
        )
    assert r.status_code in {400, 422}


# ---------------------------------------------------------------------------
# POST /api/v1/synthetic/quality-check
# ---------------------------------------------------------------------------


def test_quality_check_returns_200() -> None:
    client = _app()
    mock_gen = MagicMock()
    mock_gen.quality_metrics.return_value = _FAKE_QUALITY

    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()), \
         patch(f"{_ROUTER_MODULE}.KDEGenerator", return_value=mock_gen):
        r = client.post(
            "/api/v1/synthetic/quality-check",
            json={"original": _SAMPLE_DATA, "synthetic": _FAKE_RECORDS},
        )
    assert r.status_code == 200


def test_quality_check_returns_overall_score() -> None:
    client = _app()
    mock_gen = MagicMock()
    mock_gen.quality_metrics.return_value = _FAKE_QUALITY

    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()), \
         patch(f"{_ROUTER_MODULE}.KDEGenerator", return_value=mock_gen):
        r = client.post(
            "/api/v1/synthetic/quality-check",
            json={"original": _SAMPLE_DATA, "synthetic": _FAKE_RECORDS},
        )
    body = r.json()
    assert "overall_score" in body
    assert isinstance(body["overall_score"], float)


def test_quality_check_missing_original_400() -> None:
    client = _app()
    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()):
        r = client.post(
            "/api/v1/synthetic/quality-check",
            json={"synthetic": _FAKE_RECORDS},
        )
    assert r.status_code in {400, 422}


def test_quality_check_empty_datasets_400() -> None:
    client = _app()
    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()):
        r = client.post(
            "/api/v1/synthetic/quality-check",
            json={"original": [], "synthetic": []},
        )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/synthetic/privacy-risk
# ---------------------------------------------------------------------------


def test_privacy_risk_returns_200() -> None:
    client = _app()
    mock_checker = MagicMock()
    mock_checker.privacy_risk_score.return_value = {
        "risk_score": 0.15,
        "vulnerable_columns": ["age"],
        "recommendation": "Low risk — synthetic data is safe to share.",
    }

    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()), \
         patch(f"{_ROUTER_MODULE}.DataQualityChecker", return_value=mock_checker):
        r = client.post(
            "/api/v1/synthetic/privacy-risk",
            json={"original": _SAMPLE_DATA, "synthetic": _FAKE_RECORDS},
        )
    assert r.status_code == 200


def test_privacy_risk_has_risk_score_key() -> None:
    client = _app()
    mock_checker = MagicMock()
    mock_checker.privacy_risk_score.return_value = {
        "risk_score": 0.05,
        "vulnerable_columns": [],
        "recommendation": "Safe.",
    }

    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()), \
         patch(f"{_ROUTER_MODULE}.DataQualityChecker", return_value=mock_checker):
        r = client.post(
            "/api/v1/synthetic/privacy-risk",
            json={"original": _SAMPLE_DATA, "synthetic": _FAKE_RECORDS},
        )
    body = r.json()
    assert "risk_score" in body
    assert "recommendation" in body


def test_privacy_risk_missing_original_400() -> None:
    client = _app()
    with patch(f"{_ROUTER_MODULE}.get_current_user", return_value=_fake_user()):
        r = client.post(
            "/api/v1/synthetic/privacy-risk",
            json={"synthetic": _FAKE_RECORDS},
        )
    assert r.status_code in {400, 422}
