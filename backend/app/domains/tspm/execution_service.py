"""Execution-related service helpers for TSPM."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.audit.service import log_audit
from app.domains.tspm.models import (
    TspmExecution,
    TspmExecutionMetrics,
    TspmExecutionResult,
    TspmScenario,
)
from app.domains.tspm.schemas import (
    ExecutionCreate,
    ExecutionDetailOut,
    ExecutionOut,
    ExecutionResultOut,
    ExecutionStatsOut,
    ExecutionTrendsOut,
    FlakyTestOut,
    TrendDataPoint,
)


def list_executions_for_project(
    db: Session,
    project_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
    platform: str | None = None,
) -> list[ExecutionOut]:
    where_clauses = [TspmExecution.project_id == project_id]
    if platform == "desktop":
        where_clauses.append(TspmExecution.platform.is_(None))
    elif platform in ("ios", "android"):
        where_clauses.append(TspmExecution.platform == platform)

    executions = list(
        db.scalars(
            select(TspmExecution)
            .where(*where_clauses)
            .order_by(TspmExecution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )
    if not executions:
        return []

    exec_ids = [execution.id for execution in executions]
    from sqlalchemy import case as sa_case

    stats_rows = db.execute(
        select(
            TspmExecutionResult.execution_id,
            func.count().label("total"),
            func.sum(sa_case((TspmExecutionResult.status == "passed", 1), else_=0)).label("passed"),
            func.sum(sa_case((TspmExecutionResult.status == "failed", 1), else_=0)).label("failed"),
        )
        .where(TspmExecutionResult.execution_id.in_(exec_ids))
        .group_by(TspmExecutionResult.execution_id)
    ).all()
    stats = {
        row.execution_id: (row.total, row.passed, row.failed)
        for row in stats_rows
    }

    return [
        ExecutionOut(
            id=execution.id,
            name=execution.name,
            status=execution.status,
            created_at=execution.created_at,
            scenario_total=stats.get(execution.id, (0, 0, 0))[0],
            passed_count=stats.get(execution.id, (0, 0, 0))[1],
            failed_count=stats.get(execution.id, (0, 0, 0))[2],
            platform=execution.platform,
            device_name=execution.device_name,
            app_upload_id=execution.app_upload_id,
        )
        for execution in executions
    ]


def create_execution_for_project(
    db: Session,
    project_id: str,
    body: ExecutionCreate,
    *,
    actor_user_id: str,
) -> ExecutionOut:
    execution = TspmExecution(
        project_id=project_id,
        name=body.name,
        status="running",
        platform=body.platform,
        device_name=body.device_name,
        app_upload_id=body.app_upload_id,
    )
    db.add(execution)
    db.flush()

    for scenario_id in body.scenario_ids:
        db.add(
            TspmExecutionResult(
                execution_id=execution.id,
                scenario_id=scenario_id,
                status="pending",
            )
        )

    db.add(
        TspmExecutionMetrics(
            project_id=project_id,
            execution_id=execution.id,
            total=len(body.scenario_ids),
            passed=0,
            failed=0,
            skipped=0,
            pass_rate=0.0,
        )
    )
    db.commit()
    db.refresh(execution)

    log_audit(
        db,
        actor_user_id=actor_user_id,
        action="execution.create",
        resource_type="execution",
        resource_id=execution.id,
        payload={
            "name": execution.name,
            "scenario_count": len(body.scenario_ids),
            "project_id": project_id,
        },
        ip=None,
    )
    db.commit()

    return ExecutionOut(
        id=execution.id,
        name=execution.name,
        status=execution.status,
        created_at=execution.created_at,
        scenario_total=len(body.scenario_ids),
        passed_count=0,
        failed_count=0,
        platform=execution.platform,
        device_name=execution.device_name,
        app_upload_id=execution.app_upload_id,
    )


def compare_executions_for_project(
    db: Session,
    project_id: str,
    run1: str,
    run2: str,
) -> dict:
    execution_one = db.get(TspmExecution, run1)
    execution_two = db.get(TspmExecution, run2)
    if (
        not execution_one
        or not execution_two
        or execution_one.project_id != project_id
        or execution_two.project_id != project_id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")

    results1 = {
        result.scenario_id: result.status
        for result in db.scalars(
            select(TspmExecutionResult).where(TspmExecutionResult.execution_id == run1)
        )
    }
    results2 = {
        result.scenario_id: result.status
        for result in db.scalars(
            select(TspmExecutionResult).where(TspmExecutionResult.execution_id == run2)
        )
    }

    comparison = []
    for scenario_id in set(results1.keys()) | set(results2.keys()):
        scenario = db.get(TspmScenario, scenario_id)
        run1_status = results1.get(scenario_id, "—")
        run2_status = results2.get(scenario_id, "—")
        comparison.append(
            {
                "scenario_id": scenario_id,
                "scenario_title": scenario.title if scenario else scenario_id,
                "run1_status": run1_status,
                "run2_status": run2_status,
                "changed": run1_status != run2_status,
            }
        )

    return {
        "run1": {
            "id": execution_one.id,
            "name": execution_one.name,
            "created_at": str(execution_one.created_at),
        },
        "run2": {
            "id": execution_two.id,
            "name": execution_two.name,
            "created_at": str(execution_two.created_at),
        },
        "scenarios": sorted(comparison, key=lambda item: item["changed"], reverse=True),
    }


def get_execution_detail_for_project(
    db: Session,
    project_id: str,
    run_id: str,
) -> ExecutionDetailOut:
    execution = db.get(TspmExecution, run_id)
    if execution is None or execution.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")

    results = list(
        db.scalars(select(TspmExecutionResult).where(TspmExecutionResult.execution_id == run_id))
    )
    result_out = []
    for result in results:
        scenario = db.get(TspmScenario, result.scenario_id)
        result_out.append(
            ExecutionResultOut(
                id=result.id,
                scenario_id=result.scenario_id,
                scenario_title=scenario.title if scenario else "",
                status=result.status,
                note=result.note,
            )
        )

    return ExecutionDetailOut(
        id=execution.id,
        name=execution.name,
        status=execution.status,
        created_at=execution.created_at,
        results=result_out,
        platform=execution.platform,
        device_name=execution.device_name,
        app_upload_id=execution.app_upload_id,
    )


def update_execution_result_status(db: Session, run_id: str, result_id: str, status_value: str) -> dict:
    result = db.get(TspmExecutionResult, result_id)
    if result is None or result.execution_id != run_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sonuç bulunamadı")
    result.status = status_value
    db.commit()
    return {"ok": True}


def rerun_execution_for_project(db: Session, project_id: str, run_id: str) -> ExecutionOut:
    old_execution = db.get(TspmExecution, run_id)
    if old_execution is None or old_execution.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")

    old_results = list(
        db.scalars(select(TspmExecutionResult).where(TspmExecutionResult.execution_id == run_id))
    )
    new_execution = TspmExecution(
        project_id=project_id,
        name=f"{old_execution.name} (re-run)",
        status="running",
        platform=old_execution.platform,
        device_name=old_execution.device_name,
        app_upload_id=old_execution.app_upload_id,
    )
    db.add(new_execution)
    db.flush()

    for result in old_results:
        db.add(
            TspmExecutionResult(
                execution_id=new_execution.id,
                scenario_id=result.scenario_id,
                status="pending",
            )
        )

    db.commit()
    db.refresh(new_execution)
    return ExecutionOut(
        id=new_execution.id,
        name=new_execution.name,
        status=new_execution.status,
        created_at=new_execution.created_at,
        scenario_total=len(old_results),
        passed_count=0,
        failed_count=0,
        platform=new_execution.platform,
        device_name=new_execution.device_name,
        app_upload_id=new_execution.app_upload_id,
    )


def build_execution_trends_for_project(
    db: Session,
    project_id: str,
    *,
    days: int = 30,
) -> ExecutionTrendsOut:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    metrics = list(
        db.scalars(
            select(TspmExecutionMetrics)
            .where(
                TspmExecutionMetrics.project_id == project_id,
                TspmExecutionMetrics.executed_at >= since,
            )
            .order_by(TspmExecutionMetrics.executed_at)
        )
    )
    by_date: dict[str, list[TspmExecutionMetrics]] = defaultdict(list)
    for metric in metrics:
        by_date[metric.executed_at.strftime("%Y-%m-%d")].append(metric)

    data_points = []
    for date_str in sorted(by_date):
        day = by_date[date_str]
        total = sum(metric.total for metric in day)
        passed = sum(metric.passed for metric in day)
        failed = sum(metric.failed for metric in day)
        rate = round(passed / total * 100, 1) if total > 0 else 0.0
        data_points.append(
            TrendDataPoint(
                date=date_str,
                total=total,
                passed=passed,
                failed=failed,
                pass_rate=rate,
            )
        )

    return ExecutionTrendsOut(days=days, data_points=data_points)


def build_execution_stats_for_project(db: Session, project_id: str) -> ExecutionStatsOut:
    total_execs = db.scalar(select(func.count()).where(TspmExecution.project_id == project_id)) or 0
    total_scenarios = db.scalar(
        select(func.count()).where(
            TspmExecutionResult.execution_id.in_(
                select(TspmExecution.id).where(TspmExecution.project_id == project_id)
            )
        )
    ) or 0
    metrics = list(
        db.scalars(select(TspmExecutionMetrics).where(TspmExecutionMetrics.project_id == project_id))
    )
    avg_rate = round(sum(metric.pass_rate for metric in metrics) / len(metrics), 1) if metrics else 0.0
    last_exec = db.scalar(
        select(TspmExecution)
        .where(TspmExecution.project_id == project_id)
        .order_by(TspmExecution.created_at.desc())
    )
    return ExecutionStatsOut(
        total_executions=total_execs,
        total_scenarios_run=total_scenarios,
        avg_pass_rate=avg_rate,
        last_execution_at=last_exec.created_at if last_exec else None,
    )


def get_flaky_tests_for_project(db: Session, project_id: str) -> list[FlakyTestOut]:
    recent_execs = list(
        db.scalars(
            select(TspmExecution)
            .where(TspmExecution.project_id == project_id)
            .order_by(TspmExecution.created_at.desc())
            .limit(10)
        )
    )
    if not recent_execs:
        return []

    exec_ids = [execution.id for execution in recent_execs]
    results = list(
        db.scalars(
            select(TspmExecutionResult).where(TspmExecutionResult.execution_id.in_(exec_ids))
        )
    )
    exec_order = {execution.id: i for i, execution in enumerate(recent_execs)}
    scenario_results: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for result in results:
        if result.status in ("passed", "failed"):
            scenario_results[result.scenario_id].append((exec_order[result.execution_id], result.status))

    flaky: list[FlakyTestOut] = []
    for scenario_id, statuses in scenario_results.items():
        statuses.sort(key=lambda item: item[0])
        ordered = [item[1] for item in statuses]
        flip_count = sum(1 for i in range(1, len(ordered)) if ordered[i] != ordered[i - 1])
        if flip_count > 0:
            scenario = db.get(TspmScenario, scenario_id)
            flaky.append(
                FlakyTestOut(
                    scenario_id=scenario_id,
                    scenario_title=scenario.title if scenario else "",
                    flip_count=flip_count,
                    last_results=ordered[-10:],
                )
            )

    flaky.sort(key=lambda item: item.flip_count, reverse=True)
    return flaky
