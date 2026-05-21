"""Canonical AI workflow API schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domains.agents.v2.api_schemas import RunAgentV2Request


WorkflowStatusValue = Literal[
    "pending_approval",
    "queued",
    "running",
    "completed",
    "failed",
    "failed_validation",
    "cancelled",
]


class AIWorkflowCreateRequest(RunAgentV2Request):
    workflow_type: Literal[
        "test_generation",
        "analysis",
        "code_generation",
        "review",
        "repair",
        "report",
    ] = "test_generation"
    dry_run: bool = False
    requires_approval: bool = False


class AIWorkflowCreateResponse(BaseModel):
    workflow_id: str
    run_id: str
    status: WorkflowStatusValue
    created_at: datetime
    stream_url: str
    detail_url: str
    events_url: str
    artifacts_url: str


class AIWorkflowStatus(BaseModel):
    workflow_id: str
    run_id: str
    project_id: str
    status: str
    input_source: str
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    event_count: int = 0
    artifact_count: int = 0
    approval_count: int = 0
    cost_usd: float = 0.0
    tokens_used: int = 0
    llm_calls_count: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    intent_graph: dict[str, Any] | None = None
    app_map: dict[str, Any] | None = None
    scenarios: list[dict[str, Any]] = Field(default_factory=list)
    generated_code: dict[str, Any] | None = None
    run_result: dict[str, Any] | None = None
    healing_result: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    report: dict[str, Any] | None = None


class AIWorkflowEventListResponse(BaseModel):
    workflow_id: str
    events: list[dict[str, Any]] = Field(default_factory=list)


class AIWorkflowArtifact(BaseModel):
    artifact_id: str
    kind: str
    name: str
    storage_path: str
    mime_type: str
    size_bytes: int = 0
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIWorkflowArtifactListResponse(BaseModel):
    workflow_id: str
    artifacts: list[AIWorkflowArtifact] = Field(default_factory=list)


class AIWorkflowHealthSummary(BaseModel):
    generated_at: datetime
    sample_size: int
    runs_total: int
    active_runs: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_workflow_type: dict[str, int] = Field(default_factory=dict)
    event_counts: dict[str, int] = Field(default_factory=dict)
    artifact_count: int = 0
    artifact_bytes: int = 0
    approval_count: int = 0
    dead_letters_total: int = 0
    recent_dead_letters: list[dict[str, Any]] = Field(default_factory=list)
    queue_depth: int | None = None
    oldest_active_seconds: float | None = None
    cost_usd: float = 0.0
    tokens_used: int = 0
    llm_calls_count: int = 0
    ops_evidence: dict[str, Any] | None = None


class AIWorkflowDeadLetterListResponse(BaseModel):
    dead_letters: list[dict[str, Any]] = Field(default_factory=list)


class AIWorkflowApprovalRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = None


class AIWorkflowApprovalResponse(BaseModel):
    workflow_id: str
    status: str
    approval: dict[str, Any]
