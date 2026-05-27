"""
tests/unit/test_visual_ai_routes.py
=====================================
visual_ai_bp (/api/visual-ai/*) için birim testler.

Endpoints:
  GET  /api/visual-ai/health
  POST /api/visual-ai/analyze
  POST /api/visual-ai/smart-update
  POST /api/visual-ai/report
  GET  /api/visual-ai/baseline-status
  GET  /api/visual-ai/statistics
  GET  /api/visual-ai/config

Dış bağımlılıklar (core.python.visual_ai modülü, dosya sistemi) stub'lanır.
"""
from __future__ import annotations

import importlib
import sys
import types
import pytest


# ── Stub helpers ──────────────────────────────────────────────────────────────

def _make_fake_visual_ai_module():
    """core.python.visual_ai modülünü sahte nesnelerle simüle eder."""

    class _FakeAnomaly:
        def __init__(self):
            self.type = "color_shift"
            self.location = {"x": 10, "y": 10, "w": 50, "h": 50}
            self.severity = "low"
            self.confidence = 0.85
            self.description = "Hafif renk kayması tespit edildi"

    class _FakeAnalysis:
        def __init__(self):
            self.similarity = 0.95
            self.anomalies = []
            self.has_anomalies = False
            self.recommendations = ["Baseline güncel, değişiklik gerekmez."]
            self.should_update_baseline = False

    class _FakeAnalyzer:
        anomaly_detection_threshold = 0.80
        color_shift_threshold = 30
        layout_change_threshold = 0.15

        def analyze_visual_difference(self, current, baseline, name):
            return _FakeAnalysis()

        def generate_analysis_report(self, analysis_obj, baseline_name):
            return f"## Rapor: {baseline_name}\nSimilarity: {analysis_obj.similarity}"

    class _FakeManager:
        def __init__(self, baselines_dir):
            self.baselines_dir = baselines_dir

        def smart_update_baseline(self, name, current, baseline, force):
            return {"updated": False, "reason": "Similarity yeterince yüksek", "similarity": 0.95}

        def get_baseline_status(self, name):
            return {"exists": True, "created_at": "2026-01-01T00:00:00", "size_bytes": 12345}

    mod = types.ModuleType("core.python.visual_ai")
    mod.get_visual_ai_analyzer = lambda: _FakeAnalyzer()
    mod.SmartBaselineManager = _FakeManager
    return mod


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def visual_ai_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — visual_ai modülü stub'lanır."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-visual-ai-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-visual-ai-internal")

    # core.db stubs
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    # visual_ai modülü stub'la (import öncesi sys.modules'a enjekte et)
    fake_module = _make_fake_visual_ai_module()
    sys.modules["core.python.visual_ai"] = fake_module

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client

    # Cleanup
    sys.modules.pop("core.python.visual_ai", None)


# ── /api/visual-ai/health ────────────────────────────────────────────────────

class TestVisualAiHealth:
    """GET /api/visual-ai/health testleri."""

    def test_health_returns_200(self, visual_ai_client):
        """Health endpoint 200 dönmeli."""
        resp = visual_ai_client.get("/api/visual-ai/health")
        assert resp.status_code == 200

    def test_health_status_is_healthy(self, visual_ai_client):
        """Health yanıtı status=healthy içermeli."""
        resp = visual_ai_client.get("/api/visual-ai/health")
        data = resp.get_json()
        assert data.get("status") == "healthy"

    def test_health_service_name(self, visual_ai_client):
        """Health yanıtı service=visual_ai içermeli."""
        resp = visual_ai_client.get("/api/visual-ai/health")
        data = resp.get_json()
        assert data.get("service") == "visual_ai"


# ── /api/visual-ai/analyze ───────────────────────────────────────────────────

class TestVisualAiAnalyze:
    """POST /api/visual-ai/analyze testleri."""

    def test_analyze_missing_current_image_returns_400(self, visual_ai_client):
        """current_image olmadan 400 dönmeli."""
        resp = visual_ai_client.post(
            "/api/visual-ai/analyze",
            json={"baseline_name": "login_page"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_analyze_with_current_image_returns_success(self, visual_ai_client, tmp_path):
        """current_image ile analiz başarılı dönmeli."""
        img = tmp_path / "current.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        resp = visual_ai_client.post(
            "/api/visual-ai/analyze",
            json={
                "current_image": str(img),
                "baseline_name": "test_baseline",
            },
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True

    def test_analyze_returns_similarity_field(self, visual_ai_client, tmp_path):
        """Analiz yanıtı similarity alanı içermeli."""
        img = tmp_path / "current.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 50)

        resp = visual_ai_client.post(
            "/api/visual-ai/analyze",
            json={"current_image": str(img), "baseline_name": "home"},
            content_type="application/json",
        )
        data = resp.get_json()
        assert "similarity" in data

    def test_analyze_returns_anomalies_list(self, visual_ai_client, tmp_path):
        """Analiz yanıtı anomalies listesi içermeli."""
        img = tmp_path / "current.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 50)

        resp = visual_ai_client.post(
            "/api/visual-ai/analyze",
            json={"current_image": str(img), "baseline_name": "dashboard"},
            content_type="application/json",
        )
        data = resp.get_json()
        assert isinstance(data.get("anomalies"), list)


# ── /api/visual-ai/smart-update ─────────────────────────────────────────────

class TestSmartBaselineUpdate:
    """POST /api/visual-ai/smart-update testleri."""

    def test_smart_update_missing_baseline_name_returns_400(self, visual_ai_client):
        """baseline_name olmadan 400 dönmeli."""
        resp = visual_ai_client.post(
            "/api/visual-ai/smart-update",
            json={"current_image": "/some/path.png"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_smart_update_missing_current_image_returns_400(self, visual_ai_client):
        """current_image olmadan 400 dönmeli."""
        resp = visual_ai_client.post(
            "/api/visual-ai/smart-update",
            json={"baseline_name": "login"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_smart_update_success_returns_ok(self, visual_ai_client, tmp_path):
        """Geçerli istek success=True dönmeli."""
        img = tmp_path / "cur.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 50)

        resp = visual_ai_client.post(
            "/api/visual-ai/smart-update",
            json={"baseline_name": "checkout", "current_image": str(img)},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True


# ── /api/visual-ai/report ────────────────────────────────────────────────────

class TestGenerateReport:
    """POST /api/visual-ai/report testleri."""

    def test_report_missing_analysis_returns_400(self, visual_ai_client):
        """analysis nesnesi olmadan 400 dönmeli."""
        resp = visual_ai_client.post(
            "/api/visual-ai/report",
            json={"baseline_name": "home"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_report_with_analysis_returns_success(self, visual_ai_client):
        """Geçerli analysis ile rapor başarılı üretilmeli."""
        resp = visual_ai_client.post(
            "/api/visual-ai/report",
            json={
                "analysis": {
                    "similarity": 0.97,
                    "anomalies": [],
                    "recommendations": [],
                },
                "baseline_name": "profile",
            },
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True
        assert "report" in data


# ── /api/visual-ai/baseline-status ──────────────────────────────────────────

class TestBaselineStatus:
    """GET /api/visual-ai/baseline-status testleri."""

    def test_baseline_status_missing_name_returns_400(self, visual_ai_client):
        """baseline_name parametresi olmadan 400 dönmeli."""
        resp = visual_ai_client.get("/api/visual-ai/baseline-status")
        assert resp.status_code == 400

    def test_baseline_status_with_name_returns_success(self, visual_ai_client):
        """Geçerli baseline_name ile success=True dönmeli."""
        resp = visual_ai_client.get("/api/visual-ai/baseline-status?baseline_name=login_page")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True


# ── /api/visual-ai/statistics ───────────────────────────────────────────────

class TestStatistics:
    """GET /api/visual-ai/statistics testleri."""

    def test_statistics_returns_200(self, visual_ai_client):
        """Statistics endpoint 200 dönmeli."""
        resp = visual_ai_client.get("/api/visual-ai/statistics")
        assert resp.status_code == 200

    def test_statistics_contains_service(self, visual_ai_client):
        """Statistics yanıtı service alanı içermeli."""
        resp = visual_ai_client.get("/api/visual-ai/statistics")
        data = resp.get_json()
        assert data.get("service") == "visual_ai"

    def test_statistics_contains_analyzer_thresholds(self, visual_ai_client):
        """Statistics yanıtı analyzer threshold bilgileri içermeli."""
        resp = visual_ai_client.get("/api/visual-ai/statistics")
        data = resp.get_json()
        assert "analyzer" in data


# ── /api/visual-ai/config ────────────────────────────────────────────────────

class TestConfig:
    """GET /api/visual-ai/config testleri."""

    def test_config_returns_200(self, visual_ai_client):
        """Config endpoint 200 dönmeli."""
        resp = visual_ai_client.get("/api/visual-ai/config")
        assert resp.status_code == 200

    def test_config_contains_features(self, visual_ai_client):
        """Config yanıtı features listesi içermeli."""
        resp = visual_ai_client.get("/api/visual-ai/config")
        data = resp.get_json()
        assert "config" in data
        assert "features" in data["config"]

    def test_config_contains_thresholds(self, visual_ai_client):
        """Config yanıtı thresholds içermeli."""
        resp = visual_ai_client.get("/api/visual-ai/config")
        data = resp.get_json()
        assert "thresholds" in data["config"]
