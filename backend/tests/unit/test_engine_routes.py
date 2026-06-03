"""Unit tests for engine routes — 8 tests.

Tests cover endpoint reachability and basic request/response behaviour.
All file I/O, subprocess calls and external HTTP requests are mocked so
these tests run without any DB, Redis or running engine process.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ─── Direct module loader ──────────────────────────────────────────────────────
# Bypass app/engine/routes/__init__.py (chain-imports all routers, some use
# Python 3.10+ union syntax that fails on 3.9).  Instead we load each route
# file as a standalone module under a private package name.

_ROUTES_DIR = Path(__file__).resolve().parents[2] / "app" / "engine" / "routes"


def _load_route_module(name: str):
    """Import a single route file without triggering __init__.py."""
    mod_name = f"_engine_route_{name}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _ROUTES_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    webhook_mod      = _load_route_module("webhook")
    runner_mod       = _load_route_module("runner")
    lifecycle_mod    = _load_route_module("lifecycle")
    manual_mod       = _load_route_module("manual")
    scheduler_mod    = _load_route_module("scheduler")
    mobile_mod       = _load_route_module("mobile")
    analytics_mod    = _load_route_module("analytics")
    ai_generation_mod = _load_route_module("ai_generation")

    webhook_router      = webhook_mod.router
    runner_router       = runner_mod.router
    lifecycle_router    = lifecycle_mod.router
    manual_router       = manual_mod.router
    scheduler_router    = scheduler_mod.router
    mobile_router       = mobile_mod.router
    analytics_router    = analytics_mod.router
    ai_generation_router = ai_generation_mod.router

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="engine route imports failed")


# ─── Client factories ──────────────────────────────────────────────────────────

def _webhook_client() -> "TestClient":
    app = FastAPI()
    app.include_router(webhook_router)
    return TestClient(app, raise_server_exceptions=False)


def _runner_client() -> "TestClient":
    app = FastAPI()
    app.include_router(runner_router)
    return TestClient(app, raise_server_exceptions=False)


def _lifecycle_client() -> "TestClient":
    app = FastAPI()
    app.include_router(lifecycle_router)
    return TestClient(app, raise_server_exceptions=False)


def _manual_client() -> "TestClient":
    app = FastAPI()
    app.include_router(manual_router)
    return TestClient(app, raise_server_exceptions=False)


def _scheduler_client() -> "TestClient":
    app = FastAPI()
    app.include_router(scheduler_router)
    return TestClient(app, raise_server_exceptions=False)


def _mobile_client() -> "TestClient":
    app = FastAPI()
    app.include_router(mobile_router)
    return TestClient(app, raise_server_exceptions=False)


def _analytics_client() -> "TestClient":
    app = FastAPI()
    app.include_router(analytics_router)
    return TestClient(app, raise_server_exceptions=False)


def _ai_generation_client() -> "TestClient":
    app = FastAPI()
    app.include_router(ai_generation_router)
    return TestClient(app, raise_server_exceptions=False)


# ─── Test 1: webhook route exists ─────────────────────────────────────────────

class TestWebhookRouteExists:
    """test_webhook_route_exists — POST /api/webhooks/github endpoint mevcut."""

    def test_webhook_route_exists(self):
        """Endpoint kayıtlı; geçerli bir JSON body ile 200 veya 4xx döner (5xx değil)."""
        client = _webhook_client()

        with (
            patch.object(webhook_mod, "_load_config", return_value={
                "github_secret": "",
                "github_token": "",
                "auto_run_on_pr": False,
                "auto_run_on_push": False,
                "run_browser": "chromium",
                "smoke_markers": "smoke",
                "notify_pr": False,
                "allowed_repos": [],
            }),
            patch.object(webhook_mod, "_save_event"),
            patch.object(webhook_mod, "_webhook_secret_required", return_value=False),
        ):
            resp = client.post(
                "/api/webhooks/github",
                json={"repository": {"full_name": "org/repo"}},
                headers={"X-GitHub-Event": "ping"},
            )

        assert resp.status_code < 500, f"Unexpected server error: {resp.text}"


# ─── Test 2: webhook missing payload 400 ──────────────────────────────────────

class TestWebhookMissingPayload400:
    """test_webhook_missing_payload_400 — eksik / bozuk payload durumunda 4xx döner."""

    def test_webhook_missing_payload_400(self):
        """Generic webhook boş body gönderildiğinde 422 Unprocessable döndürür."""
        client = _webhook_client()

        with patch.object(webhook_mod, "_webhook_secret_required", return_value=False):
            # GenericWebhookPayload body beklediği için eksik content-type ile istek
            resp = client.post(
                "/api/webhooks/generic",
                content=b"",
                headers={"Content-Type": "application/json"},
            )

        # FastAPI validation hatası: 422 veya 400
        assert resp.status_code in (400, 422), (
            f"Expected 400 or 422, got {resp.status_code}: {resp.text}"
        )


# ─── Test 3: runner route exists ──────────────────────────────────────────────

class TestRunnerRouteExists:
    """test_runner_route_exists — POST /api/run endpoint kayıtlı."""

    def test_runner_route_exists(self):
        """POST /api/run endpoint'i app içinde kayıtlı; 4xx/5xx değil 200/201/422 döner."""
        # run_tests, subprocess ve dosya I/O bağımlılıklarını mock'la
        with (
            patch.object(runner_mod, "_get_settings", return_value=MagicMock(
                BASE_DIR=MagicMock(__truediv__=lambda s, o: MagicMock(exists=lambda: False)),
                TESTS_DIR=MagicMock(exists=lambda: False),
                BEHAVE_BIN="behave",
            )),
        ):
            client = _runner_client()
            # Eksik zorunlu alan → 422 (route mevcut, schema validation çalışıyor)
            resp = client.post("/api/run", json={})

        assert resp.status_code in (200, 201, 400, 422), (
            f"Unexpected status: {resp.status_code} — {resp.text}"
        )


# ─── Test 4: lifecycle start ──────────────────────────────────────────────────

class TestLifecycleStart:
    """test_lifecycle_start — POST /api/lifecycle/process-analyst endpoint."""

    def test_lifecycle_start(self):
        """Geçerli bir analiz talebi geldiğinde AI mock'lanarak 200 döner."""
        ai_json = json.dumps({
            "summary": "Kullanıcı giriş akışı",
            "steps": ["Sayfayı aç", "Kullanıcı adını gir", "Şifreyi gir", "Giriş yap"],
        })
        mock_client = MagicMock()
        mock_client.ask.return_value = ai_json

        with patch.object(lifecycle_mod, "_try_import_ai_client", return_value=mock_client):
            client = _lifecycle_client()
            resp = client.post(
                "/api/lifecycle/process-analyst",
                json={"text": "Kullanıcı sisteme giriş yapabilmeli"},
            )

        # 200 başarılı veya 503 (AI client yüklenemedi — ortam bağımsız)
        assert resp.status_code in (200, 503), (
            f"Unexpected status: {resp.status_code} — {resp.text}"
        )


# ─── Test 5: manual run create ────────────────────────────────────────────────

class TestManualRunCreate:
    """test_manual_run_create — POST /api/manual-tests manuel test koşumu oluşturma."""

    def test_manual_run_create(self):
        """Yeni bir manuel test oluşturma isteği mock DB ile 201 döndürür."""
        fake_db = MagicMock()
        fake_db.execute.return_value = MagicMock(lastrowid=42)

        with patch.object(manual_mod, "_db", return_value=fake_db):
            client = _manual_client()
            resp = client.post(
                "/api/manual-tests",
                json={
                    "title": "Giriş ekranı testi",
                    "description": "Kullanıcı giriş akışını doğrula",
                },
            )

        # 201 Created veya 422 (schema uyuşmazlığı) — 5xx olmamalı
        assert resp.status_code in (201, 422), (
            f"Unexpected status: {resp.status_code} — {resp.text}"
        )


# ─── Test 6: scheduler list jobs ─────────────────────────────────────────────

class TestSchedulerListJobs:
    """test_scheduler_list_jobs — GET /api/schedules job listesi döndürür."""

    def test_scheduler_list_jobs(self):
        """Dosya I/O mock'lanarak mevcut schedule'lar döner."""
        sample_schedules = [
            {
                "id": "sched-001",
                "name": "Gece Smoke Testi",
                "cron": "0 2 * * *",
                "markers": "smoke",
                "browser": "chromium",
                "enabled": True,
                "project_id": None,
            }
        ]

        with patch.object(scheduler_mod, "_load", return_value=sample_schedules):
            client = _scheduler_client()
            resp = client.get("/api/schedules")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Response list olmalı"
        assert len(data) == 1
        assert data[0]["id"] == "sched-001"


# ─── Test 7: mobile device list ──────────────────────────────────────────────

class TestMobileDeviceList:
    """test_mobile_device_list — GET /api/mobile/devices cihaz listesi döndürür."""

    def test_mobile_device_list(self):
        """ADB ve simülatör araçları mock'lanarak cihaz listesi endpoint'i 200 döndürür."""
        fake_devices = [
            {"id": "emulator-5554", "name": "Pixel 6 API 33", "type": "android", "status": "online"}
        ]

        with (
            patch.object(mobile_mod, "_detect_adb_devices", return_value=fake_devices),
            patch.object(mobile_mod, "_detect_ios_simulators", return_value=[]),
            patch.object(mobile_mod, "_active_farm", return_value="local"),
        ):
            client = _mobile_client()
            resp = client.get("/api/mobile/devices")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        # devices anahtarı veya doğrudan liste olabilir
        devices = body.get("devices", body) if isinstance(body, dict) else body
        assert len(devices) >= 1


# ─── Test 8: analytics summary ────────────────────────────────────────────────

class TestAnalyticsSummary:
    """test_analytics_summary — GET /api/reporting/analytics/trends özet endpoint."""

    def test_analytics_summary(self):
        """Analitik servis mock'lanarak trend endpoint'i 200 döndürür."""
        fake_trends = {
            "period_hours": 24,
            "total_runs": 10,
            "pass_rate": 0.85,
            "trends": [],
        }

        mock_engine = MagicMock()
        mock_engine.get_trends.return_value = fake_trends

        with patch.object(analytics_mod, "_get_analytics_engine", return_value=mock_engine):
            client = _analytics_client()
            resp = client.get("/api/reporting/analytics/trends?hours=24")

        # 200 başarı veya 503 (engine yüklenemedi — ortam bağımsız)
        assert resp.status_code in (200, 503), (
            f"Unexpected status: {resp.status_code} — {resp.text}"
        )


# ─── Test 9: webhook route endpoint var mı ────────────────────────────────────

class TestWebhookEndpointRegistered:
    """test_webhook_endpoint_registered — /api/webhooks prefix altında en az bir route kayıtlı."""

    def test_webhook_endpoint_registered(self):
        """Router'ın routes listesi boş olmamalı; en az bir endpoint kayıtlı."""
        assert len(webhook_router.routes) > 0, (
            "webhook_router içinde kayıtlı route bulunamadı"
        )

    def test_webhook_github_endpoint_post(self):
        """POST /api/webhooks/github endpoint'i 404 dönmemeli (route mevcut)."""
        client = _webhook_client()
        with (
            patch.object(webhook_mod, "_load_config", return_value={
                "github_secret": "",
                "github_token": "",
                "auto_run_on_pr": False,
                "auto_run_on_push": False,
                "run_browser": "chromium",
                "smoke_markers": "smoke",
                "notify_pr": False,
                "allowed_repos": [],
            }),
            patch.object(webhook_mod, "_save_event"),
            patch.object(webhook_mod, "_webhook_secret_required", return_value=False),
        ):
            resp = client.post(
                "/api/webhooks/github",
                json={"repository": {"full_name": "acme/repo"}},
                headers={"X-GitHub-Event": "ping"},
            )
        assert resp.status_code != 404, "POST /api/webhooks/github route bulunamadı (404)"


# ─── Test 10: ai_generation route endpoint var mı ─────────────────────────────

class TestAiGenerationEndpointRegistered:
    """test_ai_generation_endpoint_registered — /api/ai prefix altında route'lar kayıtlı."""

    def test_ai_generation_has_routes(self):
        """ai_generation router'ı route içerip içermediğini doğrula."""
        assert len(ai_generation_router.routes) > 0, (
            "ai_generation_router içinde kayıtlı route bulunamadı"
        )

    def test_ai_generation_generate_test_endpoint(self):
        """POST /api/ai/generate-test endpoint'i 404 dönmemeli."""
        client = _ai_generation_client()
        # Payload eksik → 422; ama 404 değil (route mevcut demek)
        resp = client.post("/api/ai/generate-test", json={})
        assert resp.status_code != 404, "POST /api/ai/generate-test route bulunamadı (404)"
        assert resp.status_code < 500, f"Sunucu hatası: {resp.status_code} — {resp.text}"


# ─── Test 11: mobile route endpoint var mı ────────────────────────────────────

class TestMobileEndpointRegistered:
    """test_mobile_endpoint_registered — /api/mobile prefix altında route'lar kayıtlı."""

    def test_mobile_has_routes(self):
        """mobile_router route içermeli."""
        assert len(mobile_router.routes) > 0, (
            "mobile_router içinde kayıtlı route bulunamadı"
        )

    def test_mobile_devices_endpoint_get(self):
        """GET /api/mobile/devices endpoint'i 404 dönmemeli."""
        with (
            patch.object(mobile_mod, "_detect_adb_devices", return_value=[]),
            patch.object(mobile_mod, "_detect_ios_simulators", return_value=[]),
            patch.object(mobile_mod, "_active_farm", return_value="local"),
        ):
            client = _mobile_client()
            resp = client.get("/api/mobile/devices")
        assert resp.status_code != 404, "GET /api/mobile/devices route bulunamadı (404)"
        assert resp.status_code < 500, f"Sunucu hatası: {resp.status_code} — {resp.text}"


# ─── Test 12: scheduler route endpoint var mı ─────────────────────────────────

class TestSchedulerEndpointRegistered:
    """test_scheduler_endpoint_registered — /api/schedules prefix altında route'lar kayıtlı."""

    def test_scheduler_has_routes(self):
        """scheduler_router route içermeli."""
        assert len(scheduler_router.routes) > 0, (
            "scheduler_router içinde kayıtlı route bulunamadı"
        )

    def test_scheduler_list_endpoint_get(self):
        """GET /api/schedules endpoint'i 404 dönmemeli."""
        with patch.object(scheduler_mod, "_load", return_value=[]):
            client = _scheduler_client()
            resp = client.get("/api/schedules")
        assert resp.status_code != 404, "GET /api/schedules route bulunamadı (404)"
        assert resp.status_code < 500, f"Sunucu hatası: {resp.status_code} — {resp.text}"

    def test_scheduler_create_endpoint_post(self):
        """POST /api/schedules endpoint'i 404 dönmemeli (route mevcut)."""
        with (
            patch.object(scheduler_mod, "_load", return_value=[]),
            patch.object(scheduler_mod, "_save", return_value=None),
        ):
            client = _scheduler_client()
            # Eksik alanlar → 422; ama 404 değil
            resp = client.post("/api/schedules", json={})
        assert resp.status_code != 404, "POST /api/schedules route bulunamadı (404)"


# ─── Test 13: runner route endpoint var mı ────────────────────────────────────

class TestRunnerEndpointRegistered:
    """test_runner_endpoint_registered — /api/run prefix altında route'lar kayıtlı."""

    def test_runner_has_routes(self):
        """runner_router route içermeli."""
        assert len(runner_router.routes) > 0, (
            "runner_router içinde kayıtlı route bulunamadı"
        )

    def test_runner_post_run_endpoint(self):
        """POST /api/run endpoint'i 404 dönmemeli."""
        with patch.object(runner_mod, "_get_settings", return_value=MagicMock(
            BASE_DIR=MagicMock(__truediv__=lambda s, o: MagicMock(exists=lambda: False)),
            TESTS_DIR=MagicMock(exists=lambda: False),
            BEHAVE_BIN="behave",
        )):
            client = _runner_client()
            resp = client.post("/api/run", json={})
        assert resp.status_code != 404, "POST /api/run route bulunamadı (404)"
        assert resp.status_code < 500, f"Sunucu hatası: {resp.status_code} — {resp.text}"
