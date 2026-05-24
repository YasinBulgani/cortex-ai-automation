"""TSPM Pydantic schemas."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.domains.tspm.product_registry import (
    DEFAULT_PRODUCT_ID,
    default_entry_key_for,
    normalize_product_tags,
    validate_product_id,
)

ProvenanceKind = Literal["real", "simulated", "fallback", "stub"]
ArtifactTarget = Literal["shared", "playwright", "maviyaka"]
ValidationStatus = Literal["pending", "validated", "failed", "not_applicable"]

# ── Güvenlik yardımcıları ─────────────────────────────────────────────

_TAG_RE = re.compile(r"<[^>]+>")  # HTML tag pattern
# PostgreSQL TEXT sütunları NUL (0x00) karakterini kabul etmez; input temizliği
# olmadan DB seviyesinde 500 hatası doğar (information leak + kararlılık sorunu).
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _strip_html(value: str) -> str:
    """HTML/script tag'lerini temizler + kontrol karakterlerini (NUL vs.) siler.

    Not: Bu bir "storage sanitizer"dır — output encoding'in yerine geçmez.
    Yalnızca DB bütünlüğünü ve NUL byte injection gibi saldırıları engeller.
    """
    cleaned = _TAG_RE.sub("", value)
    cleaned = _CONTROL_RE.sub("", cleaned)
    return cleaned.strip()


# ── Projects ──────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    base_url: str = Field(default="", max_length=500)
    primary_product_id: str = DEFAULT_PRODUCT_ID
    product_tags: list[str] = Field(default_factory=list)
    default_entry_key: Optional[str] = None

    @field_validator("name", "description", "base_url", mode="before")
    @classmethod
    def sanitize_html(cls, v: str) -> str:
        return _strip_html(str(v)) if v else ""

    @field_validator("primary_product_id")
    @classmethod
    def validate_primary_product(cls, v: str) -> str:
        return validate_product_id(v)

    @field_validator("product_tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        return normalize_product_tags(v)

    def resolved_default_entry_key(self) -> str:
        return self.default_entry_key or default_entry_key_for(self.primary_product_id)


class ProjectUpdate(ProjectCreate):
    pass


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    archived: bool
    base_url: str = ""
    primary_product_id: str = DEFAULT_PRODUCT_ID
    product_tags: list[str] = Field(default_factory=list)
    default_entry_key: Optional[str] = None
    # None = hiç açılmadı. Ana sayfada "son açılan" sıralaması için kullanılır.
    last_opened_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class RecentProjectSummary(BaseModel):
    """Ana sayfa 'Son Açılan Proje' kartı için zengin özet.

    Tek çağrıyla projenin kendisi + en son koşumun minimum bilgisini döner
    ki landing page N+1 istek yapmak zorunda kalmasın.
    """
    project: ProjectOut
    last_run_id: Optional[str] = None
    last_run_status: Optional[str] = None      # running | completed | failed | cancelled …
    last_run_created_at: Optional[datetime] = None
    last_run_passed: int = 0
    last_run_failed: int = 0
    last_run_total: int = 0
    last_run_simulated: bool = False


# ── Dashboard ─────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    scenario_count: int = 0
    pending_approvals: int = 0
    import_count: int = 0
    ai_run_pending: int = 0
    execution_count: int = 0
    latest_run_pass_rate: Optional[float] = None


# ── Global Dashboard ──────────────────────────────────────────────────

class GlobalDashboardProjectRow(BaseModel):
    id: str
    name: str
    scenario_count: int = 0
    last_run: Optional[str] = None
    pass_rate: Optional[float] = None
    status: str = "active"

class GlobalDashboardActivity(BaseModel):
    actor: str
    action: str
    time: str
    resource_type: str = ""
    resource_id: Optional[str] = None

class WeeklyTrendPoint(BaseModel):
    day: str
    runs: int = 0
    passed: int = 0

class GlobalDashboardOut(BaseModel):
    total_projects: int = 0
    total_scenarios: int = 0
    active_executions: int = 0
    overall_pass_rate: float = 0.0
    pending_approvals: int = 0
    weekly_trend: list[WeeklyTrendPoint] = []
    projects: list[GlobalDashboardProjectRow] = []
    activities: list[GlobalDashboardActivity] = []


# ── Scenarios ─────────────────────────────────────────────────────────

_VALID_STATUSES = {"draft", "active", "deprecated", "pending", "approved", "rejected"}


class ScenarioCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    status: str = "draft"
    steps: list[dict[str, Any]] = Field(default=[], max_length=200)  # maks 200 adım
    tags: list[str] = Field(default=[], max_length=30)              # maks 30 tag

    @field_validator("title", "description", mode="before")
    @classmethod
    def sanitize_html(cls, v: str) -> str:
        return _strip_html(str(v)) if v else ""

    @field_validator("tags", mode="before")
    @classmethod
    def sanitize_tags(cls, v: list) -> list:
        if not isinstance(v, list):
            return []
        return [_strip_html(str(t))[:50] for t in v[:30] if t]

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_STATUSES:
            return "draft"
        return v


class ScenarioUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[str] = None
    steps: Optional[list[dict[str, Any]]] = None
    tags: Optional[list[str]] = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def sanitize_html(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _strip_html(str(v))

    @field_validator("tags", mode="before")
    @classmethod
    def sanitize_tags(cls, v: Optional[list]) -> Optional[list]:
        if v is None:
            return None
        if not isinstance(v, list):
            return []
        return [_strip_html(str(t))[:50] for t in v[:30] if t]

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in _VALID_STATUSES:
            raise ValueError(f"Geçersiz status: {v!r}. Geçerli değerler: {_VALID_STATUSES}")
        return v

class ScenarioOut(BaseModel):
    id: str
    title: str
    status: str
    current_version: int
    description: Optional[str] = None
    steps: Optional[list[dict[str, Any]]] = None
    tags: list[str] = []
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class BulkDeleteRequest(BaseModel):
    ids: list[str]


# ── Executions ────────────────────────────────────────────────────────

class ExecutionCreate(BaseModel):
    name: str = ""
    scenario_ids: list[str] = []
    platform: Optional[str] = None
    device_name: Optional[str] = None
    app_upload_id: Optional[str] = None

class ExecutionOut(BaseModel):
    id: str
    name: str
    status: str
    created_at: Optional[datetime] = None
    scenario_total: int = 0
    passed_count: int = 0
    failed_count: int = 0
    platform: Optional[str] = None
    device_name: Optional[str] = None
    app_upload_id: Optional[str] = None
    # Gerçek Playwright koşumu mu, engine down → simülasyon mu? UI bu
    # bayrağı rozetle göstererek "sonuç güvenilir" ilüzyonunu önler.
    simulated: bool = False
    model_config = {"from_attributes": True}

class ExecutionResultOut(BaseModel):
    id: str
    scenario_id: str
    scenario_title: str = ""
    status: str
    note: Optional[str] = None
    model_config = {"from_attributes": True}

class ExecutionDetailOut(BaseModel):
    id: str
    name: str
    status: str
    created_at: Optional[datetime] = None
    results: list[ExecutionResultOut] = []
    platform: Optional[str] = None
    device_name: Optional[str] = None
    app_upload_id: Optional[str] = None
    simulated: bool = False
    model_config = {"from_attributes": True}

class ResultStatusUpdate(BaseModel):
    status: str

class ExecutionStatusUpdate(BaseModel):
    # Manuel tamamlama / iptal için kullanılır. Backend yalnızca whitelist kabul eder.
    status: Literal["completed", "cancelled"]

class RerunRequest(BaseModel):
    pass


# ── Mobile Run ────────────────────────────────────────────────────────

class MobileRunCreate(BaseModel):
    """Paralel mobil koşum isteği."""
    device_names: list[str] = Field(min_length=1)
    scenario_ids: list[str] = []
    browser: str = "chromium"
    tags: str = ""
    base_url: str = ""
    app_upload_id: Optional[str] = None

class MobileRunOut(BaseModel):
    """Paralel mobil koşum yanıtı."""
    run_id: str
    device_slugs: list[str]
    device_run_ids: dict[str, str] = {}
    execution_ids: dict[str, str] = {}
    stream_url: str


# ── Flows ─────────────────────────────────────────────────────────────

class FlowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)
    # Frontend flow-designer create payload (template_id, agent_type, tags)
    template_id: Optional[str] = Field(default=None, max_length=128)
    agent_type: Optional[str] = Field(default=None, max_length=64)
    tags: list[str] = Field(default_factory=list)

class FlowOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    template_id: Optional[str] = None
    agent_type: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class FlowGraphUpdate(BaseModel):
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

class FlowDetailOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    model_config = {"from_attributes": True}


# ── Regression Sets ───────────────────────────────────────────────────

class RegressionSetCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""

class RegressionSetOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    scenario_count: int = 0
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class RegressionSetDetailOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    scenario_ids: list[str] = []
    scenarios: list[ScenarioOut] = []
    model_config = {"from_attributes": True}

class AddScenariosRequest(BaseModel):
    scenario_ids: list[str]


class RegressionSuggestRequest(BaseModel):
    extra_instructions: str = ""

class SuggestedSet(BaseModel):
    name: str
    description: str = ""
    scenario_ids: list[str] = []
    priority: str = "medium"

class RegressionSuggestResponse(BaseModel):
    sets: list[SuggestedSet] = []

class AcceptSuggestedSetsRequest(BaseModel):
    sets: list[SuggestedSet]


# ── Approvals ─────────────────────────────────────────────────────────

class ApprovalCreate(BaseModel):
    source_text: str = ""
    draft_payload: dict[str, Any] = Field(default_factory=dict)
    source_batch_id: Optional[str] = None
    source_test_case_id: Optional[str] = None
    # Convenience: top-level title falls back to draft_payload.title
    title: Optional[str] = None

class ApprovalOut(BaseModel):
    id: str
    title: str
    status: str
    scenario_id: Optional[str] = None
    source_text: Optional[str] = None
    draft_payload: Optional[dict[str, Any]] = None
    source_batch_id: Optional[str] = None
    source_test_case_id: Optional[str] = None
    decision_note: Optional[str] = None
    decision_trace: dict[str, Any] = {}
    created_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class DecideRequest(BaseModel):
    decision: str  # "approved" | "rejected"
    notes: str = ""


# ── BDD Generation ────────────────────────────────────────────────────

class BddGenerateRequest(BaseModel):
    analysis_text: str = Field(min_length=10)
    extra_instructions: str = ""

class BddGeneratedScenario(BaseModel):
    title: str
    description: str = ""
    feature: str = ""
    gherkin: str = ""
    tags: list[str] = []
    # steps[*] opsiyonel şu alanları taşıyabilir (DSL grounding post-process):
    #   - dsl_action_id: str  (katalogdaki eşleşen action id)
    #   - dsl_score: float    (snap skoru 0-1)
    #   - dsl_canonical: str  (yer tutuculu kanonik kalıp)
    steps: list[dict[str, Any]] = []
    # Aggregate: bu senaryodaki step'lerin yüzde kaçı DSL kataloğuna snap oldu.
    dsl_coverage: float = 0.0

class BddGenerateResponse(BaseModel):
    scenarios: list[BddGeneratedScenario] = []

class BddSaveRequest(BaseModel):
    scenarios: list[BddGeneratedScenario]


# ── BDD Generation (Enhanced) ─────────────────────────────────────────

class EnhancedBddGenerateRequest(BaseModel):
    requirement_id: str = Field(min_length=1)
    options: Optional[dict[str, Any]] = None

class BddScenarioItem(BaseModel):
    title: str
    feature_name: str = ""
    gherkin: str = ""
    # steps[*] ek alanlar (bkz. BddGeneratedScenario):
    #   dsl_action_id, dsl_score, dsl_canonical
    steps: list[dict[str, Any]] = []
    tags: list[str] = []
    scenario_type: str = "happy_path"
    step_reuse_rate: float = 0.0
    quality_score: float = 0.0
    # DSL katalog uyumu (0-1): kaç step'in hazır kalıba snap edildiği.
    dsl_coverage: float = 0.0

class EnhancedBddGenerateResponse(BaseModel):
    requirement_id: str
    requirement_title: str = ""
    scenarios: list[BddScenarioItem] = []
    step_library_size: int = 0
    avg_step_reuse: float = 0.0
    # DSL katalog kapsama oranı (0-1). step_library boş olsa bile anlamlıdır.
    avg_dsl_coverage: float = 0.0
    dsl_catalog_size: int = 0
    generation_model: str = ""
    duration_ms: float = 0.0

class BulkBddRequest(BaseModel):
    requirement_ids: list[str] = Field(min_length=1)
    options: Optional[dict[str, Any]] = None

class BulkBddResultItem(BaseModel):
    requirement_id: str
    requirement_title: str = ""
    scenarios: list[BddScenarioItem] = []
    error: Optional[str] = None

class BulkBddResponse(BaseModel):
    requirement_count: int = 0
    results: list[BulkBddResultItem] = []
    total_scenarios: int = 0
    total_duration_ms: float = 0.0

class EdgeCaseSuggestion(BaseModel):
    scenario_type: str = ""
    title: str = ""
    description: str = ""
    gherkin: str = ""
    rationale: str = ""

class EdgeCaseRequest(BaseModel):
    requirement_id: str = Field(min_length=1)

class EdgeCaseResponse(BaseModel):
    requirement_id: str
    existing_scenario_count: int = 0
    suggestions: list[EdgeCaseSuggestion] = []

class StepUsageItem(BaseModel):
    step: str
    count: int

class StepLibraryResponse(BaseModel):
    total_steps: int = 0
    given_steps: list[str] = []
    when_steps: list[str] = []
    then_steps: list[str] = []
    and_steps: list[str] = []
    most_used: list[StepUsageItem] = []

class GherkinValidateRequest(BaseModel):
    gherkin: str = Field(min_length=1)

class GherkinValidateResponse(BaseModel):
    valid: bool = False
    errors: list[str] = []
    warnings: list[str] = []


# ── Imports ───────────────────────────────────────────────────────────

class ImportCreate(BaseModel):
    filename: str
    raw_text: str = ""

class ImportOut(BaseModel):
    id: str
    filename: str
    status: str
    scenario_count: int = 0
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Requirements & Coverage ──────────────────────────────────────────

_VALID_PRIORITIES = {"low", "medium", "high", "critical"}


class RequirementCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    priority: str = "medium"
    source: Optional[str] = Field(default=None, max_length=200)

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in _VALID_PRIORITIES:
            return "medium"
        return v

class RequirementUpdate(BaseModel):
    external_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    source: Optional[str] = None

class RequirementOut(BaseModel):
    id: str
    external_id: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    source: Optional[str] = None
    scenario_count: int = 0
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class LinkRequirementRequest(BaseModel):
    requirement_ids: list[str]

class CoverageMatrixRow(BaseModel):
    requirement_id: str
    external_id: str
    title: str
    scenario_ids: list[str] = []

class CoverageMatrixOut(BaseModel):
    rows: list[CoverageMatrixRow] = []
    total_requirements: int = 0
    covered_count: int = 0
    coverage_percent: float = 0.0


# ── Scenario Versions ────────────────────────────────────────────────

class ScenarioVersionOut(BaseModel):
    id: str
    scenario_id: str
    version_number: int
    title: str
    description: Optional[str] = None
    steps: Optional[list[dict[str, Any]]] = None
    status: str = "draft"
    changed_by: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class ScenarioVersionDiff(BaseModel):
    v1: int
    v2: int
    title_changed: bool = False
    description_changed: bool = False
    steps_changed: bool = False
    status_changed: bool = False
    v1_snapshot: Optional[ScenarioVersionOut] = None
    v2_snapshot: Optional[ScenarioVersionOut] = None


# ── Execution Trends & Stats ─────────────────────────────────────────

class TrendDataPoint(BaseModel):
    date: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0

class ExecutionTrendsOut(BaseModel):
    days: int = 30
    data_points: list[TrendDataPoint] = []

class ExecutionStatsOut(BaseModel):
    total_executions: int = 0
    total_scenarios_run: int = 0
    avg_pass_rate: float = 0.0
    last_execution_at: Optional[datetime] = None

class FlakyTestOut(BaseModel):
    scenario_id: str
    scenario_title: str = ""
    flip_count: int = 0
    last_results: list[str] = []


# ── Schedules ────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1)
    cron_expression: str = Field(min_length=1)
    regression_set_id: Optional[str] = None
    scenario_ids: list[str] = []
    is_active: bool = True
    platform: Optional[str] = None      # "ios" | "android" — mobil koşum
    device_name: Optional[str] = None   # "iPhone 14" vb.

class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    regression_set_id: Optional[str] = None
    scenario_ids: Optional[list[str]] = None
    is_active: Optional[bool] = None
    platform: Optional[str] = None
    device_name: Optional[str] = None

class ScheduleOut(BaseModel):
    id: str
    name: str
    cron_expression: str
    regression_set_id: Optional[str] = None
    scenario_ids: list[str] = []
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    platform: Optional[str] = None
    device_name: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Test Data Sets ───────────────────────────────────────────────────

class TestDataSetCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    columns: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

class TestDataSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    columns: Optional[list[dict[str, Any]]] = None
    rows: Optional[list[dict[str, Any]]] = None

class TestDataSetOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    columns: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class DataBindingCreate(BaseModel):
    data_set_id: str
    parameter_mapping: dict[str, Any] = {}

class DataBindingOut(BaseModel):
    id: str
    scenario_id: str
    data_set_id: str
    parameter_mapping: dict[str, Any] = {}
    model_config = {"from_attributes": True}

class ExpandedStep(BaseModel):
    order: int = 0
    keyword: str = ""
    text: str = ""

class ExpandedScenarioRow(BaseModel):
    row_index: int
    steps: list[ExpandedStep] = []

class ExpandedScenarioOut(BaseModel):
    scenario_id: str
    title: str
    expanded_rows: list[ExpandedScenarioRow] = []


# ── Integrations ─────────────────────────────────────────────────────

class IntegrationCreate(BaseModel):
    provider: str = Field(min_length=1)
    config: dict[str, Any] = {}
    is_active: bool = True

class IntegrationUpdate(BaseModel):
    provider: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None

class IntegrationOut(BaseModel):
    id: str
    provider: str
    config: dict[str, Any] = {}
    is_active: bool = True
    last_sync_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class SyncResultOut(BaseModel):
    synced_count: int = 0
    message: str = ""
    # Sync henüz gerçek bir provider ile entegre edilmediğinde `stub: true`
    # döner. UI bu bayrağı görünce "bekleyen özellik" rozetiyle kullanıcıyı
    # uyarmalı ve başarıyla eşzamanlama yapılmış gibi davranmamalıdır.
    stub: bool = False
    provider: Optional[str] = None


# ── API Testing ──────────────────────────────────────────────────────

class ApiCollectionCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    base_url: str = ""
    headers: dict[str, Any] = {}


class PostmanImportRequest(BaseModel):
    collection: dict[str, Any]
    name: Optional[str] = None
    base_url: Optional[str] = None
    folder_prefix: str = ""

class ApiRequestCreate(BaseModel):
    name: str = Field(min_length=1)
    method: str = "GET"
    path: str = "/"
    headers: dict[str, Any] = {}
    body: Optional[dict[str, Any]] = None
    assertions: list[dict[str, Any]] = []
    order: int = 0

class ApiRequestUpdate(BaseModel):
    name: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    headers: Optional[dict[str, Any]] = None
    body: Optional[dict[str, Any]] = None
    assertions: Optional[list[dict[str, Any]]] = None
    order: Optional[int] = None

class ApiRequestOut(BaseModel):
    id: str
    name: str
    method: str = "GET"
    path: str = "/"
    headers: dict[str, Any] = {}
    body: Optional[dict[str, Any]] = None
    assertions: list[dict[str, Any]] = []
    order: int = 0
    model_config = {"from_attributes": True}

class ApiCollectionOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    base_url: str = ""
    request_count: int = 0
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class PostmanImportResponse(BaseModel):
    collection: ApiCollectionOut
    imported_request_count: int = 0
    skipped_request_count: int = 0

class ApiCollectionDetailOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    base_url: str = ""
    headers: dict[str, Any] = {}
    requests: list[ApiRequestOut] = []
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class ApiTestRunOut(BaseModel):
    id: str
    collection_id: str
    status: str = "running"
    results: list[dict[str, Any]] = []
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Project Members ──────────────────────────────────────────────────

class ProjectMemberCreate(BaseModel):
    user_id: str
    role: str = "viewer"

class ProjectMemberOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str = "viewer"
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Faz 3: AI Test Case Generation ────────────────────────────────────

class TestCaseStepSchema(BaseModel):
    order: int = 0
    action: str = ""
    expected: str = ""

class TestCaseOut(BaseModel):
    id: str
    project_id: str
    batch_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    module_name: Optional[str] = None
    feature_area: Optional[str] = None
    test_type: str = "functional"
    priority: str = "medium"
    risk_level: str = "medium"
    preconditions: list[str] = []
    steps: list[dict[str, Any]] = []
    expected_result: Optional[str] = None
    tags: list[str] = []
    review_status: str = "pending"
    reviewer_note: Optional[str] = None
    scenario_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    module_name: Optional[str] = None
    feature_area: Optional[str] = None
    test_type: Optional[str] = None
    priority: Optional[str] = None
    risk_level: Optional[str] = None
    preconditions: Optional[list[str]] = None
    steps: Optional[list[dict[str, Any]]] = None
    expected_result: Optional[str] = None
    tags: Optional[list[str]] = None

class TestCaseReviewAction(BaseModel):
    action: str  # "approve" | "reject" | "edit"
    reviewer_note: Optional[str] = None
    edits: Optional[TestCaseUpdate] = None

class BulkReviewRequest(BaseModel):
    ids: list[str]
    action: str  # "approve" | "reject"
    reviewer_note: Optional[str] = None

class AiBatchOut(BaseModel):
    id: str
    project_id: str
    source_type: str = "document"
    source_name: Optional[str] = None
    source_text_preview: Optional[str] = None
    analysis_artifact_kind: str = "document_analysis"
    source_checksum: Optional[str] = None
    normalized_source_excerpt: Optional[str] = None
    extracted_requirements_count: int = 0
    candidate_scenarios_count: int = 0
    trace_links: dict[str, Any] = {}
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    status: str = "generating"
    total_generated: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class AiBatchDetailOut(BaseModel):
    batch: AiBatchOut
    test_cases: list[TestCaseOut] = []

class GenerateTestCasesRequest(BaseModel):
    source_type: str = "document"  # document | text
    source_name: Optional[str] = None
    analysis_text: str = Field(min_length=10)
    extra_instructions: str = ""
    modules: list[dict[str, Any]] = []  # from wizard analysis

class GenerateTestCasesResponse(BaseModel):
    batch_id: str
    analysis_artifact: Optional[AiBatchOut] = None
    total_generated: int = 0
    ai_provider: Optional[str] = None
    test_cases: list[TestCaseOut] = []
    message: str = ""


# ── Faz 5: Automation Code Generation ────────────────────────────────────────

class GenerateAutomationRequest(BaseModel):
    batch_id: Optional[str] = None        # use approved test cases from this batch
    test_case_ids: list[str] = []          # OR specify individual IDs
    feature_name: str = Field(min_length=1)
    include_java: bool = True
    include_playwright: bool = True

class GherkinResult(BaseModel):
    gherkin: str
    feature_name: str
    scenario_count: int = 0
    filename: str = ""

class JavaResult(BaseModel):
    java_code: str
    class_name: str
    filename: str = ""
    method_count: int = 0

class PlaywrightResult(BaseModel):
    ts_code: str
    filename: str = ""
    test_count: int = 0

class AutomationArtifactOut(BaseModel):
    id: str
    artifact_type: str
    target: ArtifactTarget = "shared"
    provenance: ProvenanceKind = "real"
    validation_status: ValidationStatus = "pending"
    generated_by: Optional[str] = None
    filename: str
    download_url: str
    size_bytes: int = 0
    created_at: Optional[datetime] = None

class GenerateAutomationResponse(BaseModel):
    feature_name: str
    test_case_count: int = 0
    gherkin: Optional[GherkinResult] = None
    java: Optional[JavaResult] = None
    playwright: Optional[PlaywrightResult] = None
    artifacts: list[AutomationArtifactOut] = []
    errors: list[str] = []
    message: str = ""


# ── Faz 6: AI Debug Loop + Allure Reporting ──────────────────────────────────

class DebugAnalysisItem(BaseModel):
    test_id: str
    root_cause_category: str = "UNKNOWN"  # PRODUCT_BUG | TEST_ISSUE | ENVIRONMENT | AUTOMATION_DEBT
    root_cause_subcategory: str = ""
    confidence: float = 0.5
    fix_steps: list[str] = []
    estimated_fix_time: str = ""
    risk_level: str = "medium"
    similar_tests_at_risk: list[str] = []
    explanation: str = ""

class DebugAnalysisResponse(BaseModel):
    execution_id: str
    project_id: str
    analyses: list[DebugAnalysisItem] = []
    overall_health: str = "unknown"  # healthy | at_risk | critical
    key_patterns: list[str] = []
    recommended_actions: list[str] = []
    ai_provider: str = "unknown"
    fallback_used: bool = False
    summary: dict[str, Any] = {}
    generated_at: Optional[str] = None
    allure_results: list[dict[str, Any]] = []

class RunDebugRequest(BaseModel):
    execution_id: str
    generate_allure: bool = True
    # Optional: provide results directly (if not reading from DB)
    results: list[dict[str, Any]] = []

class AllureExportRequest(BaseModel):
    execution_id: str

class AllureExportResponse(BaseModel):
    execution_id: str
    file_count: int = 0
    environment_properties: str = ""
    executor_json: dict[str, Any] = {}
    allure_results: list[dict[str, Any]] = []


# ── Faz 7: AI Chat Assistant ──────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: Optional[str] = None
    project_context: Optional[dict[str, Any]] = None
    history: list[ChatMessage] = []

class ChatResponse(BaseModel):
    response: str
    intent: str = "general"
    ai_provider: str = "unknown"
    fallback_used: bool = False
    session_id: str = ""
    timestamp: Optional[str] = None

class QuickAction(BaseModel):
    id: str
    label: str
    message: str
    icon: str = ""

class ChatSessionOut(BaseModel):
    session_id: str
    project_id: str
    message_count: int = 0
    created_at: Optional[str] = None
    last_message_at: Optional[str] = None


# ── Faz 8: Test Runner ─────────────────────────────────────────────────

class RunExecutionRequest(BaseModel):
    browser: str = "chromium"              # chromium | firefox | webkit
    tags: list[str] = []                   # pytest marker filtresi
    base_url: str = ""                     # override proje base URL'i
    # "simulation" (hızlı, deterministik) veya "playwright" (gerçek tarayıcı).
    # None geldiğinde engine kendi varsayılanına düşer (TSPM_DEFAULT_RUN_MODE).
    mode: Optional[Literal["simulation", "playwright"]] = None

class RunExecutionResponse(BaseModel):
    execution_id: str
    run_id: str                            # SSE stream için
    status: str = "started"
    stream_url: str = ""                   # /executions/{id}/stream/{run_id}
    # Engine'in kabul ettiği/seçtiği mod; UI gerçek vs. simülasyon rozetinde kullanır.
    mode: Optional[Literal["simulation", "playwright"]] = None

class ExecutionLiveEvent(BaseModel):
    type: str                              # output | test_result | summary | error | done
    text: str = ""
    scenario_id: str = ""
    status: str = ""
    stats: Optional[dict[str, Any]] = None

class ExecutionMetricsOut(BaseModel):
    execution_id: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    duration_seconds: Optional[float] = None
    executed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
