"""Pydantic response modelleri — Test Intelligence Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CaseRiskScoreOut(BaseModel):
    case_id: str
    case_key: str
    title: str
    risk_score: float = Field(ge=0.0, le=1.0)
    failure_rate: float
    severity_weight: float
    recency_factor: float
    priority_weight: float
    last_status: Optional[str] = None
    last_failed_at: Optional[datetime] = None
    recommendation: str  # "run_first" | "run_normal" | "deprioritize"


class TesterProfileOut(BaseModel):
    user_id: str
    assigned_count: int
    completed_count: int
    remaining_count: int
    avg_duration_seconds: float
    velocity_per_hour: float
    pass_rate: float
    blocked_rate: float
    is_bottleneck: bool
    last_activity_at: Optional[datetime] = None
    inactive_minutes: float


class ETAPredictionOut(BaseModel):
    run_id: str
    total_cases: int
    completed_cases: int
    remaining_cases: int
    elapsed_hours: float
    velocity_per_hour: float
    overall_velocity: float
    eta_hours: Optional[float] = None
    predicted_completion: Optional[datetime] = None
    confidence: float = Field(ge=0.0, le=1.0)
    on_track: bool
    risk_level: str  # "low" | "medium" | "high" | "critical"
    message: str


class AnomalyOut(BaseModel):
    severity: str  # "warning" | "critical"
    type: str
    title: str
    detail: str
    run_case_id: Optional[str] = None
    user_id: Optional[str] = None
    suggested_action: str = ""


class RunIntelligenceReportOut(BaseModel):
    run_id: str
    run_name: str
    generated_at: datetime
    eta: ETAPredictionOut
    testers: list[TesterProfileOut]
    anomalies: list[AnomalyOut]
    risk_sorted_remaining: list[CaseRiskScoreOut]
    summary_health: str  # "healthy" | "at_risk" | "critical"
    health_score: float  # 0–100


class ReleaseReadinessPredictionOut(BaseModel):
    project_id: str
    generated_at: datetime
    will_meet_gate: bool
    confidence: float
    days_to_completion: Optional[float] = None
    blocking_factors: list[str]
    execution_rate: float
    pass_rate: float
    open_defects: int
    recommendation: str


class TesterPerformanceOut(BaseModel):
    user_id: str
    total_executed: int
    pass_rate: float
    fail_rate: float = 0.0
    blocked_rate: float = 0.0
    avg_duration_seconds: float
    defect_detection_rate: float
    message: str = ""
