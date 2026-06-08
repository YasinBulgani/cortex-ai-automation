"""Pydantic schemas for Neurex Management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class PagedResponse(BaseModel, Generic[T]):
    """Standard paginated list response envelope.

    All list endpoints that support pagination return this shape::

        {
            "items": [...],
            "total": 42,
            "limit": 20,
            "offset": 0,
            "has_more": true
        }
    """

    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool


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


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    order_index: Optional[int] = None
    status: Optional[str] = Field(default=None, max_length=32)


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


class TestFolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    path: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    suite_id: Optional[str] = None
    parent_id: Optional[str] = None
    order_index: Optional[int] = None


class TestCaseStepIn(BaseModel):
    step_no: int = Field(..., ge=1)
    action: str = Field(..., min_length=1, max_length=5000)
    expected_result: str = Field(..., min_length=1, max_length=5000)
    test_data: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = Field(None, max_length=1000)
    is_required: bool = True


TestCaseStepCreate = TestCaseStepIn  # public alias used in tests and API consumers


class TestCaseStepOut(TestCaseStepIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str


class TestCaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    case_key: Optional[str] = None
    objective: Optional[str] = Field(None, max_length=2000)
    preconditions: Optional[str] = Field(None, max_length=2000)
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
    steps: list[TestCaseStepIn] = Field(default_factory=list, max_length=500)


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
    parent_id: Optional[str] = None
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
    sub_case_count: int = 0
    # Review workflow
    review_status: str = "none"
    review_by: Optional[str] = None
    review_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    # Flakiness tracking
    run_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    flakiness_score: float = 0.0


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


# ── Review Workflow Schemas ────────────────────────────────────────────────────

class CaseReviewSubmitRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=2000)


class CaseReviewActionRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=2000)


class CaseReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_key: str
    title: str
    review_status: str
    review_by: Optional[str] = None
    review_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    status: str
    updated_at: datetime


# ── Flakiness Schemas ─────────────────────────────────────────────────────────

class FlakyTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_key: str
    title: str
    suite_id: Optional[str] = None
    priority: str
    run_count: int
    pass_count: int
    fail_count: int
    flakiness_score: float
    last_run_status: Optional[str] = None
    last_run_at: Optional[datetime] = None


class FlakyTestsResponse(BaseModel):
    items: list[FlakyTestOut]
    total: int
    threshold: float


class RepositoryOut(BaseModel):
    suites: list[TestSuiteOut]
    folders: list[TestFolderOut]
    cases: list[TestCaseOut]


class TestPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    plan_type: str = "regression"
    status: str = "draft"
    release_name: Optional[str] = Field(None, max_length=100)
    scope_summary: Optional[str] = None


class TestPlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    status: Optional[str] = None
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
    name: str = Field(..., min_length=1, max_length=300)
    environment: Optional[str] = None
    build_version: Optional[str] = None


class TestCycleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    environment: Optional[str] = None
    build_version: Optional[str] = None
    status: Optional[str] = None


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
    risk_score: float = 0.0
    reason: str = "Manual selection"
    include_mode: str = "manual"


class RegressionSetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    set_type: str = "regression"
    description: Optional[str] = None
    filters: RegressionSelectionFilter = Field(default_factory=RegressionSelectionFilter)
    cases: list[RegressionSetCaseIn] = Field(default_factory=list)


class RegressionSetAddCases(BaseModel):
    case_ids: list[str]


class RegressionSetRemoveCase(BaseModel):
    case_id: str


class RegressionSetUpdate(BaseModel):
    name: Optional[str] = None
    set_type: Optional[str] = None
    description: Optional[str] = None


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
    risk_score: float
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
    risk_score: float
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
    cycle_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=300)
    case_ids: list[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None
    source_type: str = "manual"
    source_ref: Optional[str] = None
    scope_snapshot: dict[str, Any] = Field(default_factory=dict)
    environment: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TestRunUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    status: Optional[str] = None
    environment: Optional[str] = None


class RequirementLinkUpdate(BaseModel):
    coverage_status: Optional[str] = None
    title_snapshot: Optional[str] = Field(default=None, min_length=1, max_length=500)
    url: Optional[str] = None


class StepResultUpdate(BaseModel):
    status: str
    actual_result: Optional[str] = None
    comment: Optional[str] = None

    @model_validator(mode="after")
    def require_actual_result_for_failed_or_blocked(self) -> StepResultUpdate:
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


class RunCaseUpdate(BaseModel):
    """Patch the overall status of a test run case (TestRail-style case-level result)."""

    status: str
    actual_result: Optional[str] = None
    execution_notes: Optional[str] = None


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


class TestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cycle_id: str
    name: str
    status: str
    source_type: str
    source_ref: Optional[str] = None
    scope_snapshot: dict[str, Any] = Field(default_factory=dict)
    environment: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


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
    role: Optional[str] = None
    decision: str = Field(..., min_length=1, max_length=32)
    status: str = "signed"
    comment: Optional[str] = None


class ReleaseSignoffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    release_name: Optional[str] = None
    role: Optional[str] = None
    decision: str
    status: str
    comment: Optional[str] = None
    report_snapshot: dict[str, Any]
    signed_by: Optional[str] = None
    signed_at: datetime
    created_at: datetime


class RequirementCreate(BaseModel):
    external_source: str = "internal"
    external_key: Optional[str] = Field(default=None, max_length=200)
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


class RequirementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[list[str]] = None
    acceptance_criteria: Optional[list[dict[str, Any]]] = None


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
    case_id: Optional[str] = None
    external_source: str = "internal"
    external_key: Optional[str] = Field(default=None, max_length=200)
    title_snapshot: Optional[str] = Field(default=None, max_length=500)
    title: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "active"
    url: Optional[str] = None
    source_updated_at: Optional[datetime] = None
    coverage_status: str = "covered"
    tags: list[str] = Field(default_factory=list)


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
    run_case_id: Optional[str] = None
    step_result_id: Optional[str] = None
    external_source: str = "internal"
    external_key: Optional[str] = Field(default=None, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    status: str = "open"
    severity: str = "major"
    priority: str = "P2"
    assignee_id: Optional[str] = None
    root_cause: Optional[str] = None
    retest_status: str = "not_ready"
    url: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None


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
    run_case_id: Optional[str] = None
    step_result_id: Optional[str] = None
    external_source: str
    external_key: Optional[str] = None
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
    requirement_id: Optional[str] = None
    requirement_key: str
    external_key: str = ""
    title: str
    status: str = "active"
    priority: str = "medium"
    source: str
    url: Optional[str] = None
    cases: list[TracedCase] = Field(default_factory=list)
    # Derived
    covered: bool = False
    stale: bool = False  # source_updated_at newer than case's last run
    coverage_pct: float = 0.0


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
    # Kullanıcı tarafından özelleştirilebilen proje ayarları
    user_settings: dict[str, Any] = Field(default_factory=dict)


class ManagementUserSettingsUpdate(BaseModel):
    """Proje bazında özelleştirilebilir ayarlar — isteğe bağlı alanlar."""
    default_priority: Optional[str] = None
    default_type: Optional[str] = None
    case_key_prefix: Optional[str] = None
    case_key_format: Optional[str] = None
    modules: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    notifications: Optional[dict[str, bool]] = None
    roles: Optional[list[dict[str, Any]]] = None
    sso_config: Optional[dict[str, Any]] = None
    webhook_notifications: Optional[list[dict[str, Any]]] = None
    cicd_webhook: Optional[dict[str, Any]] = None
    api_keys: Optional[list[dict[str, Any]]] = None
    design_templates: Optional[dict[str, list[dict[str, Any]]]] = None


class WebhookTestRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    secret: Optional[str] = Field(default=None, max_length=512)
    payload: dict[str, Any] = Field(default_factory=dict)


class WebhookTestResponse(BaseModel):
    ok: bool
    status_code: Optional[int] = None
    message: str


class SsoTestRequest(BaseModel):
    entity_id: str = Field(..., min_length=1, max_length=512)
    sso_url: str = Field(..., min_length=1, max_length=2048)


class SsoTestResponse(BaseModel):
    ok: bool
    status_code: Optional[int] = None
    message: str


class ProjectApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    expires_at: Optional[datetime] = None


class ProjectApiKeyOut(BaseModel):
    id: str
    name: str
    masked_key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class ProjectApiKeyCreated(ProjectApiKeyOut):
    key: str


# ── M-50 Threaded Comments ───────────────────────────────────────────────────

ALLOWED_COMMENT_ENTITY_TYPES: set[str] = {
    "case",
    "defect",
    "plan",
    "run",
    "requirement",
}


class MgmtCommentCreate(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=64)
    entity_id: str = Field(..., min_length=1)
    body_md: str = Field(..., min_length=1, max_length=20000)
    parent_id: Optional[str] = None
    mentions: list[str] = Field(default_factory=list)
    project_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate_entity_type(self) -> MgmtCommentCreate:
        if self.entity_type not in ALLOWED_COMMENT_ENTITY_TYPES:
            raise ValueError(
                f"entity_type must be one of {sorted(ALLOWED_COMMENT_ENTITY_TYPES)}"
            )
        return self


class MgmtCommentUpdate(BaseModel):
    body_md: str = Field(..., min_length=1, max_length=20000)
    mentions: Optional[list[str]] = None


class MgmtCommentReact(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=32)
    add: bool = True


class MgmtCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: Optional[str] = None
    entity_type: str
    entity_id: str
    author_id: Optional[str] = None
    parent_id: Optional[str] = None
    body_md: str
    mentions: list[str] = Field(default_factory=list)
    reactions: dict[str, list[str]] = Field(default_factory=dict)
    edited_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    created_at: datetime


# ── M-45 Notification Inbox ──────────────────────────────────────────────────

ALLOWED_NOTIFICATION_KINDS: set[str] = {
    "mention",
    "assignment",
    "sla_breach",
    "comment_reply",
    "review_request",
    "system",
}


ALLOWED_NOTIFICATION_CHANNELS: set[str] = {"in_app", "email", "push", "slack", "teams"}


class MgmtNotificationCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=256)
    body: str = Field(default="", max_length=4000)
    link_path: Optional[str] = Field(default=None, max_length=512)
    severity: str = Field(default="info", max_length=16)
    channel: str = Field(default="in_app", max_length=32)
    project_id: Optional[str] = None
    source_trace: dict[str, Any] = Field(default_factory=dict)


class MgmtNotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    user_id: str
    project_id: Optional[str] = None
    kind: str
    title: str
    body: str
    link_path: Optional[str] = None
    severity: str
    channel: str = "in_app"
    source_trace: dict[str, Any] = Field(default_factory=dict)
    read_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime


class NotificationUnreadCount(BaseModel):
    unread: int
    total: int


# ── M-1 / M-2 / M-9 Test Design Techniques ───────────────────────────────────

ALLOWED_TECHNIQUES: set[str] = {"BVA", "EQ", "DT", "STD", "PAIRWISE", "CEG"}
ALLOWED_DATA_TYPES: set[str] = {"int", "float", "string", "date", "bool", "enum"}


class DesignFieldSpec(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    data_type: str = Field(..., max_length=32)
    min_value: Optional[str] = Field(default=None, max_length=128)
    max_value: Optional[str] = Field(default=None, max_length=128)
    allowed_set: Optional[list[Any]] = None
    nullable: bool = False

    @model_validator(mode="after")
    def _validate_type(self) -> DesignFieldSpec:
        if self.data_type not in ALLOWED_DATA_TYPES:
            raise ValueError(f"data_type must be one of {sorted(ALLOWED_DATA_TYPES)}")
        return self


class BvaRunCreate(BaseModel):
    project_id: Optional[str] = None
    requirement_id: Optional[str] = None
    fields: list[DesignFieldSpec] = Field(..., min_length=1)
    requirement_text: str = ""


class EqRunCreate(BaseModel):
    project_id: Optional[str] = None
    requirement_id: Optional[str] = None
    fields: list[DesignFieldSpec] = Field(..., min_length=1)
    requirement_text: str = ""


class DtRunCreate(BaseModel):
    project_id: Optional[str] = None
    requirement_id: Optional[str] = None
    # Accept either structured DesignFieldSpec list OR human-readable conditions + actions
    fields: Optional[list[DesignFieldSpec]] = None
    conditions: Optional[list[str]] = None
    actions: Optional[list[str]] = None
    requirement_text: str = ""

    def effective_fields(self) -> list[DesignFieldSpec]:
        """Convert conditions (strings) to bool DesignFieldSpec for the service."""
        if self.fields:
            return self.fields
        conds = [c.strip() for c in (self.conditions or []) if c.strip()]
        if not conds:
            raise ValueError("DT run requires at least one condition or field")
        return [DesignFieldSpec(name=c, data_type="bool") for c in conds]


class PairwiseRunCreate(BaseModel):
    project_id: Optional[str] = None
    requirement_id: Optional[str] = None
    fields: list[DesignFieldSpec] = Field(..., min_length=2, max_length=20)
    requirement_text: str = ""


class GeneratedCaseDraft(BaseModel):
    name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected: str = ""
    boundary_type: Optional[str] = None
    # boundary_type: min | max | just_inside | just_outside | nominal | invalid
    rationale: Optional[str] = None
    partition_label: Optional[str] = None
    field_name: Optional[str] = None


class DesignPartitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    partition_label: str
    is_valid: bool
    sample_value: Optional[str] = None


class DesignRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: Optional[str] = None
    requirement_id: Optional[str] = None
    technique: str
    input_spec: dict[str, Any] = Field(default_factory=dict)
    generated_cases: list[GeneratedCaseDraft] = Field(default_factory=list)
    source: str
    llm_trace_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    partitions: list[DesignPartitionOut] = Field(default_factory=list)


class PromoteCasesRequest(BaseModel):
    case_indexes: list[int] = Field(..., min_length=1)
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None


class PromoteCasesResponse(BaseModel):
    case_ids: list[str]


class CaseParamSetCreate(BaseModel):
    case_id: str
    schema_json: dict[str, Any] = Field(default_factory=dict)
    # schema_json: {fields:[{name,type,required}]}


class CaseParamSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    case_id: str
    schema_json: dict[str, Any]
    created_by: Optional[str] = None
    created_at: datetime


class CaseDataRowIn(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    source_type: str = "manual"
    category: Optional[str] = None


class CaseDataRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    param_set_id: str
    values: dict[str, Any]
    expected: dict[str, Any]
    source_type: str
    category: Optional[str] = None
    created_at: datetime


class CaseDataGenerateRequest(BaseModel):
    param_set_id: str
    source: str = "llm"  # llm | csv
    count: int = Field(default=5, ge=1, le=200)
    csv_content: Optional[str] = None


class ExpandCaseResponse(BaseModel):
    execution_ids: list[str]
    run_case_ids: list[str] = Field(default_factory=list)


# ── AI Test Üretimi ───────────────────────────────────────────────────────────

class BulkUpdateCasesRequest(BaseModel):
    case_ids: list[str] = Field(..., min_length=1)
    priority: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    tags_add: list[str] = Field(default_factory=list)
    tags_remove: list[str] = Field(default_factory=list)


class BulkUpdateCasesResponse(BaseModel):
    updated: int
    failed: int = 0


# Alias — task gereksinimi ve geriye dönük uyumluluk için
BulkCaseUpdate = BulkUpdateCasesRequest


class TestCaseGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=2000, description="Test senaryosu üretmek için açıklama")
    count: int = Field(default=5, ge=1, le=20)
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    priority: str = "medium"
    type: str = "manual"
    save: bool = Field(default=False, description="True ise üretilen case'ler DB'ye kaydedilir")


class GeneratedStepOut(BaseModel):
    step_no: int
    action: str
    expected_result: str
    is_required: bool = True


class GeneratedCaseOut(BaseModel):
    title: str
    objective: str
    preconditions: str
    priority: str
    tags: list[str]
    steps: list[GeneratedStepOut]
    saved_id: Optional[str] = None


class TestCaseGenerateResponse(BaseModel):
    cases: list[GeneratedCaseOut]


# ── Case Clone ────────────────────────────────────────────────────────────────

class TestCaseCloneRequest(BaseModel):
    title: Optional[str] = None
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None


class TestPlanAIGenerateRequest(BaseModel):
    release_name: str = Field(default="Next Release", min_length=1, max_length=200)
    goal: Optional[str] = Field(default=None, max_length=500)
    plan_type: str = "regression"
    objective: Optional[str] = Field(default=None, max_length=1000)
    risk_areas: list[str] = Field(default_factory=list)
    coverage_target: float = 0.8


class TestPlanAIGenerateResponse(BaseModel):
    name: str
    scope_summary: str
    suggested_suite_ids: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class TestCaseImproveRequest(BaseModel):
    focus: str = Field(default="all", description="all | steps | title | preconditions")


class TestCaseImproveResponse(BaseModel):
    title: Optional[str] = None
    objective: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[list[GeneratedStepOut]] = None
    suggestions: list[str] = Field(default_factory=list)


# ── Shared Steps ──────────────────────────────────────────────────────────────

class SharedStepItem(BaseModel):
    step_no: int
    action: str = Field(..., min_length=1)
    expected_result: str = ""
    notes: Optional[str] = None
    is_required: bool = True


class SharedStepCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    steps: list[SharedStepItem] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SharedStepUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    steps: Optional[list[SharedStepItem]] = None
    tags: Optional[list[str]] = None


class SharedStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    steps: list[dict[str, Any]]
    tags: list[str]
    usage_count: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Webhook Subscriptions ────────────────────────────────────────────────────

class WebhookSubscription(BaseModel):
    id: str  # uuid
    url: str
    events: list[str]  # ["run.completed", "case.failed", ...]
    secret: Optional[str] = None
    active: bool = True
    created_at: str


class WebhookSubscriptionCreate(BaseModel):
    url: str
    events: list[str]
    secret: Optional[str] = None


# ── Standup ───────────────────────────────────────────────────────────────────

class QualityScanResult(BaseModel):
    case_id: str
    case_key: str
    title: str
    issues: list[str]
    score: int
    recommendation: str


class QualityScanResponse(BaseModel):
    total: int
    scanned: int
    issues_found: int
    results: list[QualityScanResult]


class DefectRootCauseRequest(BaseModel):
    defect_title: str = Field(..., min_length=1)
    defect_status: Optional[str] = None
    test_context: Optional[str] = None


class DefectRootCauseResponse(BaseModel):
    root_cause: str
    suggestions: list[str] = Field(default_factory=list)
    category: Optional[str] = None


class StandupAnomaly(BaseModel):
    severity: str
    title: str


class CaseDependencyCreate(BaseModel):
    depends_on_id: str
    dep_type: str = "blocks"


class CaseDependencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    depends_on_id: str
    dep_type: str
    depends_on_key: str = ""   # populated from join
    depends_on_title: str = ""
    created_at: datetime


class StandupOut(BaseModel):
    health_score: float
    summary_health: str
    eta_hours: Optional[float]
    remaining_cases: int
    total_cases: int
    completed_cases: int
    pass_rate: float
    blocked: int
    failed: int
    velocity_per_hour: float
    anomalies: list[StandupAnomaly]
    run_name: str
    predicted_completion: Optional[str]
    will_meet_gate: bool
    blocking_factors: list[str]


class PlanImpactSummary(BaseModel):
    plan_id: str
    plan_name: str
    cycle_count: int
    run_count: int
    run_case_count: int
    evidence_count: int
