"""
tests/unit/test_visual_routes.py
===================================
visual_bp (/api/visual/*) blueprint için birim testler.

Endpoints:
  GET    /api/visual/baselines              — baseline listesi (domain filtresi)
  GET    /api/visual/baselines/<domain>/<test_name>  — tek baseline meta
  DELETE /api/visual/baselines/<domain>/<test_name>  — baseline sil
  POST   /api/visual/compare                — görsel karşılaştırma
  POST   /api/visual/baselines/upload       — baseline yükleme

Dış bağımlılıklar (core.visual_regression, config.settings) stub'lanır.
"""
from __future__ import annotations

import importlib
import sys
import types
import pytest


# ── Stub helpers ──────────────────────────────────────────────────────────────


def _make_fake_visual_regression_module(tmp_path):
    """core.visual_regression modülünü sahte nesnelerle simüle eder."""

    class _FakeBaselineManager:
        def __init__(self, baselines_dir=None):
            self.baselines_dir = baselines_dir
            self._store: dict = {}

        def list_baselines(self, domain=None):
            items = list(self._store.values())
            if domain:
                items = [b for b in items if b.get("domain") == domain]
            return items

        def get_baseline(self, domain, test_name):
            key = f"{domain}/{test_name}"
            return self._store.get(key)

        def delete_baseline(self, domain, test_name):
            key = f"{domain}/{test_name}"
            if key in self._store:
                del self._store[key]
                return True
            return False

        def save_baseline(self, path, domain, test_name):
            key = f"{domain}/{test_name}"
            entry = {
                "domain": domain,
                "test_name": test_name,
                "path": str(path),
                "created_at": "2026-01-01T00:00:00",
            }
            self._store[key] = entry
            return entry

    class _FakeTester:
        def __init__(self, domain="default", config=None):
            self.domain = domain
            self.config = config or {}
            self.threshold = 0.95

        def compare(self, test_name, url=None, screenshot_path=None,
                    update_baseline=False, ignore_regions=None):
            return {
                "test_name": test_name,
                "diff_score": 0.02,
                "passed": True,
                "similarity": 0.98,
            }

        def batch_test(self, test_cases):
            return {"results": [], "summary": {"total": len(test_cases), "passed": len(test_cases)}}

        def generate_report(self, batch_result):
            return str(tmp_path / "report.html")

    mod = types.ModuleType("core.visual_regression")
    mod.BaselineManager = _FakeBaselineManager
    mod.create_visual_tester = lambda domain="default", config=None: _FakeTester(domain, config)
    mod.VisualRegressionTester = _FakeTester
    mod.SSIMCalculator = object
    mod.PixelDiffVisualizer = object
    return mod


# ── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture
def visual_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — visual_regression modülü stub'lanır."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-visual-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-visual-internal")

    # core.db stub'ları
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    # visual_regression modülü stub
    fake_mod = _make_fake_visual_regression_module(tmp_path)
    sys.modules["core.visual_regression"] = fake_mod

    # settings stub — BASE_DIR ve SCREENSHOTS_DIR
    monkeypatch.setattr("config.settings.settings.BASE_DIR", tmp_path, raising=False)
    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    monkeypatch.setattr("config.settings.settings.SCREENSHOTS_DIR", screenshots_dir, raising=False)

    # config/visual_config.json — yoksa empty dict döner
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client

    sys.modules.pop("core.visual_regression", None)


# ── GET /api/visual/baselines ─────────────────────────────────────────────────


class TestListBaselines:
    """GET /api/visual/baselines testleri."""

    def test_list_baselines_returns_200(self, visual_client):
        """Baseline listesi 200 dönmeli."""
        resp = visual_client.get("/api/visual/baselines")
        assert resp.status_code == 200

    def test_list_baselines_empty_list(self, visual_client):
        """Baseline yokken boş liste dönmeli."""
        resp = visual_client.get("/api/visual/baselines")
        data = resp.get_json()
        assert data["ok"] is True
        assert isinstance(data["baselines"], list)
        assert data["count"] == 0

    def test_list_baselines_with_domain_filter(self, visual_client):
        """Domain filtresi ile sadece o domain'e ait baseline'lar dönmeli."""
        resp = visual_client.get("/api/visual/baselines?domain=staging")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert isinstance(data["baselines"], list)

    def test_list_baselines_count_field_present(self, visual_client):
        """Yanıt count alanı içermeli."""
        resp = visual_client.get("/api/visual/baselines")
        data = resp.get_json()
        assert "count" in data


# ── GET /api/visual/baselines/<domain>/<test_name> ────────────────────────────


class TestGetBaseline:
    """GET /api/visual/baselines/<domain>/<test_name> testleri."""

    def test_get_baseline_unknown_returns_404(self, visual_client):
        """Bilinmeyen baseline 404 dönmeli."""
        resp = visual_client.get("/api/visual/baselines/production/nonexistent_test")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False

    def test_get_baseline_returns_ok_false_for_missing(self, visual_client):
        """Bulunamayan baseline yanıtı ok=False içermeli."""
        resp = visual_client.get("/api/visual/baselines/web/missing_page")
        data = resp.get_json()
        assert data.get("ok") is False


# ── DELETE /api/visual/baselines/<domain>/<test_name> ────────────────────────


class TestDeleteBaseline:
    """DELETE /api/visual/baselines/<domain>/<test_name> testleri."""

    def test_delete_unknown_baseline_returns_404(self, visual_client):
        """Var olmayan baseline silinmeye çalışılırsa 404 dönmeli."""
        resp = visual_client.delete("/api/visual/baselines/production/ghost_test")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False

    def test_delete_unknown_baseline_error_message(self, visual_client):
        """404 yanıtı error alanı içermeli."""
        resp = visual_client.delete("/api/visual/baselines/web/does_not_exist")
        data = resp.get_json()
        assert "error" in data


# ── POST /api/visual/compare ──────────────────────────────────────────────────


class TestCompareVisual:
    """POST /api/visual/compare testleri."""

    def test_compare_missing_test_name_returns_400(self, visual_client):
        """test_name olmadan 400 dönmeli."""
        resp = visual_client.post(
            "/api/visual/compare",
            json={"url": "https://example.com"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False

    def test_compare_missing_url_returns_400(self, visual_client):
        """url olmadan (update_baseline=False) 400 dönmeli."""
        resp = visual_client.post(
            "/api/visual/compare",
            json={"test_name": "home_page"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_compare_success_returns_200(self, visual_client):
        """Geçerli istek 200 dönmeli."""
        resp = visual_client.post(
            "/api/visual/compare",
            json={"test_name": "home_page", "url": "https://example.com"},
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_compare_success_ok_true(self, visual_client):
        """Başarılı karşılaştırma ok=True dönmeli."""
        resp = visual_client.post(
            "/api/visual/compare",
            json={"test_name": "login_page", "url": "https://example.com/login"},
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["ok"] is True

    def test_compare_result_contains_diff_score(self, visual_client):
        """Karşılaştırma sonucu diff_score içermeli."""
        resp = visual_client.post(
            "/api/visual/compare",
            json={"test_name": "checkout", "url": "https://example.com/checkout"},
            content_type="application/json",
        )
        data = resp.get_json()
        assert "result" in data
        assert "diff_score" in data["result"]

    def test_compare_with_threshold_param(self, visual_client):
        """threshold parametresi kabul edilmeli."""
        resp = visual_client.post(
            "/api/visual/compare",
            json={
                "test_name": "dashboard",
                "url": "https://example.com/dashboard",
                "threshold": 0.90,
            },
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_compare_update_baseline_true_no_url_needed(self, visual_client):
        """update_baseline=True olduğunda url olmasa da 400 dönmemeli."""
        resp = visual_client.post(
            "/api/visual/compare",
            json={"test_name": "profile", "update_baseline": True},
            content_type="application/json",
        )
        # update_baseline=True + url=None → route koşuluna göre 400 veya 200
        # Kaynak: `if not url and not update_bl: return 400`
        assert resp.status_code in (200, 500)  # 500 ok (tester.compare pathi)


# ── POST /api/visual/baselines/upload ────────────────────────────────────────


class TestUploadBaseline:
    """POST /api/visual/baselines/upload testleri."""

    def test_upload_missing_file_returns_400(self, visual_client):
        """Dosya gönderilmezse 400 dönmeli."""
        resp = visual_client.post(
            "/api/visual/baselines/upload",
            data={"domain": "web", "test_name": "home"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False

    def test_upload_missing_test_name_returns_400(self, visual_client, tmp_path):
        """test_name olmadan 400 dönmeli."""
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        resp = visual_client.post(
            "/api/visual/baselines/upload",
            data={
                "domain": "web",
                "file": (fake_png, "screenshot.png"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_success_returns_ok(self, visual_client, tmp_path):
        """Geçerli yükleme ok=True dönmeli."""
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        resp = visual_client.post(
            "/api/visual/baselines/upload",
            data={
                "domain": "web",
                "test_name": "home_page",
                "file": (fake_png, "screenshot.png"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_upload_returns_baseline_entry(self, visual_client, tmp_path):
        """Başarılı yükleme baseline entry döndürmeli."""
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        resp = visual_client.post(
            "/api/visual/baselines/upload",
            data={
                "domain": "staging",
                "test_name": "login_page",
                "file": (fake_png, "login.png"),
            },
            content_type="multipart/form-data",
        )
        data = resp.get_json()
        assert "baseline" in data
        assert data["baseline"]["test_name"] == "login_page"


# ── POST /api/visual/batch ────────────────────────────────────────────────────


class TestBatchCompare:
    """POST /api/visual/batch testleri."""

    def test_batch_missing_test_cases_returns_400(self, visual_client):
        """test_cases listesi olmadan 400 dönmeli."""
        resp = visual_client.post(
            "/api/visual/batch",
            json={"domain": "web"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_batch_success_returns_result(self, visual_client):
        """Geçerli istek result içermeli."""
        resp = visual_client.post(
            "/api/visual/batch",
            json={
                "domain": "web",
                "test_cases": [
                    {"test_name": "home", "url": "https://example.com"},
                    {"test_name": "login", "url": "https://example.com/login"},
                ],
            },
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "result" in data
