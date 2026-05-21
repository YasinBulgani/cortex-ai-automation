"""
API Testing Pydantic Schemas
=============================

CRUD + Execution + AI Generation icin request/response modelleri.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENVIRONMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EnvironmentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    variables: Dict[str, str] = Field(default_factory=dict)
    sensitive_keys: List[str] = Field(default_factory=list)
    is_default: bool = False


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[Dict[str, str]] = None
    sensitive_keys: Optional[List[str]] = None
    is_default: Optional[bool] = None


class EnvironmentOut(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    variables: Dict[str, str] = {}
    sensitive_keys: List[str] = []
    is_default: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPEC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SpecImportRequest(BaseModel):
    """URL veya inline content ile spec import."""
    source_url: Optional[str] = None
    content: Optional[str] = None  # Raw JSON/YAML
    name: Optional[str] = None  # Opsiyonel — spec title'dan alinir


class SpecOut(BaseModel):
    id: str
    project_id: str
    name: str
    version: Optional[str] = None
    spec_format: str
    endpoint_count: int = 0
    schema_count: int = 0
    ai_analysis: Optional[dict] = None
    source_url: Optional[str] = None
    source_file: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EndpointOut(BaseModel):
    id: str
    spec_id: str
    method: str
    path: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []
    parameters: List[dict] = []
    request_body_schema: Optional[dict] = None
    response_schemas: dict = {}
    auth_required: bool = True
    risk_level: str = "medium"
    has_pii: bool = False
    has_financial: bool = False
    compliance_tags: List[str] = []
    depends_on: List[dict] = []
    test_case_count: int = 0

    model_config = {"from_attributes": True}


class SpecDetailOut(SpecOut):
    """Spec detay — endpoint listesi dahil."""
    endpoints: List[EndpointOut] = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCaseCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    test_type: str = Field(..., max_length=64)
    priority: str = Field(default="P2", max_length=32)
    endpoint_id: Optional[str] = None
    collection_id: Optional[str] = None

    owasp_category: Optional[str] = None
    regulation: Optional[str] = None
    cwe_id: Optional[str] = None

    request_method: str = Field(..., max_length=16)
    request_path: str = Field(..., max_length=1000)
    request_headers: dict = Field(default_factory=dict)
    request_params: dict = Field(default_factory=dict)
    request_body: Optional[dict] = None

    pre_request_vars: Optional[dict] = None
    setup_chain: Optional[List[dict]] = None
    assertions: List[dict] = Field(default_factory=list)

    ai_generated: bool = False
    ai_reasoning: Optional[str] = None


class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    test_type: Optional[str] = None
    priority: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    request_headers: Optional[dict] = None
    request_params: Optional[dict] = None
    request_body: Optional[dict] = None
    assertions: Optional[List[dict]] = None
    review_status: Optional[str] = None
    reviewer_note: Optional[str] = None


class TestCaseOut(BaseModel):
    id: str
    project_id: str
    endpoint_id: Optional[str] = None
    collection_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    test_type: str
    priority: str = "P2"

    owasp_category: Optional[str] = None
    regulation: Optional[str] = None
    cwe_id: Optional[str] = None

    request_method: str
    request_path: str
    request_headers: dict = {}
    request_params: dict = {}
    request_body: Optional[dict] = None

    pre_request_vars: Optional[dict] = None
    setup_chain: Optional[List[dict]] = None
    assertions: List[dict] = []

    ai_generated: bool = False
    ai_model: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_reasoning: Optional[str] = None

    review_status: str = "pending"
    reviewer_note: Optional[str] = None

    last_run_status: Optional[str] = None
    last_run_at: Optional[datetime] = None
    run_count: int = 0
    pass_count: int = 0
    fail_count: int = 0

    quarantined: bool = False
    quarantine_reason: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AI GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AIGenerateRequest(BaseModel):
    """AI ile test case uretim istegi."""
    mode: str = Field(default="test_generation")
    # test_generation, security_audit, chain_builder

    endpoint_ids: Optional[List[str]] = None  # Belirli endpoint'ler icin
    spec_id: Optional[str] = None  # Tum spec icin

    regulations: List[str] = Field(default_factory=lambda: ["BDDK", "KVKK"])
    test_types: List[str] = Field(default_factory=lambda: [
        "positive", "negative", "boundary", "security", "compliance",
    ])
    max_tests_per_endpoint: int = Field(default=8, ge=1, le=30)
    owasp_focus: List[str] = Field(default_factory=list)
    additional_context: Optional[str] = None


class AIGenerateResponse(BaseModel):
    """AI uretim sonucu."""
    mode: str
    generated_count: int
    test_cases: List[TestCaseOut] = []
    security_findings: Optional[dict] = None
    chains: Optional[List[dict]] = None
    warnings: List[str] = []
    ai_model: Optional[str] = None
    duration_ms: int = 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ChainCreate(BaseModel):
    name: str = Field(..., max_length=300)
    description: Optional[str] = None
    nodes: List[dict] = Field(default_factory=list)
    edges: List[dict] = Field(default_factory=list)
    global_variables: dict = Field(default_factory=dict)
    stop_on_failure: bool = True
    max_retries: int = Field(default=0, ge=0, le=5)
    delay_between_ms: int = Field(default=0, ge=0, le=30000)


class ChainOut(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    nodes: List[dict] = []
    edges: List[dict] = []
    global_variables: dict = {}
    ai_generated: bool = False
    stop_on_failure: bool = True
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXECUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExecuteRequest(BaseModel):
    """Tek bir request calistirma."""
    method: str = Field(..., max_length=16)
    url: str = Field(..., max_length=2000)
    headers: dict = Field(default_factory=dict)
    params: dict = Field(default_factory=dict)
    body: Any = None
    environment_id: Optional[str] = None
    assertions: List[dict] = Field(default_factory=list)
    expected_schema: Optional[dict] = None
    timeout: float = Field(default=30.0, ge=1, le=120)


class ExecuteTestCasesRequest(BaseModel):
    """Toplu test case calistirma."""
    test_case_ids: List[str]
    environment_id: Optional[str] = None
    stop_on_failure: bool = False


class ExecutionResultOut(BaseModel):
    """Tek bir request calisma sonucu."""
    method: str
    url: str
    status_code: Optional[int] = None
    response_size_bytes: int = 0
    total_ms: float = 0
    passed: bool = False
    error: Optional[str] = None
    assertion_results: List[dict] = []
    schema_valid: Optional[bool] = None
    schema_errors: List[str] = []
    extracted_variables: dict = {}
    response_body: Optional[str] = None
    response_headers: dict = {}


class ExecutionSummaryOut(BaseModel):
    """Toplu calisma ozeti."""
    run_id: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_ms: float = 0
    results: List[ExecutionResultOut] = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXECUTION HISTORY & TRENDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExecutionHistoryItem(BaseModel):
    """Tek bir calisma ozeti — execution history listesi icin."""
    run_id: str
    timestamp: Optional[datetime] = None
    total: int = 0
    passed: int = 0
    failed: int = 0
    duration_ms: float = 0
    pass_rate: float = 0.0
    status: str = "mixed"  # passed / failed / mixed
    test_types: List[str] = []


class ExecutionHistoryResponse(BaseModel):
    """Sayfalanmis execution history."""
    items: List[ExecutionHistoryItem] = []
    total_count: int = 0
    page: int = 1
    per_page: int = 20


class ExecutionDetailItem(BaseModel):
    """Tek bir test case calisma detayi — run detail icin."""
    id: str
    test_case_id: Optional[str] = None
    test_case_title: Optional[str] = None
    actual_method: str = ""
    actual_url: str = ""
    status_code: Optional[int] = None
    total_ms: float = 0.0
    passed: bool = False
    error_message: Optional[str] = None
    assertion_results: List[Dict[str, Any]] = []
    schema_valid: Optional[bool] = None
    executed_at: Optional[datetime] = None


class ExecutionRunDetailResponse(BaseModel):
    """Tek bir run'in tam detayi."""
    run_id: str
    timestamp: Optional[datetime] = None
    total: int = 0
    passed: int = 0
    failed: int = 0
    duration_ms: float = 0
    pass_rate: float = 0.0
    status: str = "mixed"
    details: List[ExecutionDetailItem] = []


class TrendDayData(BaseModel):
    """Bir gunluk trend verisi."""
    date: str  # YYYY-MM-DD
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    avg_response_ms: float = 0.0
    run_count: int = 0


class TestTypeTrendItem(BaseModel):
    """Test tipi dagilimi trend verisi."""
    test_type: str
    count: int = 0
    passed: int = 0
    failed: int = 0


class TrendResponse(BaseModel):
    """Aggregated trend verisi."""
    days: List[TrendDayData] = []
    total_runs: int = 0
    avg_pass_rate: float = 0.0
    avg_response_ms: float = 0.0
    most_failed_test_type: Optional[str] = None
    test_type_distribution: List[TestTypeTrendItem] = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FLAKY TEST DETECTION & QUARANTINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FlakyTestItem(BaseModel):
    """Tek bir flaky test bilgisi."""
    test_case_id: str
    title: str
    test_type: str
    flaky_score: float = 0.0
    run_count: int = 0
    pass_rate: float = 0.0
    fail_rate: float = 0.0
    alternation_count: int = 0
    last_status: str = "unknown"
    avg_duration_ms: float = 0.0
    recommendation: str = "stable"  # quarantine | investigate | stable


class FlakyTestListResponse(BaseModel):
    """Flaky test listesi yaniti."""
    items: List[FlakyTestItem] = []
    total_count: int = 0
    quarantine_threshold: float = 0.6
    investigate_threshold: float = 0.3


class FlakyTrendItem(BaseModel):
    """Gunluk flaky trend verisi."""
    date: str
    total_tests: int = 0
    flaky_count: int = 0
    quarantined_count: int = 0


class FlakyTrendResponse(BaseModel):
    """Flaky trend yaniti."""
    items: List[FlakyTrendItem] = []
    days: int = 30


class QuarantineRequest(BaseModel):
    """Karantinaya alma istegi."""
    reason: Optional[str] = None


class QuarantineItem(BaseModel):
    """Karantinaya alinmis test bilgisi."""
    test_case_id: str
    title: str
    test_type: str
    quarantine_reason: Optional[str] = None
    run_count: int = 0
    pass_rate: float = 0.0
    last_status: str = "unknown"
    quarantined_at: Optional[str] = None


class QuarantineListResponse(BaseModel):
    """Karantina listesi yaniti."""
    items: List[QuarantineItem] = []
    total_count: int = 0


class QuarantineActionResponse(BaseModel):
    """Karantina islemi sonucu."""
    test_case_id: str
    title: Optional[str] = None
    quarantined: bool
    quarantine_reason: Optional[str] = Field(default=None, alias="reason")

    model_config = {"populate_by_name": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COVERAGE ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CoverageSummary(BaseModel):
    """High-level coverage numbers."""
    total_endpoints: int = 0
    covered_endpoints: int = 0
    uncovered_endpoints: int = 0
    untested_endpoints: int = 0
    coverage_rate: float = 0.0
    coverage_percent: float = 0.0
    critical_uncovered: int = 0


class CoverageGapItem(BaseModel):
    """Single endpoint coverage gap."""
    endpoint_id: str
    method: str
    path: str
    risk_level: str
    has_pii: bool = False
    has_financial: bool = False
    test_count: int = 0
    test_types_present: List[str] = Field(default_factory=list)
    test_types_missing: List[str] = Field(default_factory=list)
    gap_severity: str = "low"
    pass_rate: float = 0.0
    recommendation: str = ""


class RiskLevelStats(BaseModel):
    """Coverage stats for one risk level."""
    total: int = 0
    covered: int = 0
    rate: float = 0.0


class TestTypeStats(BaseModel):
    """Stats for one test type."""
    count: int = 0
    endpoints_covered: int = 0


class CoverageAnalysisResponse(BaseModel):
    """Full coverage analysis response."""
    summary: CoverageSummary
    gaps: List[CoverageGapItem] = Field(default_factory=list)
    by_risk_level: Dict[str, RiskLevelStats] = Field(default_factory=dict)
    by_test_type: Dict[str, TestTypeStats] = Field(default_factory=dict)


class CoverageGapSuggestionItem(BaseModel):
    """A suggestion for a single coverage gap."""
    endpoint_id: str
    method: str
    path: str
    risk_level: str
    gap_severity: str = "low"
    test_count: int = 0
    test_types_missing: List[str] = Field(default_factory=list)
    suggestion: str = ""


class CoverageGapSuggestionsResponse(BaseModel):
    """Response for the suggest-tests-for-gaps endpoint."""
    suggestions: List[CoverageGapSuggestionItem] = Field(default_factory=list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST PRIORITIZATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PriorityBreakdown(BaseModel):
    """Score breakdown per weight factor."""
    failure: float = 0.0
    risk: float = 0.0
    recency: float = 0.0
    sensitivity: float = 0.0
    change_impact: float = 0.0


class PrioritizedTestItem(BaseModel):
    """A single prioritised test case."""
    test_case_id: str
    title: str
    test_type: str
    priority_score: float = 0.0
    breakdown: PriorityBreakdown
    endpoint_method: str = ""
    endpoint_path: str = ""
    risk_level: str = "medium"
    last_run_status: Optional[str] = None
    estimated_duration_ms: float = 0.0


class PrioritizationResponse(BaseModel):
    """Prioritised test list with total count."""
    items: List[PrioritizedTestItem] = Field(default_factory=list)
    total_count: int = 0


class RiskDistribution(BaseModel):
    """Risk level distribution counts."""
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class PrioritizationStatsResponse(BaseModel):
    """Summary statistics for test prioritisation."""
    total_tests: int = 0
    quarantined_skipped: int = 0
    high_priority_count: int = 0
    medium_priority_count: int = 0
    low_priority_count: int = 0
    avg_score: float = 0.0
    risk_distribution: RiskDistribution = Field(default_factory=RiskDistribution)
    estimated_total_duration_ms: float = 0.0


class OptimalSuiteRequest(BaseModel):
    """Request body for optimal suite selection."""
    time_budget_ms: Optional[float] = None
    changed_paths: Optional[List[str]] = None


class CoverageSummaryBrief(BaseModel):
    """Brief coverage summary for optimal suite."""
    by_risk_level: Dict[str, int] = Field(default_factory=dict)
    by_test_type: Dict[str, int] = Field(default_factory=dict)


class OptimalSuiteResponse(BaseModel):
    """Response for optimal suite selection."""
    selected_test_ids: List[str] = Field(default_factory=list)
    selected_count: int = 0
    total_duration_ms: float = 0.0
    time_budget_ms: Optional[float] = None
    coverage_summary: CoverageSummaryBrief = Field(default_factory=CoverageSummaryBrief)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ASSERTION SUGGESTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AssertionSuggestion(BaseModel):
    """Single assertion suggestion item."""
    type: str = ""
    field: str = ""
    operator: str = ""
    expected: Any = None
    reason: str = ""
    priority: str = "medium"
    category: str = "functional"


class AssertionSuggestionsResponse(BaseModel):
    """Full response for assertion suggestions on a test case."""
    test_case_id: str
    current_assertion_count: int = 0
    suggestions: List[AssertionSuggestion] = Field(default_factory=list)
    coverage_improvement: str = ""


class BulkAssertionSuggestItem(BaseModel):
    """Per-test breakdown in bulk suggestion response."""
    test_case_id: str
    title: str = ""
    test_type: str = ""
    current_assertions: int = 0
    suggestion_count: int = 0
    suggestions: List[AssertionSuggestion] = Field(default_factory=list)


class BulkAssertionSummary(BaseModel):
    """Summary of bulk assertion suggestions."""
    total_test_cases: int = 0
    total_suggestions: int = 0
    avg_suggestions_per_test: float = 0.0
    results: List[BulkAssertionSuggestItem] = Field(default_factory=list)


class BulkAssertionRequest(BaseModel):
    """Request body for bulk assertion suggestion."""
    test_case_ids: Optional[List[str]] = None
    test_type: Optional[str] = None


class AssertionStatsResponse(BaseModel):
    """Assertion statistics for a project."""
    total_tests: int = 0
    total_assertions: int = 0
    avg_assertions_per_test: float = 0.0
    tests_with_no_assertions: int = 0
    tests_below_threshold: int = 0
    assertion_type_distribution: Dict[str, int] = Field(default_factory=dict)
    suggestion_potential: int = 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SELF-HEALING CI RETRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class HealingDetailItem(BaseModel):
    """Single healing attempt detail."""
    test_case_id: str
    title: str
    failure_category: str
    strategy: str
    retries_attempted: int = 0
    healed: bool = False
    final_status: str = "failed"
    healing_time_ms: float = 0.0


class HealAndRetryResponse(BaseModel):
    """Summary of a heal-and-retry operation on a run."""
    run_id: str
    total_failures: int = 0
    healed: int = 0
    still_failing: int = 0
    quarantined: int = 0
    skipped: int = 0
    healing_details: List[HealingDetailItem] = Field(default_factory=list)
    total_healing_time_ms: float = 0.0


class HealingCategoryStats(BaseModel):
    """Healing statistics for a single failure category."""
    attempts: int = 0
    healed: int = 0
    rate: float = 0.0


class HealingTopTest(BaseModel):
    """A test case that was healed frequently."""
    test_case_id: str
    title: str
    heal_count: int = 0


class HealingStatsResponse(BaseModel):
    """Aggregated healing statistics over a time period."""
    total_healing_attempts: int = 0
    success_rate: float = 0.0
    by_category: Dict[str, HealingCategoryStats] = Field(default_factory=dict)
    avg_retries_needed: float = 0.0
    avg_healing_time_ms: float = 0.0
    top_healed_tests: List[HealingTopTest] = Field(default_factory=list)
    saved_ci_time_ms: float = 0.0


class HealingLogItem(BaseModel):
    """Single healing log entry."""
    id: str
    project_id: str
    run_id: str
    test_case_id: str
    failure_category: str
    strategy: str
    retries_attempted: int = 0
    healed: bool = False
    final_status: str = "failed"
    healing_time_ms: float = 0.0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class HealingLogResponse(BaseModel):
    """List of healing log entries for a run."""
    run_id: str
    items: List[HealingLogItem] = Field(default_factory=list)
    total_count: int = 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECURITY SCANNING (OWASP API Top 10)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SecurityFinding(BaseModel):
    """Single OWASP security finding."""
    owasp_category: str = ""
    owasp_name: str = ""
    severity: str = "info"
    title: str = ""
    description: str = ""
    recommendation: str = ""
    confidence: float = 0.0
    banking_impact: str = ""


class SecurityTestSuggestion(BaseModel):
    """A suggested security test based on scan findings."""
    title: str = ""
    test_type: str = "security"
    owasp_category: str = ""
    request_modifications: Dict[str, Any] = Field(default_factory=dict)
    expected_behavior: str = ""


class EndpointScanResult(BaseModel):
    """Full security scan result for a single endpoint."""
    endpoint_id: str
    method: str = ""
    path: str = ""
    risk_level: str = "unknown"
    findings: List[SecurityFinding] = Field(default_factory=list)
    security_score: float = 0.0
    test_suggestions: List[SecurityTestSuggestion] = Field(default_factory=list)
    error: Optional[str] = None


class SpecScanResult(BaseModel):
    """Per-endpoint scan result used inside SpecScanResponse."""
    endpoint_id: str
    method: str = ""
    path: str = ""
    risk_level: str = "unknown"
    findings: List[SecurityFinding] = Field(default_factory=list)
    security_score: float = 0.0
    test_suggestions: List[SecurityTestSuggestion] = Field(default_factory=list)


class SpecScanResponse(BaseModel):
    """Aggregated scan result for an entire spec."""
    spec_id: str
    spec_name: str = ""
    total_endpoints: int = 0
    scanned_endpoints: int = 0
    findings_by_severity: Dict[str, int] = Field(default_factory=dict)
    findings_by_owasp: Dict[str, int] = Field(default_factory=dict)
    avg_security_score: float = 0.0
    endpoint_results: List[SpecScanResult] = Field(default_factory=list)
    error: Optional[str] = None


class ComplianceStatus(BaseModel):
    """Compliance check results for a single regulation."""
    passed: int = 0
    failed: int = 0
    checks: List[str] = Field(default_factory=list)


class VulnerableEndpointItem(BaseModel):
    """Top vulnerable endpoint summary."""
    endpoint_id: str
    method: str = ""
    path: str = ""
    security_score: float = 0.0
    finding_count: int = 0


class SecurityDashboardResponse(BaseModel):
    """Full security dashboard overview for a project."""
    total_endpoints: int = 0
    scanned_endpoints: int = 0
    findings_by_severity: Dict[str, int] = Field(default_factory=dict)
    findings_by_owasp: Dict[str, int] = Field(default_factory=dict)
    avg_security_score: float = 0.0
    top_vulnerable_endpoints: List[VulnerableEndpointItem] = Field(default_factory=list)
    compliance_status: Dict[str, ComplianceStatus] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)


class GenerateSecurityTestsRequest(BaseModel):
    """Request body for generating security test cases from scan."""
    endpoint_id: str
    owasp_categories: Optional[List[str]] = None


class SecurityTestScanSummary(BaseModel):
    """Brief scan summary included in test generation response."""
    total_findings: int = 0
    security_score: float = 0.0
    risk_level: str = "unknown"


class GenerateSecurityTestsResponse(BaseModel):
    """Response after generating security test cases."""
    endpoint_id: str
    generated_count: int = 0
    test_cases: List[TestCaseOut] = Field(default_factory=list)
    scan_summary: Optional[SecurityTestScanSummary] = None
    error: Optional[str] = None
