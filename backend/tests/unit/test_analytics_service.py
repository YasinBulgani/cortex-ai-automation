"""Unit tests for analytics service."""

import pytest
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.orm import Session

from app.domains.analytics.models import AnalyticsEvent, AnalyticsMetric
from app.domains.analytics.service import AnalyticsService
from app.domains.analytics import schemas as domain_schemas


@pytest.fixture
def analytics_service(db: Session) -> AnalyticsService:
    """Create analytics service instance."""
    return AnalyticsService(db)


class TestAnalyticsService:
    """Analytics service tests."""

    def test_create_event(self, analytics_service: AnalyticsService):
        """Test creating an analytics event."""
        tenant_id = "test-tenant-1"

        event = domain_schemas.AnalyticsEventCreate(
            event_type="test_run",
            event_name="test_run_started",
            entity_id="test-run-123",
            entity_type="TestRun",
            project_id="project-1",
            event_data={"duration": 45.5},
        )

        result = analytics_service.create_event(tenant_id, event)

        assert result.id is not None
        assert result.tenant_id == tenant_id
        assert result.event_type == "test_run"
        assert result.event_name == "test_run_started"
        assert result.event_data["duration"] == 45.5

    def test_get_events_by_type(self, analytics_service: AnalyticsService, db: Session):
        """Test getting events by type."""
        tenant_id = "test-tenant-1"

        # Create test events
        for i in range(3):
            event = domain_schemas.AnalyticsEventCreate(
                event_type="test_run",
                event_name="test_run_completed",
            )
            analytics_service.create_event(tenant_id, event)

        # Create different event type
        event = domain_schemas.AnalyticsEventCreate(
            event_type="defect",
            event_name="defect_created",
        )
        analytics_service.create_event(tenant_id, event)

        # Query by type
        results = analytics_service.get_events(
            tenant_id, event_type="test_run", limit=10
        )

        assert len(results) == 3
        assert all(e.event_type == "test_run" for e in results)

    def test_get_event_count(self, analytics_service: AnalyticsService):
        """Test getting event count."""
        tenant_id = "test-tenant-1"

        # Create events
        for _ in range(5):
            event = domain_schemas.AnalyticsEventCreate(
                event_type="test_run",
                event_name="test_run_completed",
            )
            analytics_service.create_event(tenant_id, event)

        count = analytics_service.get_event_count(
            tenant_id, event_type="test_run"
        )

        assert count == 5

    def test_create_metric(self, analytics_service: AnalyticsService):
        """Test creating a metric."""
        tenant_id = "test-tenant-1"

        metric = domain_schemas.AnalyticsMetricCreate(
            metric_name="test_execution_count",
            metric_category="execution",
            metric_value=42.0,
            metric_unit="count",
            date=date.today(),
            period="daily",
        )

        result = analytics_service.create_metric(tenant_id, metric)

        assert result.id is not None
        assert result.metric_name == "test_execution_count"
        assert result.metric_value == 42.0

    def test_get_metrics_by_name(self, analytics_service: AnalyticsService):
        """Test getting metrics by name."""
        tenant_id = "test-tenant-1"
        today = date.today()

        # Create metrics with different names
        for i in range(2):
            metric = domain_schemas.AnalyticsMetricCreate(
                metric_name="test_execution_count",
                metric_category="execution",
                metric_value=float(10 + i),
                date=today - timedelta(days=i),
                period="daily",
            )
            analytics_service.create_metric(tenant_id, metric)

        # Create different metric
        metric = domain_schemas.AnalyticsMetricCreate(
            metric_name="defect_rate",
            metric_category="defect",
            metric_value=5.0,
            date=today,
            period="daily",
        )
        analytics_service.create_metric(tenant_id, metric)

        results = analytics_service.get_metrics(
            tenant_id, metric_name="test_execution_count"
        )

        assert len(results) == 2
        assert all(m.metric_name == "test_execution_count" for m in results)

    def test_get_latest_metric(self, analytics_service: AnalyticsService):
        """Test getting latest metric."""
        tenant_id = "test-tenant-1"
        today = date.today()

        # Create multiple metrics for same name
        for i in range(3):
            metric = domain_schemas.AnalyticsMetricCreate(
                metric_name="coverage_percentage",
                metric_category="coverage",
                metric_value=float(50 + i * 10),
                date=today - timedelta(days=2 - i),
                period="daily",
            )
            analytics_service.create_metric(tenant_id, metric)

        latest = analytics_service.get_latest_metric(
            tenant_id, "coverage_percentage"
        )

        assert latest is not None
        assert latest.metric_value == 70.0
        assert latest.date == today

    def test_get_trend_data(self, analytics_service: AnalyticsService):
        """Test getting trend data."""
        tenant_id = "test-tenant-1"
        today = date.today()

        # Create metrics for 10 days
        for i in range(10):
            metric = domain_schemas.AnalyticsMetricCreate(
                metric_name="test_execution_count",
                metric_category="execution",
                metric_value=float(100 + i * 5),
                date=today - timedelta(days=9 - i),
                period="daily",
            )
            analytics_service.create_metric(tenant_id, metric)

        trend_data = analytics_service.get_trend_data(
            tenant_id, "test_execution_count", days=10
        )

        assert len(trend_data) == 10
        assert all(isinstance(p.value, float) for p in trend_data)

    def test_aggregate_daily_metrics(
        self, analytics_service: AnalyticsService, db: Session
    ):
        """Test daily metrics aggregation."""
        tenant_id = "test-tenant-1"
        today = date.today()

        # Create some test_run events
        start = datetime.combine(today, datetime.min.time(), timezone.utc)
        end = datetime.combine(today, datetime.max.time(), timezone.utc)

        for _ in range(5):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                event_type="test_run",
                event_name="test_run_completed",
                timestamp=start + timedelta(hours=1),
            )
            db.add(event)
        db.commit()

        # Aggregate
        analytics_service.aggregate_daily_metrics(tenant_id, today)

        # Check that metric was created
        metrics = analytics_service.get_metrics(
            tenant_id, metric_name="test_execution_count", start_date=today
        )

        assert len(metrics) > 0
        assert metrics[0].metric_value == 5.0

    def test_calculate_coverage_heatmap(
        self, analytics_service: AnalyticsService
    ):
        """Test coverage heatmap calculation."""
        tenant_id = "test-tenant-1"

        # Create coverage metrics
        for module in ["auth", "api", "db"]:
            metric = domain_schemas.AnalyticsMetricCreate(
                metric_name="coverage_percentage",
                metric_category="coverage",
                metric_value=75.0 + len(module),
                date=date.today(),
                period="daily",
                metadata={"module": module, "test_type": "unit", "test_count": 10},
            )
            analytics_service.create_metric(tenant_id, metric)

        heatmap = analytics_service.calculate_coverage_heatmap(tenant_id)

        assert len(heatmap.cells) == 3
        assert heatmap.total_coverage > 0

    def test_metric_filtering_by_date_range(
        self, analytics_service: AnalyticsService
    ):
        """Test metric filtering by date range."""
        tenant_id = "test-tenant-1"
        start_date = date(2026, 1, 1)

        # Create metrics across different dates
        for i in range(10):
            metric = domain_schemas.AnalyticsMetricCreate(
                metric_name="test_count",
                metric_category="execution",
                metric_value=float(100 + i),
                date=start_date + timedelta(days=i),
                period="daily",
            )
            analytics_service.create_metric(tenant_id, metric)

        # Query specific range
        results = analytics_service.get_metrics(
            tenant_id,
            metric_name="test_count",
            start_date=start_date + timedelta(days=2),
            end_date=start_date + timedelta(days=5),
        )

        assert len(results) == 4

    def test_event_filtering_by_project(
        self, analytics_service: AnalyticsService
    ):
        """Test event filtering by project."""
        tenant_id = "test-tenant-1"

        # Create events for different projects
        for project_id in ["proj-1", "proj-2"]:
            for _ in range(3):
                event = domain_schemas.AnalyticsEventCreate(
                    event_type="test_run",
                    event_name="test_run_completed",
                    project_id=project_id,
                )
                analytics_service.create_event(tenant_id, event)

        results = analytics_service.get_events(
            tenant_id, project_id="proj-1"
        )

        assert len(results) == 3
        assert all(e.project_id == "proj-1" for e in results)


class TestAnalyticsMetricAggregation:
    """Test metric aggregation logic."""

    def test_daily_aggregation_empty_events(
        self, analytics_service: AnalyticsService
    ):
        """Test aggregation when no events exist."""
        tenant_id = "test-tenant-empty"
        today = date.today()

        # Should not fail
        analytics_service.aggregate_daily_metrics(tenant_id, today)

        # No metrics should be created
        metrics = analytics_service.get_metrics(
            tenant_id, start_date=today
        )
        assert len(metrics) == 0

    def test_multiple_event_types_counted(
        self, analytics_service: AnalyticsService, db: Session
    ):
        """Test that different event types are counted separately."""
        tenant_id = "test-tenant-multi"
        today = date.today()
        start = datetime.combine(today, datetime.min.time(), timezone.utc)

        # Create mixed events
        event_types = [
            ("test_run", "test_run_started"),
            ("test_run", "test_run_completed"),
            ("defect", "defect_created"),
        ]

        for event_type, event_name in event_types:
            for _ in range(2):
                event = AnalyticsEvent(
                    tenant_id=tenant_id,
                    event_type=event_type,
                    event_name=event_name,
                    timestamp=start,
                )
                db.add(event)
        db.commit()

        # Aggregate
        analytics_service.aggregate_daily_metrics(tenant_id, today)

        # Check counts
        test_runs = analytics_service.get_event_count(
            tenant_id, event_type="test_run"
        )
        defects = analytics_service.get_event_count(
            tenant_id, event_type="defect"
        )

        assert test_runs == 4
        assert defects == 2
