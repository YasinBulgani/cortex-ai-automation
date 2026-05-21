"""Nexus Repo Pydantic şemaları (request / response)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


# ── NexusProject ──────────────────────────────────────────────────────────────

class NexusProjectCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    repo_url: str = Field(..., max_length=1000)
    repo_type: str = Field("git", pattern="^(git|svn|bitbucket|github)$")
    branch: str = Field("main", max_length=200)
    credential_ref: Optional[str] = None
    llm_provider: str = Field("ollama", pattern="^(ollama|openai|anthropic)$")
    llm_model: str = Field("qwen2.5:32b", max_length=100)


class NexusProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    branch: Optional[str] = Field(None, max_length=200)
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    archived: Optional[bool] = None


class NexusProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    repo_url: str
    repo_type: str
    branch: str
    llm_provider: str
    llm_model: str
    archived: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── NexusCrawlJob ─────────────────────────────────────────────────────────────

class NexusCrawlJobOut(BaseModel):
    id: str
    project_id: str
    status: str
    commit_sha: Optional[str]
    files_scanned: int
    endpoints_found: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── NexusScenario ─────────────────────────────────────────────────────────────

class NexusScenarioCreate(BaseModel):
    title: str = Field(..., max_length=500)
    type: str = Field(..., pattern="^(manual|service|automation)$")
    feature_area: Optional[str] = Field(None, max_length=200)
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    gherkin: Optional[str] = None
    notes: Optional[str] = None


class NexusScenarioUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    type: Optional[str] = None
    feature_area: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    gherkin: Optional[str] = None
    notes: Optional[str] = None


class NexusScenarioOut(BaseModel):
    id: str
    project_id: str
    title: str
    type: str
    feature_area: Optional[str]
    priority: str
    status: str
    gherkin: Optional[str]
    notes: Optional[str]
    llm_model: Optional[str]
    llm_prompt_tokens: int
    llm_completion_tokens: int
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── NexusCase ─────────────────────────────────────────────────────────────────

class NexusCaseOut(BaseModel):
    id: str
    scenario_id: str
    name: str
    preconditions: Optional[str]
    steps: Optional[list]
    expected_result: Optional[str]
    test_data: Optional[dict]
    order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── NexusExport ───────────────────────────────────────────────────────────────

class NexusExportCreate(BaseModel):
    format: str = Field(..., pattern="^(gherkin|postman|excel|jira)$")
    scenario_ids: Optional[list[str]] = None  # None = tüm senaryolar
    # Jira için opsiyonel alan — hangi proje/component'e aktarılacağı
    jira_project_key: Optional[str] = None


class NexusExportOut(BaseModel):
    id: str
    project_id: str
    format: str
    file_path: Optional[str]
    scenario_ids: Optional[list]
    status: str
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Genel yanıt sarmalayıcılar ────────────────────────────────────────────────

class NexusEndpointOut(BaseModel):
    id: str
    crawl_job_id: str
    method: str
    path: str
    source_file: Optional[str]
    source_line: Optional[int]
    auth_required: bool
    tags: Optional[list]
    created_at: datetime

    model_config = {"from_attributes": True}


class NexusFileOut(BaseModel):
    id: str
    crawl_job_id: str
    path: str
    language: Optional[str]
    size_bytes: int
    tokens_estimate: int
    summary: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class NexusStatsOut(BaseModel):
    total_scenarios: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    by_priority: dict[str, int]
    total_crawl_jobs: int
    last_crawl_at: Optional[datetime]
    total_endpoints: int
    total_files: int


class NexusHealthOut(BaseModel):
    status: str = "ok"
    feature_enabled: bool
    version: str = "0.1.0"


class NexusGenerateRequest(BaseModel):
    crawl_job_id: str
    scenario_types: list[str] = Field(default=["manual", "service", "automation"])
    max_scenarios: int = Field(default=20, ge=1, le=100)
    language: str = Field(default="tr", pattern="^(tr|en)$")
