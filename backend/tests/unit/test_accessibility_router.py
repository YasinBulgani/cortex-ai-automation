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
