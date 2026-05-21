"""REST API Request/Response Pydantic modelleri."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunAgentV2Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    input_source: Literal[
        "pdf", "docx", "url", "swagger", "confluence",
        "jira", "figma", "bpmn", "postman", "manual", "text"
    ]

    url: str | None = None
    file_path: str | None = None
    text: str | None = None
    swagger_url: str | None = None

    extra_context: str | None = None
    credentials: dict[str, str] | None = None
    allowed_hosts: list[str] | None = None
    max_pages: int = Field(15, ge=1, le=100)
    max_depth: int = Field(2, ge=1, le=4)

    enable_ai_xpath: bool = False
    auto_pr: bool = False
    auto_merge: bool = False


class RunAgentV2Response(BaseModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    stream_url: str
    detail_url: str


class RunV2Status(BaseModel):
    run_id: str
    status: str
    project_id: str
    input_source: str
    created_at: datetime
    completed_at: datetime | None = None
    cost_usd: float = 0.0
    tokens_used: int = 0
    llm_calls_count: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)

    intent_graph: dict | None = None
    app_map: dict | None = None
    scenarios: list[dict] = Field(default_factory=list)
    generated_code: dict | None = None
    run_result: dict | None = None
    healing_result: dict | None = None
    review: dict | None = None
    report: dict | None = None


class RunV2ListItem(BaseModel):
    run_id: str
    project_id: str
    status: str
    input_source: str
    created_at: datetime
    completed_at: datetime | None = None
    cost_usd: float = 0.0
    scenario_count: int = 0
    passed_count: int = 0
    failed_count: int = 0


class RunV2ListResponse(BaseModel):
    runs: list[RunV2ListItem]
    total: int
    page: int = 1
    page_size: int = 20


class AgentStreamEvent(BaseModel):
    run_id: str
    event_type: Literal[
        "started", "agent_started", "agent_finished",
        "llm_call", "error", "completed", "failed", "progress"
    ]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_name: str | None = None
    message: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
