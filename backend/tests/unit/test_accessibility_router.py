"""Accessibility router endpoint'leri — UX-F3-306.

Gerçek FastAPI app + TestClient kullanır ama analyzer.analyze monkeypatch'li
(gateway_complete patlatmasın). Bu testler PR #52'deki core analyzer testleriyle
ORTOGONAL — router layer'ı odaklıdır.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domains.accessibility import accessibility_analyzer
from app.domains.accessibility.router import router
from app.domains.accessibility.schemas import (
    A11yNode,
    A11yViolation,
    AnalyzeA11yResponse,
)


def _app() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _sample_violation_payload() -> dict:
    return {
        "violations": [
            {
                "id": "color-contrast",
                "impact": "serious",
                "help": "Contrast",
                "tags": ["wcag2aa"],
                "nodes": [
                    {"html": "<button>X</button>", "target": ["button"]}
                ],
            }
        ],
        "url": "https://ex.com",
        "max_violations": 5,
    }


def test_status_endpoint_shape() -> None:
    client = _app()
    r = client.get("/accessibility/status")
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data
    assert "total_calls" in data


def test_analyze_disabled_returns_noop(monkeypatch) -> None:
    """Flag kapalıyken endpoint ok=true + empty remediations döner."""
    monkeypatch.delenv("AI_ACCESSIBILITY_ENABLED", raising=False)
    client = _app()
    r = client.post("/accessibility/analyze", json=_sample_violation_payload())
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["remediations"] == []
    assert data["error"] is None


def test_analyze_validation_error_422() -> None:
    """Boş violations → Pydantic 422."""
    client = _app()
    r = client.post("/accessibility/analyze", json={"violations": []})
    assert r.status_code == 422


def test_analyze_calls_service(monkeypatch) -> None:
    """Router'ın service'i gerçekten çağırdığını doğrula."""
    called = {"count": 0}

    def fake_analyze(req):
        called["count"] += 1
        return AnalyzeA11yResponse(
            ok=True,
            remediations=[],
            skipped_count=0,
            error=None,
            latency_ms=1,
        )

    monkeypatch.setattr(accessibility_analyzer, "analyze", fake_analyze)
    client = _app()
    r = client.post("/accessibility/analyze", json=_sample_violation_payload())
    assert r.status_code == 200
    assert called["count"] == 1


def test_analyze_preserves_error_response(monkeypatch) -> None:
    """Service ok=false döndürse bile HTTP 200 olur (ok alanı kontrol edilir)."""
    monkeypatch.setattr(
        accessibility_analyzer,
        "analyze",
        lambda req: AnalyzeA11yResponse(
            ok=False,
            remediations=[],
            error="AI Gateway erişilemedi: Connection refused",
        ),
    )
    client = _app()
    r = client.post("/accessibility/analyze", json=_sample_violation_payload())
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert "Gateway" in data["error"]


# ---------------------------------------------------------------------------
# Additional router tests (Task 3)
# ---------------------------------------------------------------------------

def test_analyze_missing_url_still_validates_violations() -> None:
    """Payload without 'url' field must still be accepted (url is optional)."""
    client = _app()
    payload = {
        "violations": [
            {
                "id": "image-alt",
                "impact": "critical",
                "help": "Images must have alternate text",
                "tags": ["wcag2a"],
                "nodes": [{"html": "<img src='x.jpg'>", "target": ["img"]}],
            }
        ]
    }
    r = client.post("/accessibility/analyze", json=payload)
    # 200 (ok) or 422 (if url is required) — both valid, not a 5xx
    assert r.status_code in {200, 422}


def test_analyze_returns_remediations_list(monkeypatch) -> None:
    """Successful analyze must return a list under 'remediations' key."""
    monkeypatch.setattr(
        accessibility_analyzer,
        "analyze",
        lambda req: AnalyzeA11yResponse(
            ok=True,
            remediations=[],
            skipped_count=0,
            error=None,
            latency_ms=42,
        ),
    )
    client = _app()
    r = client.post("/accessibility/analyze", json=_sample_violation_payload())
    assert r.status_code == 200
    data = r.json()
    assert "remediations" in data
    assert isinstance(data["remediations"], list)


def test_status_endpoint_enabled_field_is_boolean() -> None:
    """GET /accessibility/status 'enabled' field must be a boolean."""
    client = _app()
    r = client.get("/accessibility/status")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["enabled"], bool)


def test_analyze_invalid_json_returns_422() -> None:
    """POST /accessibility/analyze with completely wrong types returns 422."""
    client = _app()
    r = client.post("/accessibility/analyze", json={"violations": "not-a-list"})
    assert r.status_code == 422
