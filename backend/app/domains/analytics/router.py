"""Analytics domain router — /api/v1/analytics."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.event_bus import bus, DomainEvent
from app.deps import get_current_user, require_permission
from app.infra.database import get_db
from app.infra.models import User

from .models import AnalyticsEvent, AnalyticsMetric
from .slack_models import SlackSubscription, SlackNotificationQueue, SlackDeliveryLog
from .service import AnalyticsService
from .slack_service import SlackService
from . import schemas as domain_schemas
from . import slack_schemas as slack_domain_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


# Analytics Events Endpoints

@router.post("/events", response_model=domain_schemas.AnalyticsEventResponse)
def create_event(
    event: domain_schemas.AnalyticsEventCreate,
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("analytics.write")),
) -> AnalyticsEvent:
    """Create analytics event."""
    service = AnalyticsService(db)
    db_event = service.create_event(user.organization_id, event)

    # Publish event for subscribers
    evt = DomainEvent(
        name="analytics.event_created",
        payload={
            "event_id": db_event.id,
            "event_type": db_event.event_type,
            "event_name": db_event.event_name,
        },
        project_id=db_event.project_id,
    )
    bus.publish(evt)

    return db_event


@router.get("/events", response_model=list[domain_schemas.AnalyticsEventResponse])
def list_events(
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("analytics.read")),
    event_type: Optional[str] = Query(None),
    event_name: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[AnalyticsEvent]:
    """List analytics events."""
    service = AnalyticsService(db)
    return service.get_events(
        tenant_id=user.organization_id,
        event_type=event_type,
        event_name=event_name,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


# Analytics Metrics Endpoints

@router.post("/metrics", response_model=domain_schemas.AnalyticsMetricResponse)
def create_metric(
    metric: domain_schemas.AnalyticsMetricCreate,
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("analytics.write")),
) -> AnalyticsMetric:
    """Create analytics metric."""
    service = AnalyticsService(db)
    return service.create_metric(user.organization_id, metric)


@router.get("/metrics", response_model=list[domain_schemas.AnalyticsMetricResponse])
def list_metrics(
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("analytics.read")),
    metric_name: Optional[str] = Query(None),
    metric_category: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    period: Optional[str] = Query(None),
) -> list[domain_schemas.AnalyticsMetricResponse]:
    """List analytics metrics."""
    service = AnalyticsService(db)
    return service.get_metrics(
        tenant_id=user.organization_id,
        metric_name=metric_name,
        metric_category=metric_category,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        period=period,
    )


# Dashboard Endpoints

@router.get("/dashboard/metrics", response_model=domain_schemas.DashboardMetricsResponse)
def get_dashboard_metrics(
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("analytics.read")),
    project_id: Optional[str] = Query(None),
) -> domain_schemas.DashboardMetricsResponse:
    """Get dashboard metrics summary."""
    service = AnalyticsService(db)

    # Get latest metrics
    test_exec = service.get_latest_metric(
        user.organization_id, "test_execution_count", project_id
    )
    defect_created = service.get_latest_metric(
        user.organization_id, "defect_created_count", project_id
    )
    coverage = service.get_latest_metric(
        user.organization_id, "coverage_percentage", project_id
    )
    flakiness = service.get_latest_metric(
        user.organization_id, "flakiness_rate", project_id
    )

    return domain_schemas.DashboardMetricsResponse(
        test_execution_count=int(test_exec.metric_value) if test_exec else 0,
        test_pass_rate=float(service.get_latest_metric(
            user.organization_id, "test_pass_rate", project_id
        ).metric_value if service.get_latest_metric(
            user.organization_id, "test_pass_rate", project_id
        ) else 0.0),
        defect_rate=float(defect_created.metric_value) if defect_created else 0.0,
        team_velocity=float(service.get_latest_metric(
            user.organization_id, "team_velocity", project_id
        ).metric_value if service.get_latest_metric(
            user.organization_id, "team_velocity", project_id
        ) else 0.0),
        coverage_percentage=float(coverage.metric_value) if coverage else 0.0,
        average_resolution_time=None,
        flakiness_rate=float(flakiness.metric_value) if flakiness else 0.0,
        data_period="daily",
    )


@router.get("/dashboard/trends", response_model=domain_schemas.TrendChartResponse)
def get_trend_chart(
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("analytics.read")),
    metric_name: str = Query("test_execution_count"),
    days: int = Query(30, ge=1, le=365),
) -> domain_schemas.TrendChartResponse:
    """Get trend chart data."""
    service = AnalyticsService(db)
    trend_data = service.get_trend_data(user.organization_id, metric_name, days)

    if not trend_data:
        raise HTTPException(404, "No trend data available")

    # Calculate trend direction
    if len(trend_data) >= 2:
        recent = sum(p.value for p in trend_data[-7:]) / 7 if len(trend_data) >= 7 else trend_data[-1].value
        previous = sum(p.value for p in trend_data[-14:-7]) / 7 if len(trend_data) >= 14 else trend_data[0].value
        change = ((recent - previous) / previous * 100) if previous > 0 else 0.0
        trend = "up" if change > 0 else "down" if change < 0 else "stable"
    else:
        trend = "stable"
        change = 0.0

    return domain_schemas.TrendChartResponse(
        title=f"{metric_name} Trend",
        metric_name=metric_name,
        unit="count",
        data_points=trend_data,
        trend=trend,
        change_percentage=change,
    )


@router.get("/dashboard/coverage-heatmap", response_model=domain_schemas.CoverageHeatmapResponse)
def get_coverage_heatmap(
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("analytics.read")),
    project_id: Optional[str] = Query(None),
) -> domain_schemas.CoverageHeatmapResponse:
    """Get coverage heatmap."""
    service = AnalyticsService(db)
    return service.calculate_coverage_heatmap(user.organization_id, project_id)


# Slack Integration Endpoints

@router.post("/slack/subscriptions", response_model=slack_domain_schemas.SlackSubscriptionResponse)
def create_slack_subscription(
    subscription: slack_domain_schemas.SlackSubscriptionCreate,
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("slack.manage")),
) -> SlackSubscription:
    """Create Slack subscription."""
    service = SlackService(db)
    return service.create_subscription(user.organization_id, subscription, created_by=user.id)


@router.get("/slack/subscriptions", response_model=list[slack_domain_schemas.SlackSubscriptionResponse])
def list_slack_subscriptions(
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("slack.read")),
    workspace_id: Optional[str] = Query(None),
) -> list[SlackSubscription]:
    """List Slack subscriptions."""
    service = SlackService(db)
    return service.get_subscriptions(user.organization_id, workspace_id)


@router.put("/slack/subscriptions/{subscription_id}", response_model=slack_domain_schemas.SlackSubscriptionResponse)
def update_slack_subscription(
    subscription_id: str,
    update: slack_domain_schemas.SlackSubscriptionUpdate,
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("slack.manage")),
) -> SlackSubscription:
    """Update Slack subscription."""
    service = SlackService(db)
    subscription = db.get(SlackSubscription, subscription_id)
    if not subscription or subscription.tenant_id != user.organization_id:
        raise HTTPException(404, "Subscription not found")

    return service.update_subscription(subscription_id, update)


@router.delete("/slack/subscriptions/{subscription_id}")
def delete_slack_subscription(
    subscription_id: str,
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("slack.manage")),
) -> dict:
    """Delete Slack subscription."""
    service = SlackService(db)
    subscription = db.get(SlackSubscription, subscription_id)
    if not subscription or subscription.tenant_id != user.organization_id:
        raise HTTPException(404, "Subscription not found")

    service.delete_subscription(subscription_id)
    return {"status": "deleted"}


@router.get("/slack/delivery-logs", response_model=list[slack_domain_schemas.SlackDeliveryLogResponse])
def list_delivery_logs(
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("slack.read")),
    channel_id: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[SlackDeliveryLog]:
    """List Slack delivery logs."""
    service = SlackService(db)
    return service.get_delivery_logs(
        user.organization_id,
        channel_id=channel_id,
        success=success,
        limit=limit,
    )


@router.get("/slack/queue-status", response_model=dict)
def get_queue_status(
    user: CurrentUser,
    db: DB,
    _: str = Depends(require_permission("slack.read")),
) -> dict:
    """Get Slack notification queue status."""
    service = SlackService(db)
    pending = service.get_pending_notifications(user.organization_id, limit=1000)

    return {
        "total_pending": len(pending),
        "by_status": {
            "pending": sum(1 for p in pending if p.status == "pending"),
            "failed": sum(1 for p in pending if p.status == "failed"),
            "dlq": sum(1 for p in pending if p.status == "dlq"),
        },
    }
