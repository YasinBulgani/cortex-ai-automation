"""
tests/unit/test_pipeline_routes.py
=====================================
Pipeline blueprint endpoint testleri.

DB çağrıları ve _run_feature tamamen mock'lanır.
Testler yalnızca HTTP katmanını doğrular:
  - Eksik / geçersiz girdi → 400 / 404 / 422
  - Preview endpoint: Gherkin üretimi, mock mod
  - Ana endpoint: test_id zorunluluğu, adım yoksa 422
  - Assertion synthesis: expect() kullanımı, TODO yorum yok (regresyon testi)
  - Koşu geçmişi: list dönüşü

Fixture stratejisi:
  Tam `app` modülünü yüklemek yerine minimal bir Flask uygulaması kuruluyor.
  Bu sayede Python 3.9'da derleme hatası veren diğer route modüllerinden
  (llm_agent_routes vb.) bağımsız çalışılabiliyor.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def pipeline_client(monkeypatch):
    """
    Sadece pipeline blueprint'ini barındıran minimal Flask test istemcisi.

    core.db, core.ai_engine ve config.settings stub'lanır;
    başka route modülleri yüklenmez.
    """
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")

    # ── core.db stub ──────────────────────────────────────────────────────
    fake_db = MagicMock()
    fake_db.get_manual_tests.return_value = []
    fake_db.create_pipeline_run.return_value = 1
    fake_db.complete_pipeline_run.return_value = None
    fake_db.list_pipeline_runs.return_value = []
    monkeypatch.setitem(sys.modules, "core.db", fake_db)

    # ── core.ai_engine stub ───────────────────────────────────────────────
    fake_ai_engine = MagicMock()
    fake_ai_engine.get_ai_engine = MagicMock(return_value=MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai_engine", fake_ai_engine)

    # ── config.settings stub ─────────────────────────────────────────────
    fake_settings_mod = MagicMock()
    fake_settings_mod.settings = MagicMock(
        OPENAI_API_KEY="",
        ANTHROPIC_API_KEY="",
    )
    monkeypatch.setitem(sys.modules, "config.settings", fake_settings_mod)
    monkeypatch.setitem(sys.modules, "config", MagicMock())

    # blueprint modülü daha önce yüklenmiş olabilir; temizle
    sys.modules.pop("routes.pipeline_routes", None)
    sys.modules.pop("routes", None)

    import importlib
    bp_module = importlib.import_module("routes.pipeline_routes")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.register_blueprint(bp_module.pipeline_bp)

    with app.test_client() as client:
        yield client


# ── /api/pipeline/manual-to-automation/preview ───────────────────────────────

class TestPreviewEndpoint:
    """POST /api/pipeline/manual-to-automation/preview testleri."""

    def test_preview_missing_steps_returns_400(self, pipeline_client):
        """`steps` alanı eksik → 400 dönmeli."""
        response = pipeline_client.post(
            "/api/pipeline/manual-to-automation/preview",
            json={"title": "Test Başlığı"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("ok") is False
        assert "error" in data

    def test_preview_empty_steps_returns_400(self, pipeline_client):
        """`steps` boş liste → 400 dönmeli."""
        response = pipeline_client.post(
            "/api/pipeline/manual-to-automation/preview",
            json={"title": "Test", "steps": []},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_preview_returns_gherkin_field(self, pipeline_client):
        """Geçerli steps ile preview → 200 ve `gherkin` alanı dönmeli."""
        steps = [
            {"action": "login butonuna tıkla", "expected": "anasayfa görünür"},
        ]
        with patch("routes.pipeline_routes._has_ai_key", return_value=False):
            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation/preview",
                json={"title": "Login Testi", "steps": steps},
                content_type="application/json",
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("ok") is True
        assert "gherkin" in data
        assert isinstance(data["gherkin"], str)
        assert len(data["gherkin"]) > 0

    def test_preview_gherkin_contains_step_text(self, pipeline_client):
        """Gherkin çıktısı adım action metnini içermeli."""
        action_text = "kullanici arama kutusuna yazar"
        steps = [{"action": action_text, "expected": "sonuçlar listelenir"}]
        with patch("routes.pipeline_routes._has_ai_key", return_value=False):
            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation/preview",
                json={"title": "Arama Testi", "steps": steps},
                content_type="application/json",
            )
        assert response.status_code == 200
        data = response.get_json()
        gherkin = data.get("gherkin", "")
        # _mock_gherkin adımı When satırına action metnini ekler
        assert action_text in gherkin

    def test_preview_mock_mode_flagged(self, pipeline_client):
        """AI anahtarı yokken mock_mode=True ve simulated=True dönmeli."""
        steps = [{"action": "sayfaya git", "expected": "sayfa açılır"}]
        with patch("routes.pipeline_routes._has_ai_key", return_value=False):
            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation/preview",
                json={"title": "Mock Test", "steps": steps},
                content_type="application/json",
            )
        data = response.get_json()
        assert data.get("mock_mode") is True
        assert data.get("simulated") is True

    def test_preview_allow_mock_false_no_key_returns_503(self, pipeline_client):
        """`allow_mock=false` + AI anahtarı yok → 503 dönmeli."""
        steps = [{"action": "tıkla", "expected": "açılır"}]
        with patch("routes.pipeline_routes._has_ai_key", return_value=False):
            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation/preview",
                json={"title": "T", "steps": steps, "allow_mock": False},
                content_type="application/json",
            )
        assert response.status_code == 503
        data = response.get_json()
        assert data.get("ok") is False

    def test_preview_no_body_returns_400(self, pipeline_client):
        """Body hiç gönderilmeden preview → steps yok → 400 dönmeli."""
        response = pipeline_client.post(
            "/api/pipeline/manual-to-automation/preview",
            data="",
            content_type="application/json",
        )
        assert response.status_code == 400


# ── Assertion synthesis (playwright_code) ─────────────────────────────────────
# _mock_playwright ana endpoint'te (manual_to_automation) kullanılıyor.

class TestAssertionSynthesis:
    """_mock_playwright assertion sentezi regresyon testleri."""

    SAMPLE_TEST = {
        "id": 99,
        "title": "Giriş Akışı",
        "steps": [
            {"action": "login butonuna tıkla", "expected": "dashboard görünür"},
            {"action": "profil sayfasına git", "expected": "profil yüklendi"},
        ],
    }

    def _call_pipeline(self, pipeline_client):
        """Ana pipeline endpoint'ini mock DB + mock mod ile çağırır."""
        mock_path = MagicMock()
        mock_path.write_text = MagicMock()
        mock_path.__str__ = lambda s: "/tmp/fake.feature"

        def fake_truediv(self, other):
            return mock_path

        with (
            patch("routes.pipeline_routes._has_ai_key", return_value=False),
            patch("routes.pipeline_routes._get_test_by_id", return_value=self.SAMPLE_TEST),
            patch("routes.pipeline_routes.create_pipeline_run", return_value=1),
            patch("routes.pipeline_routes.complete_pipeline_run"),
            patch("routes.pipeline_routes.FEATURES_DIR") as mfd,
            patch("routes.pipeline_routes.TESTS_DIR") as mtd,
            patch("routes.pipeline_routes.STEPS_DIR"),
        ):
            mfd.__truediv__ = fake_truediv
            mfd.mkdir = MagicMock()
            mfd.relative_to = MagicMock(return_value="features/generated/fake.feature")
            mtd.__truediv__ = fake_truediv
            mtd.mkdir = MagicMock()
            mtd.relative_to = MagicMock(return_value="tests/generated/fake.py")

            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation",
                json={"test_id": 99, "auto_run": False},
                content_type="application/json",
            )
        return response

    def test_playwright_has_expect(self, pipeline_client):
        """Playwright kodu `expect(` içermeli — assertion synthesis çalışıyor."""
        response = self._call_pipeline(pipeline_client)
        assert response.status_code == 200
        data = response.get_json()
        playwright_code = data.get("playwright_code", "")
        assert "expect(" in playwright_code, (
            "Assertion synthesis çalışmıyor: playwright_code içinde `expect(` bulunamadı.\n"
            f"Üretilen kod:\n{playwright_code}"
        )

    def test_playwright_no_todo_comment(self, pipeline_client):
        """playwright_code 'TODO: Assertions buraya' içermemeli — regresyon testi."""
        response = self._call_pipeline(pipeline_client)
        assert response.status_code == 200
        data = response.get_json()
        playwright_code = data.get("playwright_code", "")
        assert "TODO: Assertions buraya" not in playwright_code, (
            "Regresyon: eski TODO placeholder hâlâ mevcut. "
            "Assertion synthesis düzgün çalışmıyor.\n"
            f"Üretilen kod:\n{playwright_code}"
        )

    def test_playwright_imports_expect(self, pipeline_client):
        """playwright_code başında `from playwright.sync_api import` satırı olmalı."""
        response = self._call_pipeline(pipeline_client)
        data = response.get_json()
        playwright_code = data.get("playwright_code", "")
        assert "from playwright.sync_api import" in playwright_code
        assert "expect" in playwright_code

    def test_playwright_contains_page_goto(self, pipeline_client):
        """playwright_code `page.goto(` içermeli."""
        response = self._call_pipeline(pipeline_client)
        data = response.get_json()
        playwright_code = data.get("playwright_code", "")
        assert "page.goto(" in playwright_code

    def test_playwright_general_health_assertion(self, pipeline_client):
        """Genel sağlık kontrolü (error/404/500 URL assertion) olmalı."""
        response = self._call_pipeline(pipeline_client)
        data = response.get_json()
        playwright_code = data.get("playwright_code", "")
        # _mock_playwright sonuna genel hata URL assertion'ı ekliyor
        assert "error|404|500" in playwright_code or "not_to_have_url" in playwright_code


# ── /api/pipeline/manual-to-automation/runs ───────────────────────────────────

class TestListRunsEndpoint:
    """GET /api/pipeline/manual-to-automation/runs testleri."""

    def test_list_runs_returns_200(self, pipeline_client):
        """GET /runs → 200 dönmeli."""
        with patch("routes.pipeline_routes.list_pipeline_runs", return_value=[]):
            response = pipeline_client.get("/api/pipeline/manual-to-automation/runs")
        assert response.status_code == 200

    def test_list_runs_returns_runs_key(self, pipeline_client):
        """Response JSON'da `runs` anahtarı ve liste değeri olmalı."""
        with patch("routes.pipeline_routes.list_pipeline_runs", return_value=[]):
            response = pipeline_client.get("/api/pipeline/manual-to-automation/runs")
        data = response.get_json()
        assert "runs" in data
        assert isinstance(data["runs"], list)

    def test_list_runs_returns_total_key(self, pipeline_client):
        """Response JSON'da `total` anahtarı olmalı."""
        with patch("routes.pipeline_routes.list_pipeline_runs", return_value=[]):
            response = pipeline_client.get("/api/pipeline/manual-to-automation/runs")
        data = response.get_json()
        assert "total" in data

    def test_list_runs_with_mock_data(self, pipeline_client):
        """DB'den dönen run kayıtları JSON'da görünmeli ve total doğru olmalı."""
        fake_runs = [
            {"id": 1, "test_title": "Login", "status": "passed", "mock_mode": False},
            {"id": 2, "test_title": "Kayıt", "status": "failed", "mock_mode": True},
        ]
        with patch("routes.pipeline_routes.list_pipeline_runs", return_value=fake_runs):
            response = pipeline_client.get("/api/pipeline/manual-to-automation/runs")
        data = response.get_json()
        assert data["total"] == 2
        assert len(data["runs"]) == 2

    def test_list_runs_adds_provenance(self, pipeline_client):
        """Her run kaydında `provenance` alanı eklenmeli."""
        fake_runs = [{"id": 1, "test_title": "T", "status": "passed", "mock_mode": True}]
        with patch("routes.pipeline_routes.list_pipeline_runs", return_value=fake_runs):
            response = pipeline_client.get("/api/pipeline/manual-to-automation/runs")
        data = response.get_json()
        assert "provenance" in data["runs"][0]

    def test_list_runs_invalid_project_id_ignored(self, pipeline_client):
        """Geçersiz project_id query param → 200 (hata vermeden çalışmalı)."""
        with patch("routes.pipeline_routes.list_pipeline_runs", return_value=[]):
            response = pipeline_client.get(
                "/api/pipeline/manual-to-automation/runs?project_id=abc"
            )
        assert response.status_code == 200


# ── /api/pipeline/manual-to-automation (POST) ────────────────────────────────

class TestAutomationEndpoint:
    """POST /api/pipeline/manual-to-automation testleri."""

    def test_automation_missing_test_id_returns_400(self, pipeline_client):
        """`test_id` eksikken → 400 dönmeli."""
        response = pipeline_client.post(
            "/api/pipeline/manual-to-automation",
            json={"target_url": "http://example.com"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("ok") is False
        assert "test_id" in data.get("error", "").lower()

    def test_automation_invalid_test_id_returns_400(self, pipeline_client):
        """`test_id` geçersiz tür → 400 dönmeli."""
        response = pipeline_client.post(
            "/api/pipeline/manual-to-automation",
            json={"test_id": "not-a-number"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_automation_nonexistent_test_id_returns_404(self, pipeline_client):
        """DB'de bulunmayan test_id → 404 dönmeli."""
        with (
            patch("routes.pipeline_routes._has_ai_key", return_value=False),
            patch("routes.pipeline_routes._get_test_by_id", return_value=None),
        ):
            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation",
                json={"test_id": 9999},
                content_type="application/json",
            )
        assert response.status_code == 404
        data = response.get_json()
        assert data.get("ok") is False

    def test_automation_test_with_no_steps_returns_422(self, pipeline_client):
        """Adımsız test kaydı → 422 dönmeli."""
        empty_test = {"id": 5, "title": "Adımsız Test", "steps": []}
        with (
            patch("routes.pipeline_routes._has_ai_key", return_value=False),
            patch("routes.pipeline_routes._get_test_by_id", return_value=empty_test),
        ):
            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation",
                json={"test_id": 5},
                content_type="application/json",
            )
        assert response.status_code == 422
        data = response.get_json()
        assert data.get("ok") is False

    def test_automation_allow_mock_false_no_key_returns_503(self, pipeline_client):
        """`allow_mock=false` ve AI anahtarı yok → 503 dönmeli."""
        with patch("routes.pipeline_routes._has_ai_key", return_value=False):
            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation",
                json={"test_id": 1, "allow_mock": False},
                content_type="application/json",
            )
        assert response.status_code == 503
        data = response.get_json()
        assert data.get("ok") is False
        assert data.get("mock_mode") is True

    def test_automation_mock_mode_returns_ok(self, pipeline_client):
        """Mock modda geçerli test → 200 ve ok=True, gherkin+playwright_code dönmeli."""
        fake_test = {
            "id": 10,
            "title": "Örnek Test",
            "steps": [{"action": "butona tıkla", "expected": "modal açılır"}],
        }
        mock_path = MagicMock()
        mock_path.write_text = MagicMock()
        mock_path.__str__ = lambda s: "/tmp/fake.feature"

        def fake_truediv(self, other):
            return mock_path

        with (
            patch("routes.pipeline_routes._has_ai_key", return_value=False),
            patch("routes.pipeline_routes._get_test_by_id", return_value=fake_test),
            patch("routes.pipeline_routes.FEATURES_DIR") as mfd,
            patch("routes.pipeline_routes.TESTS_DIR") as mtd,
            patch("routes.pipeline_routes.STEPS_DIR"),
        ):
            mfd.__truediv__ = fake_truediv
            mfd.mkdir = MagicMock()
            mtd.__truediv__ = fake_truediv
            mtd.mkdir = MagicMock()

            response = pipeline_client.post(
                "/api/pipeline/manual-to-automation",
                json={"test_id": 10, "auto_run": False},
                content_type="application/json",
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("ok") is True
        assert data.get("mock_mode") is True
        assert "gherkin" in data
        assert "playwright_code" in data

    def test_automation_no_body_returns_400(self, pipeline_client):
        """Body olmadan POST → test_id yok → 400 dönmeli."""
        response = pipeline_client.post(
            "/api/pipeline/manual-to-automation",
            data="",
            content_type="application/json",
        )
        assert response.status_code == 400
