"""
tests/unit/test_scheduler_routes.py
=====================================
scheduler_routes.py (scheduler_bp) HTTP katmanı testleri.

Blueprint: scheduler_bp  —  url_prefix=/api/schedules
Kapsanan endpointler:
  GET    /api/schedules                  — schedule listesi
  POST   /api/schedules                  — yeni schedule oluştur
  PUT    /api/schedules/<id>             — schedule güncelle
  DELETE /api/schedules/<id>             — schedule sil
  POST   /api/schedules/<id>/trigger     — anında tetikle
  GET    /api/schedules/<id>/runs        — koşu logları

Fixture stratejisi:
  apscheduler opsiyonel bir bağımlılık; sys.modules üzerinden stub'lanır.
  _load / _save JSON dosya erişimi de patch'lenir; böylece disk I/O olmaz.
  Yalnızca scheduler_routes blueprint'i yüklenir.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def scheduler_client(monkeypatch):
    """
    Sadece scheduler_routes blueprint'ini barındıran minimal Flask test
    istemcisi. APScheduler ve dosya I/O stub'lanır.
    """
    # ── APScheduler stub (opsiyonel bağımlılık) ──────────────────────────
    fake_apscheduler = MagicMock()
    fake_bg_scheduler_cls = MagicMock()
    fake_bg_scheduler_instance = MagicMock()
    fake_bg_scheduler_instance.get_job.return_value = None
    fake_bg_scheduler_cls.return_value = fake_bg_scheduler_instance
    fake_apscheduler.schedulers = MagicMock()
    fake_apscheduler.schedulers.background = MagicMock()
    fake_apscheduler.schedulers.background.BackgroundScheduler = fake_bg_scheduler_cls

    fake_triggers = MagicMock()
    fake_triggers.cron = MagicMock()
    fake_triggers.cron.CronTrigger = MagicMock()

    monkeypatch.setitem(sys.modules, "apscheduler", fake_apscheduler)
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers", fake_apscheduler.schedulers)
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers.background", fake_apscheduler.schedulers.background)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers", fake_triggers)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.cron", fake_triggers.cron)

    # ── blueprint modülünü temizle ve yükle ──────────────────────────────
    sys.modules.pop("routes.scheduler_routes", None)
    sys.modules.pop("routes", None)

    import importlib
    bp_module = importlib.import_module("routes.scheduler_routes")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.register_blueprint(bp_module.scheduler_bp)

    with app.test_client() as client:
        # _load ve _save patch'leri her test için override edilebilir;
        # varsayılan olarak boş liste + no-op kullanılır.
        with (
            patch("routes.scheduler_routes._load", return_value=[]),
            patch("routes.scheduler_routes._save"),
            patch("routes.scheduler_routes._register_with_apscheduler"),
            patch("routes.scheduler_routes._unregister_from_apscheduler"),
        ):
            yield client


# ── Yardımcı: kayıtlı schedule listesiyle client ─────────────────────────────

@pytest.fixture
def scheduler_client_with_data(monkeypatch):
    """Önceden yüklenmiş iki schedule içeren test istemcisi."""
    fake_schedules = [
        {
            "id": "sched-01",
            "name": "Gece Testi",
            "cron_expression": "0 2 * * *",
            "project_id": "proj-1",
            "feature_path": "features/login.feature",
            "markers": "",
            "browser": "chromium",
            "notify_on_fail": False,
            "notify_email": "",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00",
            "last_run_at": None,
            "runs": [
                {"run_id": "r1", "triggered_at": "2024-01-02T02:00:00", "status": "started"}
            ],
        },
        {
            "id": "sched-02",
            "name": "Haftalık Regresyon",
            "cron_expression": "0 10 * * 1",
            "project_id": "proj-2",
            "feature_path": "",
            "markers": "smoke",
            "browser": "firefox",
            "notify_on_fail": True,
            "notify_email": "team@example.com",
            "is_active": False,
            "created_at": "2024-01-01T00:00:00",
            "last_run_at": "2024-01-08T10:00:00",
            "runs": [],
        },
    ]

    # APScheduler stub
    fake_apscheduler = MagicMock()
    fake_bg_scheduler_cls = MagicMock()
    fake_bg_scheduler_instance = MagicMock()
    fake_bg_scheduler_instance.get_job.return_value = None
    fake_bg_scheduler_cls.return_value = fake_bg_scheduler_instance
    monkeypatch.setitem(sys.modules, "apscheduler", fake_apscheduler)
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers", MagicMock())
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers.background", MagicMock(BackgroundScheduler=fake_bg_scheduler_cls))
    monkeypatch.setitem(sys.modules, "apscheduler.triggers", MagicMock())
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.cron", MagicMock())

    sys.modules.pop("routes.scheduler_routes", None)
    sys.modules.pop("routes", None)

    import importlib
    bp_module = importlib.import_module("routes.scheduler_routes")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.register_blueprint(bp_module.scheduler_bp)

    with app.test_client() as client:
        with (
            patch("routes.scheduler_routes._load", return_value=fake_schedules),
            patch("routes.scheduler_routes._save"),
            patch("routes.scheduler_routes._register_with_apscheduler"),
            patch("routes.scheduler_routes._unregister_from_apscheduler"),
        ):
            yield client


# ── GET /api/schedules ────────────────────────────────────────────────────────

class TestListSchedules:
    """GET /api/schedules testleri."""

    def test_list_empty_returns_200(self, scheduler_client):
        """Store boşken → 200 ve boş liste dönmeli."""
        response = scheduler_client.get("/api/schedules")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_returns_all_schedules(self, scheduler_client_with_data):
        """Store'da 2 schedule varsa → 2 kayıt dönmeli."""
        response = scheduler_client_with_data.get("/api/schedules")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_does_not_include_runs_array(self, scheduler_client_with_data):
        """Liste yanıtında `runs` dizisi değil `run_count` olmalı."""
        data = scheduler_client_with_data.get("/api/schedules").get_json()
        for item in data:
            assert "runs" not in item
            assert "run_count" in item

    def test_list_filter_by_project_id(self, scheduler_client_with_data):
        """project_id query param ile filtreleme çalışmalı."""
        data = scheduler_client_with_data.get("/api/schedules?project_id=proj-1").get_json()
        assert len(data) == 1
        assert data[0]["id"] == "sched-01"


# ── POST /api/schedules ───────────────────────────────────────────────────────

class TestCreateSchedule:
    """POST /api/schedules testleri."""

    def test_create_missing_name_returns_400(self, scheduler_client):
        """`name` eksik → 400 ve ok=False dönmeli."""
        response = scheduler_client.post(
            "/api/schedules",
            json={"cron_expression": "0 2 * * *"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data.get("ok") is False
        assert "error" in data

    def test_create_missing_cron_expression_returns_400(self, scheduler_client):
        """`cron_expression` eksik → 400 dönmeli."""
        response = scheduler_client.post(
            "/api/schedules",
            json={"name": "Test Schedule"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_create_invalid_cron_expression_returns_400(self, scheduler_client):
        """5 alandan az cron ifadesi → 400 dönmeli."""
        response = scheduler_client.post(
            "/api/schedules",
            json={"name": "Bad Cron", "cron_expression": "0 2 *"},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "5 alan" in data.get("error", "")

    def test_create_valid_schedule_returns_200(self, scheduler_client):
        """Geçerli payload → 200 ve ok=True dönmeli."""
        response = scheduler_client.post(
            "/api/schedules",
            json={"name": "Günlük Test", "cron_expression": "0 6 * * *"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("ok") is True
        assert "schedule" in data

    def test_create_schedule_response_has_id(self, scheduler_client):
        """Oluşturulan schedule'da `id` alanı olmalı."""
        response = scheduler_client.post(
            "/api/schedules",
            json={"name": "ID Check", "cron_expression": "30 8 * * 1"},
            content_type="application/json",
        )
        data = response.get_json()
        assert "id" in data.get("schedule", {})

    def test_create_schedule_defaults(self, scheduler_client):
        """Opsiyonel alanlar verilmeden oluşturma → varsayılan browser=chromium ve is_active=True olmalı."""
        response = scheduler_client.post(
            "/api/schedules",
            json={"name": "Defaults Test", "cron_expression": "0 0 * * *"},
            content_type="application/json",
        )
        schedule = response.get_json().get("schedule", {})
        assert schedule.get("browser") == "chromium"
        assert schedule.get("is_active") is True


# ── PUT /api/schedules/<id> ───────────────────────────────────────────────────

class TestUpdateSchedule:
    """PUT /api/schedules/<id> testleri."""

    def test_update_nonexistent_schedule_returns_404(self, scheduler_client):
        """Var olmayan ID → 404 ve ok=False dönmeli."""
        response = scheduler_client.put(
            "/api/schedules/nonexistent-id",
            json={"is_active": False},
            content_type="application/json",
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data.get("ok") is False

    def test_update_existing_schedule_returns_200(self, scheduler_client_with_data):
        """Var olan ID → 200 ve ok=True dönmeli."""
        response = scheduler_client_with_data.put(
            "/api/schedules/sched-01",
            json={"is_active": False},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("ok") is True

    def test_update_modifies_field(self, scheduler_client_with_data):
        """Güncellenen alan response'da yeni değeri yansıtmalı."""
        response = scheduler_client_with_data.put(
            "/api/schedules/sched-01",
            json={"browser": "webkit"},
            content_type="application/json",
        )
        schedule = response.get_json().get("schedule", {})
        assert schedule.get("browser") == "webkit"


# ── DELETE /api/schedules/<id> ────────────────────────────────────────────────

class TestDeleteSchedule:
    """DELETE /api/schedules/<id> testleri."""

    def test_delete_nonexistent_returns_404(self, scheduler_client):
        """Var olmayan ID silme → 404 ve ok=False dönmeli."""
        response = scheduler_client.delete("/api/schedules/ghost-id")
        assert response.status_code == 404
        data = response.get_json()
        assert data.get("ok") is False

    def test_delete_existing_returns_200(self, scheduler_client_with_data):
        """Var olan ID silme → 200 ve ok=True dönmeli."""
        response = scheduler_client_with_data.delete("/api/schedules/sched-02")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("ok") is True


# ── POST /api/schedules/<id>/trigger ─────────────────────────────────────────

class TestTriggerSchedule:
    """POST /api/schedules/<id>/trigger testleri."""

    def test_trigger_returns_200_and_ok(self, scheduler_client):
        """Trigger endpoint → 200 ve ok=True dönmeli (var olmayan ID da kabul edilir)."""
        response = scheduler_client.post("/api/schedules/any-id/trigger")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("ok") is True
        assert "message" in data


# ── GET /api/schedules/<id>/runs ─────────────────────────────────────────────

class TestScheduleRuns:
    """GET /api/schedules/<id>/runs testleri."""

    def test_runs_nonexistent_schedule_returns_404(self, scheduler_client):
        """Var olmayan ID → 404 ve ok=False dönmeli."""
        response = scheduler_client.get("/api/schedules/ghost-id/runs")
        assert response.status_code == 404
        data = response.get_json()
        assert data.get("ok") is False

    def test_runs_existing_schedule_returns_200(self, scheduler_client_with_data):
        """Var olan ID → 200 ve ok=True, runs listesi dönmeli."""
        response = scheduler_client_with_data.get("/api/schedules/sched-01/runs")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("ok") is True
        assert "runs" in data
        assert isinstance(data["runs"], list)

    def test_runs_returns_run_entries(self, scheduler_client_with_data):
        """sched-01'in 1 koşu logu olmalı."""
        data = scheduler_client_with_data.get("/api/schedules/sched-01/runs").get_json()
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == "r1"
