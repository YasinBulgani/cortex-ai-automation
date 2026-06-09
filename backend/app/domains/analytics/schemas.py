"""Analytics domain schemas — request/response contracts."""

from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Analytics event types."""

    TEST_RUN = "test_run"
    DEFECT = "defect"
    COVERAGE = "coverage"
    EXECUTION = "execution"
    INTEGRATION = "integration"


class EventName(str, Enum):
    """Specific event names."""

    TEST_RUN_STARTED = "test_run_started"
    TEST_RUN_COMPLETED = "test_run_completed"
    TEST_CASE_COMPLETED = "test_case_completed"
    DEFECT_CREATED = "defect_created"
    DEFECT_RESOLVED = "defect_resolved"
    COVERAGE_UPDATED = "coverage_updated"
    TEAM_VELOCITY = "team_velocity"


class AnalyticsEventCreate(BaseModel):
    """Create analytics event."""

    event_type: str
    event_name: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    event_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None


class AnalyticsEventResponse(BaseModel):
    """Analytics event response."""

    id: str
    event_type: str
    event_name: str
    entity_id: Optional[str]
    entity_type: Optional[str]
    user_id: Optional[str]
    project_id: Optional[str]
    event_data: dict[str, Any]
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsMetricCreate(BaseModel):
    """Create analytics metric."""

    metric_name: str
    metric_category: str
    metric_value: float
    metric_unit: Optional[str] = None
    project_id: Optional[str] = None
    team_id: Optional[str] = None
    date: date
    period: str  # "daily", "weekly", "monthly"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsMetricResponse(BaseModel):
    """Analytics metric response."""

    id: str
    metric_name: str
    metric_category: str
    metric_value: float
    metric_unit: Optional[str]
    project_id: Optional[str]
    team_id: Optional[str]
    date: date
    period: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetricsFilter(BaseModel):
    """Filter for metrics queries."""

    metric_name: Optional[str] = None
    metric_category: Optional[str] = None
    project_id: Optional[str] = None
    team_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    period: Optional[str] = None


class DashboardMetricsResponse(BaseModel):
    """Dashboard metrics summary."""

    test_execution_count: int
    test_pass_rate: float
    defect_rate: float
    team_velocity: float
    coverage_percentage: float
    average_resolution_time: Optional[float]
    flakiness_rate: float
    data_period: str


class TrendDataPoint(BaseModel):
    """Single data point for trend charts."""

    date: date
    value: float
    label: Optional[str] = None


class TrendChartResponse(BaseModel):
    """Trend chart data."""

    title: str
    metric_name: str
    unit: Optional[str]
    data_points: list[TrendDataPoint]
    trend: str  # "up", "down", "stable"
    change_percentage: float


class CoverageHeatmapCell(BaseModel):
    """Coverage heatmap cell."""

    module: str
    test_type: str
    coverage_percentage: float
    test_count: int


class CoverageHeatmapResponse(BaseModel):
    """Coverage heatmap data."""

    cells: list[CoverageHeatmapCell]
    total_coverage: float


class DefectTrendResponse(BaseModel):
    """Defect trend data."""

    by_severity: dict[str, int]
    by_status: dict[str, int]
    average_resolution_time_hours: float
    trend_data: list[TrendDataPoint]


class ROIMetricsResponse(BaseModel):
    """ROI metrics response."""

    time_saved_hours: float
    manual_test_hours: float
    automated_test_hours: float
    cost_savings_usd: float
    roi_percentage: float
    period: str
