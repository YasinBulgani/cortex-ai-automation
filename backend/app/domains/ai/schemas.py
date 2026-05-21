"""AI domain Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    context_type: Optional[str] = None  # "scenario", "execution", "coverage", ...
    context_id: Optional[str] = None

class ChatMessageOut(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class ChatSessionOut(BaseModel):
    id: str
    title: str
    project_id: str
    created_at: Optional[datetime] = None
    message_count: int = 0
    model_config = {"from_attributes": True}

class ChatSessionDetail(BaseModel):
    id: str
    title: str
    project_id: str
    messages: list[ChatMessageOut] = []
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Test Analysis ─────────────────────────────────────────────────────

class TestAnalysisRequest(BaseModel):
    execution_id: Optional[str] = None
    question: str = Field(default="", max_length=5000)

class TestAnalysisInsight(BaseModel):
    category: str  # "failure_pattern", "coverage_gap", "flaky_test", "optimization", "risk"
    severity: str = "info"  # "info", "warning", "critical"
    title: str
    description: str
    affected_scenarios: list[str] = []
    suggestion: str = ""

class TestAnalysisResponse(BaseModel):
    summary: str
    insights: list[TestAnalysisInsight] = []
    recommendations: list[str] = []


# ── Scenario Generation ──────────────────────────────────────────────

class ScenarioGenerateRequest(BaseModel):
    description: str = Field(min_length=10, max_length=10000)
    context: str = ""
    count: int = Field(default=5, ge=1, le=20)

class GeneratedScenario(BaseModel):
    title: str
    description: str = ""
    steps: list[dict[str, Any]] = []
    tags: list[str] = []
    priority: str = "medium"

class ScenarioGenerateResponse(BaseModel):
    scenarios: list[GeneratedScenario] = []


# ── Test Data Generation ─────────────────────────────────────────────

class TestDataGenerateRequest(BaseModel):
    description: str = Field(min_length=5, max_length=5000)
    columns: list[dict[str, Any]] = []
    row_count: int = Field(default=10, ge=1, le=1000)

class TestDataGenerateResponse(BaseModel):
    columns: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
