"""
Scheduler routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/scheduler_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/scheduler.py — APIRouter, port 8000 (consolidated)

Endpointler:
  GET    /api/schedules                  — tüm schedule'ları listele
  POST   /api/schedules                  — yeni schedule oluştur
  PUT    /api/schedules/{id}             — schedule güncelle
  DELETE /api/schedules/{id}             — schedule sil
  POST   /api/schedules/{id}/trigger     — anında tetikle
  GET    /api/schedules/{id}/runs        — son koşu logları
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["engine", "scheduler"])

# ─── Basit in-memory / JSON store ─────────────────────────────────────────────

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


# ─── APScheduler (opsiyonel) ──────────────────────────────────────────────────

_scheduler = None
try:
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
    from apscheduler.triggers.cron import CronTrigger  # type: ignore
    _scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
    _scheduler.start()
    logger.info("APScheduler başlatıldı")
except ImportError:
    logger.warning(
        "APScheduler yüklü değil — zamanlamalar kaydedilir ama otomatik "
        "tetiklenmez. pip install apscheduler"
    )


def _run_schedule(schedule_id: str) -> None:
    """Bir schedule'ın test koşusunu başlatır (runner /api/run endpointini çağırır)."""
    with _store_lock:
        schedules = _load()
        schedule = next((s for s in schedules if s["id"] == schedule_id), None)
        if not schedule or not schedule.get("is_active", True):
            return

    logger.info("Schedule tetiklendi: %s (%s)", schedule["name"], schedule_id)

    try:
        import httpx  # type: ignore

        payload = {
            "feature": schedule.get("feature_path", ""),
            "markers": schedule.get("markers", ""),
            "browser": schedule.get("browser", "chromium"),
        }
        resp = httpx.post("http://127.0.0.1:8000/api/run", json=payload, timeout=10)
        run_id = resp.json().get("run_id", "unknown")
        log_entry = {
            "run_id": run_id,
            "triggered_at": datetime.now().isoformat(),
            "status": "started",
        }
    except Exception as e:
        log_entry = {
            "run_id": "error",
            "triggered_at": datetime.now().isoformat(),
            "status": f"error: {e}",
        }

    with _store_lock:
        schedules = _load()
        for s in schedules:
            if s["id"] == schedule_id:
                s["last_run_at"] = log_entry["triggered_at"]
                runs = s.get("runs", [])
                runs.insert(0, log_entry)
                s["runs"] = runs[:50]
                break
        _save(schedules)


def _register_with_apscheduler(schedule: dict) -> None:
    if not _scheduler:
        return
    try:
        from apscheduler.triggers.cron import CronTrigger  # type: ignore

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
                    timezone="Europe/Istanbul",
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


def _boot_schedules() -> None:
    schedules = _load()
    for s in schedules:
        if s.get("is_active"):
            _register_with_apscheduler(s)
    logger.info(
        "%d aktif schedule yüklendi", sum(1 for s in schedules if s.get("is_active"))
    )


threading.Thread(target=_boot_schedules, daemon=True).start()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1)
    cron_expression: str = Field(..., min_length=1)
    project_id: str = ""
    feature_path: str = ""
    markers: str = ""
    browser: str = "chromium"
    notify_on_fail: bool = False
    notify_email: str = ""
    is_active: bool = True


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None
    feature_path: Optional[str] = None
    markers: Optional[str] = None
    browser: Optional[str] = None
    notify_on_fail: Optional[bool] = None
    notify_email: Optional[str] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
def list_schedules(project_id: Optional[str] = None):
    with _store_lock:
        schedules = _load()
    if project_id:
        schedules = [s for s in schedules if s.get("project_id") == project_id]
    return [
        {**{k: v for k, v in s.items() if k != "runs"}, "run_count": len(s.get("runs", []))}
        for s in schedules
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_schedule(body: ScheduleCreate):
    cron = body.cron_expression.strip()
    if len(cron.split()) != 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cron ifadesi 5 alan içermelidir (örn: 0 2 * * *)",
        )

    schedule = {
        "id": str(uuid.uuid4())[:8],
        "name": body.name.strip(),
        "cron_expression": cron,
        "project_id": body.project_id,
        "feature_path": body.feature_path,
        "markers": body.markers,
        "browser": body.browser,
        "notify_on_fail": body.notify_on_fail,
        "notify_email": body.notify_email,
        "is_active": body.is_active,
        "created_at": datetime.now().isoformat(),
        "last_run_at": None,
        "runs": [],
    }

    with _store_lock:
        schedules = _load()
        schedules.append(schedule)
        _save(schedules)

    _register_with_apscheduler(schedule)
    return {"ok": True, "schedule": {k: v for k, v in schedule.items() if k != "runs"}}


@router.put("/{schedule_id}")
def update_schedule(schedule_id: str, body: ScheduleUpdate):
    updatable = (
        "name", "cron_expression", "is_active", "feature_path",
        "markers", "browser", "notify_on_fail", "notify_email",
    )
    with _store_lock:
        schedules = _load()
        for s in schedules:
            if s["id"] == schedule_id:
                for field in updatable:
                    value = getattr(body, field, None)
                    if value is not None:
                        s[field] = value
                _save(schedules)
                _register_with_apscheduler(s)
                return {"ok": True, "schedule": {k: v for k, v in s.items() if k != "runs"}}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule bulunamadı")


@router.delete("/{schedule_id}", status_code=status.HTTP_200_OK)
def delete_schedule(schedule_id: str):
    with _store_lock:
        schedules = _load()
        new_list = [s for s in schedules if s["id"] != schedule_id]
        if len(new_list) == len(schedules):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule bulunamadı",
            )
        _save(new_list)
    _unregister_from_apscheduler(schedule_id)
    return {"ok": True}


@router.post("/{schedule_id}/trigger")
def trigger_schedule(schedule_id: str):
    threading.Thread(target=_run_schedule, args=[schedule_id], daemon=True).start()
    return {"ok": True, "message": "Koşu başlatıldı"}


@router.get("/{schedule_id}/runs")
def get_schedule_runs(schedule_id: str):
    with _store_lock:
        schedules = _load()
    schedule = next((s for s in schedules if s["id"] == schedule_id), None)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule bulunamadı")
    return {"ok": True, "runs": schedule.get("runs", [])[:20]}
