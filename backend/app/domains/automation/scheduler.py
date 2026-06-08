"""In-process scheduler for cron-driven automation runs.

Mirrors app.domains.tspm.scheduler: an APScheduler BackgroundScheduler loads
active AutomationSchedule rows and fires a trigger="schedule" AutomationRun on
each cron cadence. The actual run execution reuses the same async starter
helpers as the HTTP layer (router._start_*_run) via asyncio.run from the
scheduler worker thread.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone as _tz
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler = None


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            _scheduler = BackgroundScheduler(timezone="UTC")
        except ImportError:
            logger.warning("APScheduler not installed, automation scheduler disabled")
            return None
    return _scheduler


def start_scheduler():
    s = get_scheduler()
    if s and not s.running:
        s.start()
        logger.info("Automation scheduler started")
        load_schedules_from_db()


def is_scheduler_running() -> bool:
    s = get_scheduler()
    return bool(s and s.running)


def shutdown_scheduler():
    s = get_scheduler()
    if s and s.running:
        s.shutdown(wait=False)
        logger.info("Automation scheduler shut down")


def is_valid_cron(cron_expression: str) -> bool:
    """5-alanlı cron ifadesini doğrula (croniter)."""
    try:
        from croniter import croniter
        return bool(croniter.is_valid(cron_expression)) and len(cron_expression.split()) == 5
    except Exception:
        return False


def compute_next_run(cron_expression: str) -> Optional[datetime]:
    try:
        from croniter import croniter
        c = croniter(cron_expression, datetime.now(_tz.utc))
        return c.get_next(datetime)
    except Exception:
        return None


def add_schedule_job(schedule_id: str, cron_expression: str):
    s = get_scheduler()
    if s is None:
        return
    parts = cron_expression.split()
    if len(parts) != 5:
        logger.warning("Automation schedule %s has invalid cron: %r", schedule_id, cron_expression)
        return
    s.add_job(
        _run_schedule_job, 'cron',
        id=f"automation:{schedule_id}",
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3], day_of_week=parts[4],
        args=[schedule_id],
        replace_existing=True,
    )


def remove_schedule_job(schedule_id: str):
    s = get_scheduler()
    if s is None:
        return
    try:
        s.remove_job(f"automation:{schedule_id}")
    except Exception as exc:
        logger.debug("automation remove_job(%s): %s", schedule_id, exc)


def load_schedules_from_db():
    """Startup'ta DB'deki aktif automation schedule'larını APScheduler'a yükler."""
    s = get_scheduler()
    if s is None:
        return
    try:
        from sqlalchemy import select

        from app.infra.database import SessionLocal
        from app.infra.models import AutomationSchedule
        with SessionLocal() as db:
            rows = list(
                db.scalars(select(AutomationSchedule).where(AutomationSchedule.is_active.is_(True)))
            )
            for sched in rows:
                add_schedule_job(sched.id, sched.cron_expression)
        logger.info("Loaded %d active automation schedules from DB", len(rows))
    except Exception as exc:
        logger.warning("Could not load automation schedules from DB: %s", exc)


def _run_schedule_job(schedule_id: str):
    """APScheduler tarafından çağrılan iş: schedule'dan bir automation run üretir.

    Run, HTTP katmanıyla aynı async başlatıcı helper'ları (router._start_*_run)
    kullanılarak çalıştırılır.
    """
    import asyncio

    try:
        from app.domains.automation import router as automation_router
        from app.domains.automation.brain import (
            AutomationBrainService,
            SqlAlchemyAutomationRunStore,
        )
        from app.domains.automation.schemas import AutomationRunCreate
        from app.infra.database import SessionLocal
        from app.infra.models import AutomationSchedule

        with SessionLocal() as db:
            sched = db.get(AutomationSchedule, schedule_id)
            if sched is None or not sched.is_active:
                return

            # Timestamps güncelle
            sched.last_run_at = datetime.now(_tz.utc)
            next_run = compute_next_run(sched.cron_expression)
            if next_run:
                sched.next_run_at = next_run
            db.commit()

            service = AutomationBrainService(SqlAlchemyAutomationRunStore(db))
            request = AutomationRunCreate(
                project_id=sched.project_id,
                kind=sched.kind,  # type: ignore[arg-type]
                name=f"Scheduled: {sched.name}",
                trigger="schedule",
                environment=sched.environment,
                device=sched.device,
                target=sched.target,
                execute_now=True,
                metadata={**(sched.run_metadata or {}), "schedule_id": sched.id},
            )
            run = service.create_run(request, created_by=sched.created_by)

            # Kind'a göre HTTP katmanındaki aynı async başlatıcıyı çağır
            kind = run.kind
            if kind == "web" and run.target:
                asyncio.run(automation_router._start_web_suite_run(service, run))
            elif kind == "api":
                asyncio.run(automation_router._start_api_test_run(service, run, db))
            elif kind == "mobile":
                asyncio.run(automation_router._start_mobile_farm_run(service, run))
            elif kind == "regression":
                asyncio.run(automation_router._start_regression_suggestion_run(service, run, db))
            elif kind == "llm":
                asyncio.run(automation_router._start_llm_agent_run(service, run))
            logger.info("Automation schedule %s triggered run %s (%s)", schedule_id, run.id, kind)
    except Exception as exc:
        logger.error("Automation schedule job %s failed: %s", schedule_id, exc)
