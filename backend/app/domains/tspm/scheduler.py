"""Lightweight in-process scheduler for scheduled test executions."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
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
            logger.warning("APScheduler not installed, scheduler disabled")
            return None
    return _scheduler


def start_scheduler():
    s = get_scheduler()
    if s and not s.running:
        s.start()
        logger.info("Scheduler started")
        load_schedules_from_db()


def is_scheduler_running() -> bool:
    """Return True when the TSPM scheduler is available and currently running."""
    s = get_scheduler()
    return bool(s and s.running)


def shutdown_scheduler():
    s = get_scheduler()
    if s and s.running:
        s.shutdown(wait=False)
        logger.info("Scheduler shut down")


def compute_next_run(cron_expression: str) -> Optional[datetime]:
    try:
        from croniter import croniter
        c = croniter(cron_expression, datetime.now(timezone.utc))
        return c.get_next(datetime)
    except Exception:
        return None


def add_schedule_job(schedule_id: str, cron_expression: str, func, args=None):
    s = get_scheduler()
    if s is None:
        return
    parts = cron_expression.split()
    if len(parts) == 5:
        s.add_job(
            func, 'cron',
            id=schedule_id,
            minute=parts[0], hour=parts[1],
            day=parts[2], month=parts[3], day_of_week=parts[4],
            args=args or [],
            replace_existing=True,
        )


def remove_schedule_job(schedule_id: str):
    s = get_scheduler()
    if s is None:
        return
    try:
        s.remove_job(schedule_id)
    except Exception as exc:
        logger.debug("remove_job(%s): %s", schedule_id, exc)


def load_schedules_from_db():
    """Startup'ta DB'deki aktif schedule'ları APScheduler'a yükler."""
    s = get_scheduler()
    if s is None:
        return
    try:
        from app.infra.database import SessionLocal
        from app.domains.tspm.models import TspmSchedule
        from sqlalchemy import select
        with SessionLocal() as db:
            rows = list(db.scalars(select(TspmSchedule).where(TspmSchedule.is_active == True)))
            for sched in rows:
                add_schedule_job(
                    sched.id,
                    sched.cron_expression,
                    _run_schedule_job,
                    args=[sched.id],
                )
        logger.info("Loaded %d active schedules from DB", len(rows))
    except Exception as exc:
        logger.warning("Could not load schedules from DB: %s", exc)


def _run_schedule_job(schedule_id: str):
    """APScheduler tarafından çağrılan iş: ilgili schedule'ı tetikler.

    Mobil schedule (platform != None) → launch_mobile_run() çağrısı.
    Masaüstü schedule → TspmExecution kaydı oluşturur.
    """
    try:
        from app.infra.database import SessionLocal
        from app.domains.tspm.models import TspmSchedule, TspmExecution, TspmExecutionResult, TspmRegressionSet
        from datetime import datetime, timezone

        with SessionLocal() as db:
            sched = db.get(TspmSchedule, schedule_id)
            if sched is None or not sched.is_active:
                return
            scenario_ids = list(sched.scenario_ids or [])
            if not scenario_ids and sched.regression_set_id:
                rs = db.get(TspmRegressionSet, sched.regression_set_id)
                if rs:
                    scenario_ids = list(rs.scenario_ids or [])
            if not scenario_ids:
                logger.warning("Schedule %s has no scenarios", schedule_id)
                return

            # Timestamps güncelle (commit sonrası çakışmasın diye burada yapılır)
            sched.last_run_at = datetime.now(timezone.utc)
            next_run = compute_next_run(sched.cron_expression)
            if next_run:
                sched.next_run_at = next_run

            if sched.platform and sched.device_name:
                # ── Mobil koşum: Visium Farm ──────────────────────────────
                db.commit()  # timestamps'i kaydet
                logger.info("Schedule %s launching mobile run on %s (%s)",
                            schedule_id, sched.device_name, sched.platform)
                try:
                    from app.domains.tspm.test_runner_service import launch_mobile_run
                    launch_mobile_run(
                        project_id=sched.project_id,
                        device_names=[sched.device_name],
                        scenario_ids=scenario_ids,
                    )
                except Exception as mob_exc:
                    logger.error("Mobile launch failed for schedule %s: %s", schedule_id, mob_exc)
            else:
                # ── Masaüstü koşum ───────────────────────────────────────
                ex = TspmExecution(
                    project_id=sched.project_id,
                    name=f"Scheduled: {sched.name}",
                    status="running",
                )
                db.add(ex)
                db.flush()
                for sid in scenario_ids:
                    db.add(TspmExecutionResult(execution_id=ex.id, scenario_id=sid, status="pending"))
                db.commit()
                logger.info("Schedule %s triggered execution %s", schedule_id, ex.id)
    except Exception as exc:
        logger.error("Schedule job %s failed: %s", schedule_id, exc)
