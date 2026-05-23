"""Pydantic models for qa/ domain.

qa/tools/schemas/*.json ile aynı şemaya bağlı. Frontend type-safe consume eder.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Priority = Literal["P0", "P1", "P2", "P3"]
TestStatus = Literal["pass", "fail", "blocked", "skipped", "untested", "retest", "not-applicable"]
TestType = Literal[
    "functional", "smoke", "regression", "integration", "api", "ui", "perf", "security", "a11y", "exploratory"
]
TcStatus = Literal["draft", "active", "deprecated"]
AutomationStatus = Literal["not-automated", "in-progress", "automated", "out-of-scope"]
Severity = Literal["S1", "S2", "S3", "S4"]


class AutomationInfo(BaseModel):
    status: AutomationStatus
    reason: Optional[str] = None
    refs: List[str] = Field(default_factory=list)


class Configurations(BaseModel):
    browsers: List[str] = Field(default_factory=list)
    envs: List[str] = Field(default_factory=list)


class TestCase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    suite: str
    priority: Priority
    type: List[TestType]
    status: TcStatus
    owner: str
    created: str
    updated: str
    estimated_minutes: Optional[int] = None
    automation: AutomationInfo
    requirements: List[str] = Field(default_factory=list)
    pre_conditions: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    configurations: Optional[Configurations] = None
    open_defects: List[str] = Field(default_factory=list)
    # body content (markdown) — separate from frontmatter
    body: Optional[str] = None


class TestCaseListItem(BaseModel):
    """Lightweight projection — table listeleri için."""
    id: str
    title: str
    suite: str
    priority: Priority
    type: List[TestType]
    status: TcStatus
    automation_status: AutomationStatus
    owner: str
    last_run: Optional[str] = None
    last_status: Optional[TestStatus] = None
    open_defects_count: int = 0


class TestCaseListResponse(BaseModel):
    total: int
    items: List[TestCaseListItem]


class RunResult(BaseModel):
    tc: str
    tc_commit: str
    status: TestStatus
    duration_s: Optional[float] = None
    automation: Optional[str] = None
    defect: Optional[str] = None
    note: Optional[str] = None
    evidence: Optional[str] = None


class RunSummary(BaseModel):
    total: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    untested: int = 0


class RunEnvironment(BaseModel):
    branch: str
    commit: str
    browser: Optional[str] = None
    env: str
    url: Optional[str] = None


class TestRun(BaseModel):
    id: str
    plan: str
    started: str
    ended: str
    executor: str
    environment: RunEnvironment
    summary: RunSummary
    results: List[RunResult]


class TestRunListItem(BaseModel):
    id: str
    plan: str
    started: str
    executor: str
    summary: RunSummary


class CreateRunRequest(BaseModel):
    plan: str
    executor: str = "@web-ui"
    environment: RunEnvironment
    results: List[RunResult]


class Plan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    milestone: str
    owner: str
    created: str
    scope: dict
    exit_criteria: List[str]


class Requirement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    domain: str
    source: str
    external: Optional[str] = ""
    covered_by: List[str] = Field(default_factory=list)
    status: str


class PreCondition(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    setup_steps: List[str]
    teardown_steps: List[str] = Field(default_factory=list)


class CoverageMatrixRow(BaseModel):
    suite: str
    P0: int = 0
    P1: int = 0
    P2: int = 0
    P3: int = 0
    total: int
    automated: int
    automation_pct: int


class CoverageResponse(BaseModel):
    total_tcs: int
    automated_count: int
    automation_pct: int
    suites: List[CoverageMatrixRow]


class HealthComponent(BaseModel):
    score: int
    max: int
    note: str


class HealthReport(BaseModel):
    total: int
    max: int
    grade: Literal["A", "B", "C", "D", "F"]
    components: dict
    stats: dict
    generated_at: str


class CreateTestCaseRequest(BaseModel):
    suite: str
    title: str
    priority: Priority = "P2"
    type: List[TestType] = Field(default_factory=lambda: ["functional"])
    owner: str = "@web-ui"
    estimated_minutes: int = 5
    body: Optional[str] = None


class UpdateTestCaseRequest(BaseModel):
    title: Optional[str] = None
    priority: Optional[Priority] = None
    type: Optional[List[TestType]] = None
    status: Optional[TcStatus] = None
    owner: Optional[str] = None
    estimated_minutes: Optional[int] = None
    automation: Optional[AutomationInfo] = None
    requirements: Optional[List[str]] = None
    pre_conditions: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    body: Optional[str] = None


class OpenDefectIssueRequest(BaseModel):
    tc_id: str
    run_id: Optional[str] = None
    severity: Severity = "S2"
    title: str
    reproduce: str
    expected: str
    actual: str
    environment: Optional[str] = None


class OpenDefectIssueResponse(BaseModel):
    issue_number: Optional[int] = None
    issue_url: Optional[str] = None
    dry_run: bool = False
    message: str
