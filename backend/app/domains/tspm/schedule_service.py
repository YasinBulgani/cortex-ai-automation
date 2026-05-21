"""Schedule-related service helpers for TSPM."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tspm.models import (
    TspmExecution,
    TspmExecutionResult,
    TspmRegressionSet,
    TspmSchedule,
    utcnow,
)
from app.domains.tspm.schemas import ExecutionOut, ScheduleCreate, ScheduleUpdate
from app.domains.tspm.scheduler import (
    _run_schedule_job,
    add_schedule_job,
    compute_next_run,
    remove_schedule_job,
)


logger = logging.getLogger(__name__)


def create_schedule_for_project(
    db: Session,
    project_id: str,
    body: ScheduleCreate,
    *,
    actor_user_id: str,
) -> TspmSchedule:
    sched = TspmSchedule(
        project_id=project_id,
        name=body.name,
        cron_expression=body.cron_expression,
        regression_set_id=body.regression_set_id,
        scenario_ids=body.scenario_ids,
        is_active=body.is_active,
        created_by=actor_user_id,
        platform=body.platform,
        device_name=body.device_name,
    )
    db.add(sched)
    try:
        db.flush()
        if sched.is_active:
            next_run = compute_next_run(sched.cron_expression)
            if next_run:
                sched.next_run_at = next_run
        db.commit()
    except Exception:
        db.rollback()
        raise

    if sched.is_active:
        try:
            add_schedule_job(sched.id, sched.cron_expression, _run_schedule_job, args=[sched.id])
        except Exception as exc:
            logger.warning("Scheduler job eklenemedi: %s", exc)

    db.refresh(sched)
    return sched


def list_schedules_for_project(
    db: Session,
    project_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[TspmSchedule]:
    return list(
        db.scalars(
            select(TspmSchedule)
            .where(TspmSchedule.project_id == project_id)
            .order_by(TspmSchedule.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )


def update_schedule_for_project(
    db: Session,
    project_id: str,
    schedule_id: str,
    body: ScheduleUpdate,
) -> TspmSchedule:
    sched = get_schedule_or_404(db, project_id, schedule_id)
    if body.name is not None:
        sched.name = body.name
    if body.cron_expression is not None:
        sched.cron_expression = body.cron_expression
        sched.next_run_at = compute_next_run(sched.cron_expression) if sched.is_active else None
    if body.regression_set_id is not None:
        sched.regression_set_id = body.regression_set_id
    if body.scenario_ids is not None:
        sched.scenario_ids = body.scenario_ids
    if body.is_active is not None:
        sched.is_active = body.is_active
        sched.next_run_at = compute_next_run(sched.cron_expression) if sched.is_active else None
    if body.platform is not None:
        sched.platform = body.platform
    if body.device_name is not None:
        sched.device_name = body.device_name

    db.commit()
    db.refresh(sched)

    remove_schedule_job(sched.id)
    if sched.is_active:
        add_schedule_job(sched.id, sched.cron_expression, _run_schedule_job, args=[sched.id])
    return sched


def delete_schedule_for_project(db: Session, project_id: str, schedule_id: str) -> None:
    sched = get_schedule_or_404(db, project_id, schedule_id)
    remove_schedule_job(sched.id)
    db.delete(sched)
    db.commit()


def trigger_schedule_for_project(
    db: Session,
    project_id: str,
    schedule_id: str,
) -> ExecutionOut:
    sched = get_schedule_or_404(db, project_id, schedule_id)
    scenario_ids = list(sched.scenario_ids or [])
    if not scenario_ids and sched.regression_set_id:
        regression_set = db.get(TspmRegressionSet, sched.regression_set_id)
        if regression_set:
            scenario_ids = list(regression_set.scenario_ids or [])
    if not scenario_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Zamanlamada senaryo bulunamadı")

    execution = TspmExecution(
        project_id=project_id,
        name=f"Scheduled: {sched.name}",
        status="running",
    )
    db.add(execution)
    db.flush()
    for scenario_id in scenario_ids:
        db.add(
            TspmExecutionResult(
                execution_id=execution.id,
                scenario_id=scenario_id,
                status="pending",
            )
        )
    sched.last_run_at = utcnow()
    sched.next_run_at = compute_next_run(sched.cron_expression) if sched.is_active else sched.next_run_at
    db.commit()
    db.refresh(execution)
    return ExecutionOut(
        id=execution.id,
        name=execution.name,
        status=execution.status,
        created_at=execution.created_at,
        scenario_total=len(scenario_ids),
        passed_count=0,
        failed_count=0,
    )


def get_schedule_or_404(db: Session, project_id: str, schedule_id: str) -> TspmSchedule:
    sched = db.get(TspmSchedule, schedule_id)
    if sched is None or sched.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zamanlama bulunamadı")
    return sched
