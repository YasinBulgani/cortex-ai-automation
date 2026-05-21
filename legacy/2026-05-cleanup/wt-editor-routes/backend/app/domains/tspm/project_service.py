"""Project and dashboard service helpers for TSPM."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.auth.permissions import Permission
from app.domains.tspm.models import (
    TspmApproval,
    TspmExecution,
    TspmExecutionMetrics,
    TspmExecutionResult,
    TspmImport,
    TspmProject,
    TspmProjectMember,
    TspmScenario,
)
from app.domains.tspm.schemas import (
    DashboardStats,
    GlobalDashboardActivity,
    GlobalDashboardOut,
    GlobalDashboardProjectRow,
    ProjectCreate,
)
from app.infra.models import AuditEvent, User


def list_projects_for_user(db: Session, user: User) -> list[TspmProject]:
    """Return projects visible to the current user."""
    user_perms = {rp.permission for role in user.roles for rp in role.permissions}
    if Permission.ADMIN_FULL in user_perms:
        stmt = select(TspmProject).order_by(TspmProject.created_at.desc())
    else:
        stmt = (
            select(TspmProject)
            .join(TspmProjectMember, TspmProjectMember.project_id == TspmProject.id)
            .where(TspmProjectMember.user_id == user.id)
            .order_by(TspmProject.created_at.desc())
        )
    return list(db.scalars(stmt))


def create_project_for_user(db: Session, body: ProjectCreate, user: User) -> TspmProject:
    """Create a project and add the creator as admin member."""
    project = TspmProject(name=body.name, description=body.description)
    db.add(project)
    db.flush()
    db.add(TspmProjectMember(project_id=project.id, user_id=user.id, role="admin"))
    db.commit()
    db.refresh(project)
    return project


def build_project_dashboard(db: Session, project_id: str) -> DashboardStats:
    """Build dashboard stats for a single project."""
    scenario_count = db.scalar(select(func.count()).where(TspmScenario.project_id == project_id)) or 0
    pending_approvals = db.scalar(
        select(func.count()).where(
            TspmApproval.project_id == project_id,
            TspmApproval.status == "pending",
        )
    ) or 0
    import_count = db.scalar(select(func.count()).where(TspmImport.project_id == project_id)) or 0
    execution_count = db.scalar(select(func.count()).where(TspmExecution.project_id == project_id)) or 0

    latest_exec = db.scalar(
        select(TspmExecution)
        .where(TspmExecution.project_id == project_id)
        .order_by(TspmExecution.created_at.desc())
    )

    pass_rate = None
    if latest_exec:
        total = db.scalar(select(func.count()).where(TspmExecutionResult.execution_id == latest_exec.id)) or 0
        passed = db.scalar(
            select(func.count()).where(
                TspmExecutionResult.execution_id == latest_exec.id,
                TspmExecutionResult.status == "passed",
            )
        ) or 0
        if total > 0:
            pass_rate = round(passed / total * 100, 1)

    return DashboardStats(
        scenario_count=scenario_count,
        pending_approvals=pending_approvals,
        import_count=import_count,
        ai_run_pending=0,
        execution_count=execution_count,
        latest_run_pass_rate=pass_rate,
    )


def build_global_dashboard(db: Session, user: User) -> GlobalDashboardOut:
    """Build the platform-wide dashboard."""
    user_perms = {rp.permission for role in user.roles for rp in role.permissions}
    is_admin = Permission.ADMIN_FULL in user_perms
    if is_admin:
        accessible_project_ids = None
    else:
        accessible_project_ids = list(
            db.scalars(
                select(TspmProjectMember.project_id).where(TspmProjectMember.user_id == user.id)
            )
        )

    def _project_filter(column):
        if accessible_project_ids is None:
            return []
        return [column.in_(accessible_project_ids)]

    total_projects = db.scalar(
        select(func.count()).select_from(TspmProject).where(*_project_filter(TspmProject.id))
    ) or 0
    total_scenarios = db.scalar(
        select(func.count()).select_from(TspmScenario).where(*_project_filter(TspmScenario.project_id))
    ) or 0
    active_execs = db.scalar(
        select(func.count()).where(
            TspmExecution.status == "running",
            *_project_filter(TspmExecution.project_id),
        )
    ) or 0
    pending_approvals = db.scalar(
        select(func.count()).where(
            TspmApproval.status == "pending",
            *_project_filter(TspmApproval.project_id),
        )
    ) or 0

    all_metrics = list(
        db.scalars(
            select(TspmExecutionMetrics)
            .where(*_project_filter(TspmExecutionMetrics.project_id))
            .order_by(TspmExecutionMetrics.executed_at.desc())
            .limit(100)
        )
    )
    overall_rate = round(sum(metric.pass_rate for metric in all_metrics) / len(all_metrics), 1) if all_metrics else 0.0

    day_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    weekly_metrics = list(
        db.scalars(
            select(TspmExecutionMetrics).where(
                TspmExecutionMetrics.executed_at >= week_start,
                *_project_filter(TspmExecutionMetrics.project_id),
            )
        )
    )
    day_buckets: dict[int, tuple[int, int]] = {day: (0, 0) for day in range(7)}
    for metric in weekly_metrics:
        ts = metric.executed_at.replace(tzinfo=timezone.utc) if metric.executed_at.tzinfo is None else metric.executed_at
        days_ago = (now.date() - ts.date()).days
        if 0 <= days_ago <= 6:
            slot = 6 - days_ago
            runs, passed = day_buckets[slot]
            day_buckets[slot] = (runs + metric.total, passed + metric.passed)

    weekly = []
    for i in range(7):
        day = now - timedelta(days=6 - i)
        runs, passed = day_buckets[i]
        weekly.append({"day": day_names[day.weekday()], "runs": runs, "passed": passed})

    top_projects = list(
        db.scalars(
            select(TspmProject)
            .where(*_project_filter(TspmProject.id))
            .order_by(TspmProject.created_at.desc())
            .limit(5)
        )
    )
    top_project_ids = [project.id for project in top_projects]

    sc_by_project: dict[str, int] = {}
    latest_exec_by_project: dict[str, TspmExecution] = {}
    result_stats: dict[str, tuple[int, int]] = {}
    if top_project_ids:
        sc_rows = db.execute(
            select(TspmScenario.project_id, func.count().label("cnt"))
            .where(TspmScenario.project_id.in_(top_project_ids))
            .group_by(TspmScenario.project_id)
        ).all()
        sc_by_project = {row.project_id: row.cnt for row in sc_rows}

        latest_exec_subq = (
            select(
                TspmExecution.project_id,
                func.max(TspmExecution.created_at).label("max_ts"),
            )
            .where(TspmExecution.project_id.in_(top_project_ids))
            .group_by(TspmExecution.project_id)
            .subquery()
        )
        latest_execs = list(
            db.scalars(
                select(TspmExecution).join(
                    latest_exec_subq,
                    (TspmExecution.project_id == latest_exec_subq.c.project_id)
                    & (TspmExecution.created_at == latest_exec_subq.c.max_ts),
                )
            )
        )
        latest_exec_by_project = {execution.project_id: execution for execution in latest_execs}

        exec_ids = [execution.id for execution in latest_execs]
        if exec_ids:
            from sqlalchemy import case as sa_case

            result_stats_rows = db.execute(
                select(
                    TspmExecutionResult.execution_id,
                    func.count().label("total"),
                    func.sum(sa_case((TspmExecutionResult.status == "passed", 1), else_=0)).label("passed"),
                )
                .where(TspmExecutionResult.execution_id.in_(exec_ids))
                .group_by(TspmExecutionResult.execution_id)
            ).all()
            result_stats = {
                row.execution_id: (row.total, row.passed)
                for row in result_stats_rows
            }

    projects_rows: list[GlobalDashboardProjectRow] = []
    for project in top_projects:
        scenario_count = sc_by_project.get(project.id, 0)
        last_exec = latest_exec_by_project.get(project.id)
        pass_rate = None
        last_run_str = None
        project_status = "active"
        if last_exec:
            total, passed = result_stats.get(last_exec.id, (0, 0))
            pass_rate = round(passed / total * 100, 1) if total > 0 else None
            if pass_rate is not None:
                project_status = "critical" if pass_rate < 70 else ("warning" if pass_rate < 85 else "active")
            last_run_str = _time_ago(now, last_exec.created_at)

        projects_rows.append(
            GlobalDashboardProjectRow(
                id=project.id,
                name=project.name,
                scenario_count=scenario_count,
                last_run=last_run_str,
                pass_rate=pass_rate,
                status=project_status,
            )
        )

    audit_events = list(db.scalars(select(AuditEvent).order_by(AuditEvent.ts.desc()).limit(10)))
    actor_ids = list({event.actor_user_id for event in audit_events if event.actor_user_id})
    actor_map: dict[str, str] = {}
    if actor_ids:
        actor_rows = list(db.scalars(select(User).where(User.id.in_(actor_ids))))
        actor_map = {row.id: (row.full_name or row.email) for row in actor_rows}

    activities: list[GlobalDashboardActivity] = []
    for event in audit_events:
        actor_name = actor_map.get(event.actor_user_id, "Sistem") if event.actor_user_id else "Sistem"
        activities.append(
            GlobalDashboardActivity(
                actor=actor_name,
                action=event.action,
                time=_time_ago(now, event.ts),
                resource_type=event.resource_type,
                resource_id=event.resource_id,
            )
        )

    return GlobalDashboardOut(
        total_projects=total_projects,
        total_scenarios=total_scenarios,
        active_executions=active_execs,
        pending_approvals=pending_approvals,
        overall_pass_rate=overall_rate,
        projects=projects_rows,
        activities=activities,
        weekly=weekly,
    )


def _time_ago(now: datetime, value: datetime) -> str:
    diff = now - (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value)
    if diff.days > 0:
        return f"{diff.days} gün önce"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600} saat önce"
    return f"{diff.seconds // 60} dk önce"
