"""Automation Brain API schemas.

This module defines the single run contract shared by web, mobile, API,
LLM, and regression automation entry points.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


AutomationKind = Literal["web", "mobile", "api", "llm", "regression"]
AutomationStatus = Literal["queued", "running", "passed", "failed", "cancelled"]
AutomationTrigger = Literal["manual", "schedule", "api", "retry", "llm"]
AutomationProvenance = Literal["real", "simulated", "fallback", "stub"]


class AutomationCapability(BaseModel):
    kind: AutomationKind
    label: str
    description: str
    provenance: AutomationProvenance = "fallback"
    supports_cancel: bool = True
    supports_retry: bool = True
    required_fields: list[str] = Field(default_factory=list)
    route_hint: str | None = None


class AutomationRunCreate(BaseModel):
    project_id: str = Field(min_length=1, max_length=120)
    kind: AutomationKind
    name: str | None = Field(default=None, max_length=240)
    trigger: AutomationTrigger = "manual"
    environment: str | None = Field(default=None, max_length=120)
    device: str | None = Field(default=None, max_length=160)
    target: str | None = Field(default=None, max_length=1000)
    execute_now: bool = Field(
        default=False,
        description="Desteklenen adapter için gerçek koşumu hemen tetikle.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutomationRunOut(BaseModel):
    id: str
    project_id: str
    kind: AutomationKind
    name: str
    status: AutomationStatus
    trigger: AutomationTrigger
    environment: str | None = None
    device: str | None = None
    target: str | None = None
    provenance: AutomationProvenance
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    next_action: dict[str, Any] | None = None
    error: str | None = None
    retry_of: str | None = None
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutomationRunList(BaseModel):
    items: list[AutomationRunOut]
    total: int


class AutomationBrainSummary(BaseModel):
    capabilities: list[AutomationCapability]
    active_runs: int
    queued_runs: int
    last_run: AutomationRunOut | None = None
