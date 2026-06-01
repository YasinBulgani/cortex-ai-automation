"""Pydantic schemas for Neurex Management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ManagementProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    key: str = Field(..., min_length=1, max_length=32)
    description: str = ""
    tspm_project_id: Optional[str] = None


class ManagementProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    tspm_project_id: Optional[str] = None
    name: str
    key: str
    description: Optional[str] = ""
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TestSuiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    order_index: int = 0


class TestSuiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    description: Optional[str] = ""
    order_index: int
    status: str
    created_at: datetime


class TestFolderCreate(BaseModel):
    suite_id: str
    name: str = Field(..., min_length=1, max_length=200)
    path: str = Field(..., min_length=1, max_length=1000)
    parent_id: Optional[str] = None
    order_index: int = 0


class TestFolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    suite_id: str
    parent_id: Optional[str] = None
    name: str
    path: str
    order_index: int
    created_at: datetime


class TestCaseStepIn(BaseModel):
    step_no: int = Field(..., ge=1)
    action: str = Field(..., min_length=1)
    expected_result: str = Field(..., min_length=1)
    test_data: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    is_required: bool = True


class TestCaseStepOut(TestCaseStepIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str


class TestCaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    case_key: Optional[str] = None
    objective: str = ""
    preconditions: str = ""
    test_data: dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"
    severity: str = "major"
    type: str = "functional"
    automation_status: str = "manual"
    status: str = "draft"
    source_type: str = "manual"
    source_ref: Optional[str] = None
    owner_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    steps: list[TestCaseStepIn] = Field(default_factory=list)


class TestCaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    objective: Optional[str] = None
    preconditions: Optional[str] = None
    test_data: Optional[dict[str, Any]] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    type: Optional[str] = None
    automation_status: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[str] = None
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None
    steps: Optional[list[TestCaseStepIn]] = None
    change_summary: str = "Manual update"


class TestCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    case_key: str
    title: str
    objective: Optional[str] = ""
    preconditions: Optional[str] = ""
    test_data: dict[str, Any]
    priority: str
    severity: str
    type: str
    automation_status: str
    status: str
    source_type: str
    source_ref: Optional[str] = None
    owner_id: Optional[str] = None
    tags: list[str]
    custom_fields: dict[str, Any]
    current_version: int
    last_run_status: Optional[str] = None
    last_run_at: Optional[datetime] = None
    archived: bool
    created_at: datetime
    updated_at: datetime
    steps: list[TestCaseStepOut] = Field(default_factory=list)


class TestCaseVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    version_no: int
    snapshot: dict[str, Any]
    change_summary: Optional[str] = None
    changed_fields: list[str]
    snapshot_size_bytes: int
    created_by: Optional[str] = None
    created_at: datetime


class RepositoryOut(BaseModel):
    suites: list[TestSuiteOut]
    folders: list[TestFolderOut]
    cases: list[TestCaseOut]


class TestPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    plan_type: str = "regression"
    release_name: Optional[str] = None
    scope_summary: Optional[str] = None


class TestPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    plan_type: str
    release_name: Optional[str] = None
    status: str
    scope_summary: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime


class TestCycleCreate(BaseModel):
    plan_id: str
    name: str = Field(..., min_length=1, max_length=200)
    environment: Optional[str] = None
    build_version: Optional[str] = None


class TestCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    name: str
    environment: Optional[str] = None
    build_version: Optional[str] = None
    status: str
    created_at: datetime


class RegressionSelectionFilter(BaseModel):
    priorities: list[str] = Field(default_factory=list)
    severities: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    suite_ids: list[str] = Field(default_factory=list)
    folder_ids: list[str] = Field(default_factory=list)
    include_last_failed: bool = True
    include_not_run: bool = True
    include_without_requirements: bool = False
    max_cases: int = Field(default=150, ge=1, le=1000)


class RegressionSetCaseIn(BaseModel):
    case_id: str
    order_index: int = 0
    risk_score: int = 0
    reason: str = "Manual selection"
    include_mode: str = "manual"


class RegressionSetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    set_type: str = "regression"
    description: Optional[str] = None
    filters: RegressionSelectionFilter = Field(default_factory=RegressionSelectionFilter)
    cases: list[RegressionSetCaseIn] = Field(default_factory=list)


class RegressionCandidateOut(BaseModel):
    case_id: str
    case_key: str
    title: str
    priority: str
    severity: str
    type: str
    status: str
    tags: list[str]
    last_run_status: Optional[str] = None
    risk_score: int
    reasons: list[str]


class RegressionSetCaseOut(BaseModel):
    id: str
    case_id: str
    case_version_no: int
    case_key: str
    title: str
    priority: str
    severity: str
    type: str
    last_run_status: Optional[str] = None
    order_index: int
    risk_score: int
    reason: Optional[str] = None
    include_mode: str


class RegressionSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    set_type: str
    description: Optional[str] = None
    source_filters: dict[str, Any]
    selection_summary: dict[str, Any]
    created_by: Optional[str] = None
    created_at: datetime
    cases: list[RegressionSetCaseOut] = Field(default_factory=list)


class TestRunCreate(BaseModel):
    cycle_id: str
    name: str = Field(..., min_length=1, max_length=300)
    case_ids: list[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None
    source_type: str = "manual"
    source_ref: Optional[str] = None
    scope_snapshot: dict[str, Any] = Field(default_factory=dict)


class TestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cycle_id: str
    name: str
    status: str
    source_type: str
    source_ref: Optional[str] = None
    scope_snapshot: dict[str, Any]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class StepResultUpdate(BaseModel):
    status: str
    actual_result: Optional[str] = None
    comment: Optional[str] = None

    @model_validator(mode="after")
    def require_actual_result_for_failed_or_blocked(self) -> "StepResultUpdate":
        if self.status in {"failed", "blocked"} and not (self.actual_result or "").strip():
            raise ValueError("Failed veya blocked adımda actual_result zorunlu.")
        return self


class StepResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_case_id: str
    step_no: int
    status: str
    actual_result: Optional[str] = None
    comment: Optional[str] = None
    executed_at: Optional[datetime] = None


class RunCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    case_id: str
    case_version_no: int
    case_snapshot: dict[str, Any] = Field(default_factory=dict)
    assigned_to: Optional[str] = None
    status: str
    actual_result: Optional[str] = None
    execution_notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    step_results: list[StepResultOut] = Field(default_factory=list)


class RunDetailOut(TestRunOut):
    """Extended run with nested run_cases (for execute screen)."""
    model_config = ConfigDict(from_attributes=True)

    run_cases: list[RunCaseOut] = Field(default_factory=list)


class ExecutionSummaryOut(BaseModel):
    total: int
    not_run: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    retest: int
    progress_pct: float
    pass_rate_pct: float


class ReleaseChecklistItem(BaseModel):
    label: str
    metric: str
    status: str


class ReleaseBlockerOut(BaseModel):
    label: str
    value: int
    detail: str


class ReleaseReportOut(BaseModel):
    project_id: str
    decision: str
    generated_at: datetime
    progress_pct: float
    pass_rate_pct: float
    requirement_coverage_pct: float
    stale_requirement_count: int
    uncovered_requirement_count: int
    open_defect_count: int
    oldest_open_defect_days: int
    active_run_count: int
    blockers: list[ReleaseBlockerOut] = Field(default_factory=list)
    checklist: list[ReleaseChecklistItem] = Field(default_factory=list)


class ReleaseSignoffCreate(BaseModel):
    release_name: Optional[str] = None
    decision: str = Field(..., min_length=1, max_length=32)
    status: str = "signed"
    comment: Optional[str] = None


class ReleaseSignoffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    release_name: Optional[str] = None
    decision: str
    status: str
    comment: Optional[str] = None
    report_snapshot: dict[str, Any]
    signed_by: Optional[str] = None
    signed_at: datetime
    created_at: datetime


class RequirementCreate(BaseModel):
    external_source: str = "internal"
    external_key: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "active"
    owner_id: Optional[str] = None
    url: Optional[str] = None
    source_updated_at: Optional[datetime] = None
    version_no: int = 1
    acceptance_criteria: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    external_source: str
    external_key: str
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    owner_id: Optional[str] = None
    url: Optional[str] = None
    source_updated_at: Optional[datetime] = None
    version_no: int
    acceptance_criteria: list[dict[str, Any]]
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class RequirementLinkCreate(BaseModel):
    requirement_id: Optional[str] = None
    case_id: str
    external_source: str = "internal"
    external_key: str = Field(..., min_length=1, max_length=200)
    title_snapshot: str = Field(..., min_length=1, max_length=500)
    url: Optional[str] = None
    source_updated_at: Optional[datetime] = None
    coverage_status: str = "covered"


class RequirementLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    requirement_id: Optional[str] = None
    case_id: str
    external_source: str
    external_key: str
    title_snapshot: str
    url: Optional[str] = None
    source_updated_at: Optional[datetime] = None
    coverage_status: str


class DefectLinkCreate(BaseModel):
    run_case_id: str
    step_result_id: Optional[str] = None
    external_source: str = "internal"
    external_key: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    status: str = "open"
    severity: str = "major"
    priority: str = "P2"
    assignee_id: Optional[str] = None
    root_cause: Optional[str] = None
    retest_status: str = "not_ready"
    url: Optional[str] = None


class DefectLinkUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    severity: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    root_cause: Optional[str] = None
    retest_status: Optional[str] = None
    url: Optional[str] = None


class DefectLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_case_id: str
    step_result_id: Optional[str] = None
    external_source: str
    external_key: str
    title: str
    status: str
    severity: str
    priority: str
    assignee_id: Optional[str] = None
    root_cause: Optional[str] = None
    retest_status: str
    url: Optional[str] = None
    resolved_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TestImportJobCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=500)
    mapping: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class TestImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    status: str
    mapping: dict[str, Any]
    totals: dict[str, Any]
    created_by: Optional[str] = None
    created_at: datetime


class ImportJobRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    row_no: int
    parsed_data: dict[str, Any]
    validation_errors: list[dict[str, Any]]
    status: str  # new | duplicate_candidate | conflict | invalid | ready
    conflict_key: Optional[str] = None


class ImportJobDetailOut(TestImportJobOut):
    """Extended import job with staging rows."""
    model_config = ConfigDict(from_attributes=True)

    rows: list[ImportJobRowOut] = Field(default_factory=list)


class EvidenceOut(BaseModel):
    """Evidence / artifact linked to a run-case."""
    id: str
    run_case_id: str
    step_result_id: Optional[str] = None
    filename: str
    content_type: str
    url: str
    uploaded_at: str


class TracedCase(BaseModel):
    """A single test case entry in the traceability matrix."""
    case_id: str
    case_key: Optional[str] = None
    title: str
    last_run_status: Optional[str] = None
    coverage_status: str  # coverage_status from the requirement link

class TraceabilityRow(BaseModel):
    """One requirement row in the traceability matrix."""
    requirement_key: str
    title: str
    source: str
    url: Optional[str] = None
    cases: list[TracedCase] = Field(default_factory=list)
    # Derived
    covered: bool = False
    stale: bool = False  # source_updated_at newer than case's last run


# ── Semantic search ───────────────────────────────────────────────────────────

class SimilarCaseQuery(BaseModel):
    """Input for semantic case similarity search."""
    query: str = Field(..., min_length=1, max_length=2000,
                       description="Natural-language description to match against test cases")
    k: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    min_score: float = Field(default=0.30, ge=0.0, le=1.0,
                              description="Minimum cosine similarity threshold (0–1)")
    exclude_case_id: Optional[str] = None


class SimilarCaseResult(BaseModel):
    """A test case match from semantic search."""
    case_id: str
    case_key: str
    title: str
    score: float
    project_id: str
    tags: list[str] = Field(default_factory=list)
    last_run_status: Optional[str] = None


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: Optional[str] = None
    actor_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    payload: dict[str, Any]
    created_at: datetime


class ManagementSettingsOut(BaseModel):
    project_id: str
    permissions: list[str]
    workflow_statuses: dict[str, list[str]]
    evidence_retention_days: dict[str, int]
    aggregation_policy: dict[str, Any]
    custom_field_usage: dict[str, Any]
