"""Subscription service — read/write subscriptions, compute usage, check limits.

Usage counters are computed on-demand by aggregating from authoritative
sources (users, projects, scenarios, executions, usage events). The
billing_subscriptions table only stores plan state, not usage totals,
to avoid drift.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domains.billing.models import Subscription, UsageEvent
from app.domains.billing.plans import (
    DEFAULT_PLAN_CODE,
    PLAN_CATALOG,
    Plan,
    get_plan,
    is_unlimited,
    within_limit,
)

logger = logging.getLogger(__name__)


@dataclass
class UsageSnapshot:
    """Frontend-facing usage shape (matches apps/web billing page)."""

    plan: str
    plan_expires_at: Optional[str]
    scenario_count: int
    scenario_limit: int
    run_count_month: int
    run_limit_month: int
    ai_token_spend_usd: float
    ai_token_limit_usd: float
    team_size: int
    team_limit: int
    storage_mb: int
    storage_limit_mb: int
    project_count: int
    project_limit: int

    def to_dict(self) -> dict:
        return {
            "plan": self.plan,
            "plan_expires_at": self.plan_expires_at,
            "scenario_count": self.scenario_count,
            "scenario_limit": self.scenario_limit,
            "run_count_month": self.run_count_month,
            "run_limit_month": self.run_limit_month,
            "ai_token_spend_usd": round(self.ai_token_spend_usd, 4),
            "ai_token_limit_usd": self.ai_token_limit_usd,
            "team_size": self.team_size,
            "team_limit": self.team_limit,
            "storage_mb": self.storage_mb,
            "storage_limit_mb": self.storage_limit_mb,
            "project_count": self.project_count,
            "project_limit": self.project_limit,
        }


# ── Subscription lifecycle ──────────────────────────────────────────────────


def get_or_create_subscription(db: Session, tenant_id: str) -> Subscription:
    """Return tenant's subscription, creating a free-tier row if missing."""
    sub = db.execute(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if sub is not None:
        return sub

    sub = Subscription(tenant_id=tenant_id, plan_code=DEFAULT_PLAN_CODE, status="active")
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def set_plan(
    db: Session,
    tenant_id: str,
    plan_code: str,
    *,
    period_end: Optional[datetime] = None,
    external_subscription_id: Optional[str] = None,
) -> Subscription:
    if plan_code not in PLAN_CATALOG:
        raise ValueError(f"Bilinmeyen plan kodu: {plan_code}")

    sub = get_or_create_subscription(db, tenant_id)
    sub.plan_code = plan_code
    sub.status = "active"
    sub.current_period_start = datetime.now(timezone.utc)
    if period_end is not None:
        sub.current_period_end = period_end
    if external_subscription_id is not None:
        sub.external_subscription_id = external_subscription_id
    db.commit()
    db.refresh(sub)
    return sub


# ── Usage events ────────────────────────────────────────────────────────────


def record_usage(
    db: Session,
    tenant_id: str,
    kind: str,
    amount: float = 1.0,
    *,
    actor_user_id: Optional[str] = None,
    meta: Optional[str] = None,
) -> None:
    """Append a usage event. Caller commits."""
    db.add(
        UsageEvent(
            tenant_id=tenant_id,
            kind=kind,
            amount=amount,
            actor_user_id=actor_user_id,
            meta=meta[:2000] if meta else None,
        )
    )


def _start_of_month() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# ── Usage aggregation ───────────────────────────────────────────────────────


def _count_safe(db: Session, sql_select) -> int:
    """Run a count query that may target a non-existent table. Return 0 on error."""
    try:
        result = db.execute(sql_select).scalar_one_or_none()
        return int(result or 0)
    except SQLAlchemyError:
        db.rollback()
        return 0


def _sum_usage(db: Session, tenant_id: str, kind: str, since: datetime) -> float:
    try:
        result = db.execute(
            select(func.coalesce(func.sum(UsageEvent.amount), 0)).where(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.kind == kind,
                UsageEvent.occurred_at >= since,
            )
        ).scalar_one_or_none()
        return float(result or 0)
    except SQLAlchemyError:
        db.rollback()
        return 0.0


def compute_usage_snapshot(db: Session, tenant_id: str) -> UsageSnapshot:
    """Aggregate current usage for a tenant."""
    sub = get_or_create_subscription(db, tenant_id)
    plan: Plan = get_plan(sub.plan_code)
    L = plan.limits

    # Lazy imports — these models may not be loaded in every test context
    from app.infra.models import User

    team_size = _count_safe(
        db,
        select(func.count(User.id)).where(User.tenant_id == tenant_id),
    )

    # tspm tables are present in production; fall back to 0 if missing.
    try:
        from app.domains.tspm.models import (
            TspmProject,
            TspmScenario,
            TspmExecution,
            TspmProjectMember,
        )

        # Project count: distinct projects whose members belong to the tenant.
        member_user_ids = (
            select(User.id).where(User.tenant_id == tenant_id).scalar_subquery()
        )
        project_count = _count_safe(
            db,
            select(func.count(func.distinct(TspmProjectMember.project_id))).where(
                TspmProjectMember.user_id.in_(member_user_ids)
            ),
        )
        scenario_count = _count_safe(
            db,
            select(func.count(TspmScenario.id))
            .join(TspmProjectMember, TspmProjectMember.project_id == TspmScenario.project_id)
            .where(TspmProjectMember.user_id.in_(member_user_ids)),
        )
        run_count_month = _count_safe(
            db,
            select(func.count(TspmExecution.id))
            .join(TspmProjectMember, TspmProjectMember.project_id == TspmExecution.project_id)
            .where(
                TspmProjectMember.user_id.in_(member_user_ids),
                TspmExecution.created_at >= _start_of_month(),
            ),
        )
    except Exception as exc:  # pragma: no cover — defensive for partial schemas
        logger.debug("tspm usage aggregation skipped: %s", exc)
        project_count = scenario_count = run_count_month = 0

    ai_token_spend_usd = _sum_usage(
        db, tenant_id, "ai.token_spend", _start_of_month()
    )
    storage_mb = int(_sum_usage(db, tenant_id, "storage.delta_mb", datetime.fromtimestamp(0, tz=timezone.utc)))

    return UsageSnapshot(
        plan=plan.code,
        plan_expires_at=sub.current_period_end.isoformat() if sub.current_period_end else None,
        scenario_count=scenario_count,
        scenario_limit=L.scenario_count,
        run_count_month=run_count_month,
        run_limit_month=L.run_count_month,
        ai_token_spend_usd=ai_token_spend_usd,
        ai_token_limit_usd=L.ai_token_spend_usd,
        team_size=team_size,
        team_limit=L.team_size,
        storage_mb=max(0, storage_mb),
        storage_limit_mb=L.storage_mb,
        project_count=project_count,
        project_limit=L.project_count,
    )


# ── Limit checks ────────────────────────────────────────────────────────────


@dataclass
class LimitCheck:
    allowed: bool
    used: float
    limit: float
    reason: Optional[str] = None


def check_limit(
    snapshot: UsageSnapshot,
    metric: str,
    *,
    delta: float = 1.0,
) -> LimitCheck:
    """Verify ``snapshot.{metric}`` + delta is within plan limit."""
    mapping = {
        "project_count": (snapshot.project_count, snapshot.project_limit),
        "scenario_count": (snapshot.scenario_count, snapshot.scenario_limit),
        "run_count_month": (snapshot.run_count_month, snapshot.run_limit_month),
        "team_size": (snapshot.team_size, snapshot.team_limit),
        "storage_mb": (snapshot.storage_mb, snapshot.storage_limit_mb),
        "ai_token_spend_usd": (snapshot.ai_token_spend_usd, snapshot.ai_token_limit_usd),
    }
    if metric not in mapping:
        raise ValueError(f"Bilinmeyen metric: {metric}")
    used, limit = mapping[metric]
    if is_unlimited(limit):
        return LimitCheck(True, used, limit)
    projected = used + delta
    if projected <= limit:
        return LimitCheck(True, used, limit)
    return LimitCheck(
        False,
        used,
        limit,
        reason=f"Plan limiti aşıldı: {metric} {projected:.0f}/{limit:.0f}",
    )
