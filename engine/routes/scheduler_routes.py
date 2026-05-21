"""
Zamanlanmış Test Koşuları — APScheduler tabanlı cron yönetimi.

Endpointler:
  GET    /api/schedules                      — tüm schedule'ları listele
  POST   /api/schedules                      — yeni schedule oluştur
  PUT    /api/schedules/<id>                 — schedule güncelle (aktif/pasif, cron)
  DELETE /api/schedules/<id>                 — schedule sil
  POST   /api/schedules/<id>/trigger         — anında tetikle
  GET    /api/schedules/<id>/runs            — son koşu logları
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

scheduler_bp = Blueprint("scheduler", __name__, url_prefix="/api/schedules")

# ─── Basit in-memory store (production'da SQLite/Postgres kullanın) ────────────
_STORE_FILE = Path(__file__).parent.parent / "data" / "schedules.json"
_store_lock = threading.Lock()


def _load() -> list[dict]:
    try:
        _STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _STORE_FILE.exists():
            return json.loads(_STORE_FILE.read_text())
    except Exception:
        pass
    return []


def _save(schedules: list[dict]) -> None:
    try:
        _STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STORE_FILE.write_text(json.dumps(schedules, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error("Schedule kaydetme hatası: %s", e)


# ─── APScheduler (opsiyonel — yüklü değilse schedule kayıt edilir ama cron çalışmaz) ─
_scheduler = None
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
    _scheduler.start()
    logger.info("APScheduler başlatıldı")
except ImportError:
    logger.warning("APScheduler yüklü değil — zamanlamalar kaydedilir ama otomatik tetiklenmez. pip install apscheduler")


def _run_schedule(schedule_id: str) -> None:
    """Bir schedule'ın test koşusunu başlatır."""
    with _store_lock:
        schedules = _load()
        schedule = next((s for s in schedules if s["id"] == schedule_id), None)
        if not schedule or not schedule.get("is_active", True):
            return

    logger.info("Schedule tetiklendi: %s (%s)", schedule["name"], schedule_id)

    try:
        import requests as req_lib
        payload = {
            "feature": schedule.get("feature_path", ""),
            "markers": schedule.get("markers", ""),
            "browser": schedule.get("browser", "chromium"),
        }
        # Engine'in kendi runner'ını çağır
        resp = req_lib.post("http://127.0.0.1:5001/api/run", json=payload, timeout=10)
        run_id = resp.json().get("run_id", "unknown")
        log_entry = {"run_id": run_id, "triggered_at": datetime.now().isoformat(), "status": "started"}
    except Exception as e:
        log_entry = {"run_id": "error", "triggered_at": datetime.now().isoformat(), "status": f"error: {e}"}

    # Koşu logunu güncelle
    with _store_lock:
        schedules = _load()
        for s in schedules:
            if s["id"] == schedule_id:
                s["last_run_at"] = log_entry["triggered_at"]
                runs = s.get("runs", [])
                runs.insert(0, log_entry)
                s["runs"] = runs[:50]  # Son 50 koşu
                break
        _save(schedules)


def _register_with_apscheduler(schedule: dict) -> None:
    if not _scheduler:
        return
    try:
        from apscheduler.triggers.cron import CronTrigger
        job_id = f"bgts_schedule_{schedule['id']}"
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
        if schedule.get("is_active", True):
            parts = schedule["cron_expression"].split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                trigger = CronTrigger(
                    minute=minute, hour=hour, day=day,
                    month=month, day_of_week=day_of_week,
                    timezone="Europe/Istanbul"
                )
                _scheduler.add_job(
                    _run_schedule, trigger,
                    args=[schedule["id"]],
                    id=job_id,
                    replace_existing=True,
                )
                logger.info("Schedule APScheduler'a eklendi: %s", schedule["name"])
    except Exception as e:
        logger.warning("APScheduler job eklenemedi: %s", e)


def _unregister_from_apscheduler(schedule_id: str) -> None:
    if not _scheduler:
        return
    try:
        job_id = f"bgts_schedule_{schedule_id}"
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
    except Exception:
        pass


# Startup: mevcut schedule'ları yükle ve APScheduler'a kaydet
def _boot_schedules() -> None:
    schedules = _load()
    for s in schedules:
        if s.get("is_active"):
            _register_with_apscheduler(s)
    logger.info("%d aktif schedule yüklendi", sum(1 for s in schedules if s.get("is_active")))

threading.Thread(target=_boot_schedules, daemon=True).start()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@scheduler_bp.route("", methods=["GET"])
def list_schedules():
    project_id = request.args.get("project_id")
    with _store_lock:
        schedules = _load()
    if project_id:
        schedules = [s for s in schedules if s.get("project_id") == project_id]
    # runs listesi çok büyük olabilir, özet döndür
    result = [{**{k: v for k, v in s.items() if k != "runs"}, "run_count": len(s.get("runs", []))} for s in schedules]
    return jsonify(result)


@scheduler_bp.route("", methods=["POST"])
def create_schedule():
    data = request.json or {}
    required = ["name", "cron_expression"]
    for r in required:
        if not data.get(r, "").strip():
            return jsonify({"ok": False, "error": f"{r} zorunludur"}), 400

    cron = data["cron_expression"].strip()
    if len(cron.split()) != 5:
        return jsonify({"ok": False, "error": "Cron ifadesi 5 alan içermelidir (örn: 0 2 * * *)"}), 400

    schedule = {
        "id": str(uuid.uuid4())[:8],
        "name": data["name"].strip(),
        "cron_expression": cron,
        "project_id": data.get("project_id", ""),
        "feature_path": data.get("feature_path", ""),
        "markers": data.get("markers", ""),
        "browser": data.get("browser", "chromium"),
        "notify_on_fail": data.get("notify_on_fail", False),
        "notify_email": data.get("notify_email", ""),
        "is_active": data.get("is_active", True),
        "created_at": datetime.now().isoformat(),
        "last_run_at": None,
        "runs": [],
    }

    with _store_lock:
        schedules = _load()
        schedules.append(schedule)
        _save(schedules)

    _register_with_apscheduler(schedule)

    return jsonify({"ok": True, "schedule": {k: v for k, v in schedule.items() if k != "runs"}})


@scheduler_bp.route("/<schedule_id>", methods=["PUT"])
def update_schedule(schedule_id: str):
    data = request.json or {}
    with _store_lock:
        schedules = _load()
        for s in schedules:
            if s["id"] == schedule_id:
                for field in ("name", "cron_expression", "is_active", "feature_path", "markers", "browser", "notify_on_fail", "notify_email"):
                    if field in data:
                        s[field] = data[field]
                _save(schedules)
                _register_with_apscheduler(s)
                return jsonify({"ok": True, "schedule": {k: v for k, v in s.items() if k != "runs"}})
    return jsonify({"ok": False, "error": "Schedule bulunamadı"}), 404


@scheduler_bp.route("/<schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id: str):
    with _store_lock:
        schedules = _load()
        new_list = [s for s in schedules if s["id"] != schedule_id]
        if len(new_list) == len(schedules):
            return jsonify({"ok": False, "error": "Schedule bulunamadı"}), 404
        _save(new_list)
    _unregister_from_apscheduler(schedule_id)
    return jsonify({"ok": True})


@scheduler_bp.route("/<schedule_id>/trigger", methods=["POST"])
def trigger_schedule(schedule_id: str):
    threading.Thread(target=_run_schedule, args=[schedule_id], daemon=True).start()
    return jsonify({"ok": True, "message": "Koşu başlatıldı"})


@scheduler_bp.route("/<schedule_id>/runs", methods=["GET"])
def get_schedule_runs(schedule_id: str):
    with _store_lock:
        schedules = _load()
    schedule = next((s for s in schedules if s["id"] == schedule_id), None)
    if not schedule:
        return jsonify({"ok": False, "error": "Schedule bulunamadı"}), 404
    return jsonify({"ok": True, "runs": schedule.get("runs", [])[:20]})
