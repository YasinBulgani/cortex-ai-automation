"""Analytics domain service — event tracking and metrics aggregation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from app.domains.analytics.models import AnalyticsEvent, AnalyticsMetric
from . import schemas as domain_schemas

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_event(
        self, tenant_id: str, event: domain_schemas.AnalyticsEventCreate
    ) -> AnalyticsEvent:
        """Create analytics event."""
        event_timestamp = event.timestamp or datetime.now(timezone.utc)

        db_event = AnalyticsEvent(
            tenant_id=tenant_id,
            event_type=event.event_type,
            event_name=event.event_name,
            entity_id=event.entity_id,
            entity_type=event.entity_type,
            user_id=event.user_id,
            project_id=event.project_id,
            event_data=event.event_data or {},
            timestamp=event_timestamp,
        )
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)

        logger.info(f"Analytics event created: {event.event_name} ({db_event.id})")
        return db_event

    def get_events(
        self,
        tenant_id: str,
        event_type: Optional[str] = None,
        event_name: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalyticsEvent]:
        """Get analytics events with filtering."""
        query = select(AnalyticsEvent).where(AnalyticsEvent.tenant_id == tenant_id)

        if event_type:
            query = query.where(AnalyticsEvent.event_type == event_type)
        if event_name:
            query = query.where(AnalyticsEvent.event_name == event_name)
        if project_id:
            query = query.where(AnalyticsEvent.project_id == project_id)
        if user_id:
            query = query.where(AnalyticsEvent.user_id == user_id)
        if start_date:
            query = query.where(AnalyticsEvent.timestamp >= start_date)
        if end_date:
            query = query.where(AnalyticsEvent.timestamp <= end_date)

        query = query.order_by(AnalyticsEvent.timestamp.desc()).limit(limit).offset(offset)

        return self.db.scalars(query).all()

    def get_event_count(
        self,
        tenant_id: str,
        event_type: Optional[str] = None,
        event_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get event count with filtering."""
        query = select(func.count()).select_from(AnalyticsEvent).where(AnalyticsEvent.tenant_id == tenant_id)

        if event_type:
            query = query.where(AnalyticsEvent.event_type == event_type)
        if event_name:
            query = query.where(AnalyticsEvent.event_name == event_name)
        if start_date:
            query = query.where(AnalyticsEvent.timestamp >= start_date)
        if end_date:
            query = query.where(AnalyticsEvent.timestamp <= end_date)

        return self.db.scalar(query) or 0

    def create_metric(
        self, tenant_id: str, metric: domain_schemas.AnalyticsMetricCreate
    ) -> AnalyticsMetric:
        """Create analytics metric."""
        db_metric = AnalyticsMetric(
            tenant_id=tenant_id,
            metric_name=metric.metric_name,
            metric_category=metric.metric_category,
            metric_value=float(metric.metric_value),
            metric_unit=metric.metric_unit,
            project_id=metric.project_id,
            team_id=metric.team_id,
            date=metric.date,
            period=metric.period,
            metadata=metric.metadata or {},
        )
        self.db.add(db_metric)
        self.db.commit()
        self.db.refresh(db_metric)

        return db_metric

    def get_metrics(
        self,
        tenant_id: str,
        metric_name: Optional[str] = None,
        metric_category: Optional[str] = None,
        project_id: Optional[str] = None,
        team_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        period: Optional[str] = None,
        limit: int = 100,
    ) -> list[AnalyticsMetric]:
        """Get metrics with filtering."""
        query = select(AnalyticsMetric).where(AnalyticsMetric.tenant_id == tenant_id)

        if metric_name:
            query = query.where(AnalyticsMetric.metric_name == metric_name)
        if metric_category:
            query = query.where(AnalyticsMetric.metric_category == metric_category)
        if project_id:
            query = query.where(AnalyticsMetric.project_id == project_id)
        if team_id:
            query = query.where(AnalyticsMetric.team_id == team_id)
        if start_date:
            query = query.where(AnalyticsMetric.date >= start_date)
        if end_date:
            query = query.where(AnalyticsMetric.date <= end_date)
        if period:
            query = query.where(AnalyticsMetric.period == period)

        query = query.order_by(AnalyticsMetric.date.desc()).limit(limit)

        return self.db.scalars(query).all()

    def get_latest_metric(
        self,
        tenant_id: str,
        metric_name: str,
        project_id: Optional[str] = None,
    ) -> Optional[AnalyticsMetric]:
        """Get latest metric value."""
        query = select(AnalyticsMetric).where(
            and_(
                AnalyticsMetric.tenant_id == tenant_id,
                AnalyticsMetric.metric_name == metric_name,
            )
        )

        if project_id:
            query = query.where(AnalyticsMetric.project_id == project_id)

        query = query.order_by(AnalyticsMetric.date.desc()).limit(1)

        return self.db.scalars(query).first()

    def aggregate_daily_metrics(self, tenant_id: str, target_date: date) -> None:
        """Aggregate daily metrics from events."""
        start_datetime = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
        end_datetime = datetime.combine(target_date, datetime.max.time(), tzinfo=timezone.utc)

        # Test execution count
        test_run_count = self.get_event_count(
            tenant_id,
            event_type="test_run",
            start_date=start_datetime,
            end_date=end_datetime,
        )
        if test_run_count > 0:
            self.create_metric(
                tenant_id,
                domain_schemas.AnalyticsMetricCreate(
                    metric_name="test_execution_count",
                    metric_category="execution",
                    metric_value=test_run_count,
                    metric_unit="count",
                    date=target_date,
                    period="daily",
                ),
            )

        # Defect creation count
        defect_count = self.get_event_count(
            tenant_id,
            event_type="defect",
            event_name="defect_created",
            start_date=start_datetime,
            end_date=end_datetime,
        )
        if defect_count > 0:
            self.create_metric(
                tenant_id,
                domain_schemas.AnalyticsMetricCreate(
                    metric_name="defect_created_count",
                    metric_category="defect",
                    metric_value=defect_count,
                    metric_unit="count",
                    date=target_date,
                    period="daily",
                ),
            )

    def get_trend_data(
        self,
        tenant_id: str,
        metric_name: str,
        days: int = 30,
    ) -> list[domain_schemas.TrendDataPoint]:
        """Get trend data for a metric."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        metrics = self.get_metrics(
            tenant_id,
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
            limit=days,
        )

        return [
            domain_schemas.TrendDataPoint(
                date=m.date,
                value=float(m.metric_value),
                label=m.metric_unit,
            )
            for m in sorted(metrics, key=lambda x: x.date)
        ]

    def calculate_coverage_heatmap(
        self, tenant_id: str, project_id: Optional[str] = None
    ) -> domain_schemas.CoverageHeatmapResponse:
        """Calculate coverage heatmap."""
        query = select(AnalyticsMetric).where(
            and_(
                AnalyticsMetric.tenant_id == tenant_id,
                AnalyticsMetric.metric_name == "coverage_percentage",
            )
        )

        if project_id:
            query = query.where(AnalyticsMetric.project_id == project_id)

        metrics = self.db.scalars(query).all()

        cells = [
            domain_schemas.CoverageHeatmapCell(
                module=m.metadata.get("module", "Unknown") if m.metadata else "Unknown",
                test_type=m.metadata.get("test_type", "Unknown") if m.metadata else "Unknown",
                coverage_percentage=float(m.metric_value),
                test_count=m.metadata.get("test_count", 0) if m.metadata else 0,
            )
            for m in metrics
        ]

        total_coverage = (
            sum(float(m.metric_value) for m in metrics) / len(metrics) if metrics else 0.0
        )

        return domain_schemas.CoverageHeatmapResponse(
            cells=cells,
            total_coverage=total_coverage,
        )
