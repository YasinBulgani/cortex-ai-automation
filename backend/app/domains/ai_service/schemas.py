"""AI Service Schemas - Request/Response models."""

from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# Enums
class OutputType(str, Enum):
    BDD = "bdd"
    CODE = "code"
    SUMMARY = "summary"
    TEST_CASE = "test_case"


class TestSuggestionType(str, Enum):
    MISSING_EDGE_CASE = "missing_edge_case"
    MISSING_ERROR_PATH = "missing_error_path"
    MISSING_BOUNDARY = "missing_boundary"
    MISSING_PERFORMANCE = "missing_performance"


# ============================================================================
# Feature 1: BDD Generation
# ============================================================================

class BDDGenerationRequest(BaseModel):
    story: str = Field(..., min_length=10, max_length=5000, description="User story or requirement")
    project_id: str = Field(..., description="Project UUID")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context (acceptance criteria, etc)")


class TestCase(BaseModel):
    scenario_name: str
    given: List[str]
    when: List[str]
    then: List[str]
    priority: str = Field(default="medium")  # low, medium, high


class BDDGenerationResponse(BaseModel):
    success: bool
    test_cases: List[TestCase]
    confidence_score: float = Field(ge=0, le=1)
    execution_time_ms: int


# ============================================================================
# Feature 2: Test Improvement
# ============================================================================

class TestImprovementRequest(BaseModel):
    test_case_id: str = Field(..., description="Test case UUID")
    project_id: str = Field(..., description="Project UUID")


class TestImprovement(BaseModel):
    type: str  # clarity, coverage, performance, maintainability
    description: str
    suggested_change: str
    priority: str = Field(default="medium")


class TestImprovementResponse(BaseModel):
    success: bool
    suggestions: List[TestImprovement]
    quality_score: float = Field(ge=0, le=1)


# ============================================================================
# Feature 3: Missing Test Suggestions
# ============================================================================

class MissingTestRequest(BaseModel):
    project_id: str = Field(..., description="Project UUID")
    requirement_ids: Optional[List[str]] = Field(default=None, description="Specific requirements to analyze")
    min_confidence: Optional[float] = Field(default=0.7, ge=0, le=1)


class MissingTestSuggestion(BaseModel):
    test_case_id: Optional[str] = None  # if existing; None if new
    scenario_name: str
    description: str
    suggestion_type: TestSuggestionType
    coverage_impact: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    estimated_effort_hours: float


# ============================================================================
# Feature 4: Regression Suite Selection
# ============================================================================

class RegressionSelectionRequest(BaseModel):
    project_id: str = Field(..., description="Project UUID")
    code_changes: Dict[str, Any] = Field(..., description="Changed files/functions")
    max_test_count: Optional[int] = Field(default=50)


class RegressionSelectionResponse(BaseModel):
    success: bool
    selected_test_ids: List[str]
    coverage_prediction: float = Field(ge=0, le=1)
    estimated_duration_minutes: int


# ============================================================================
# Feature 5: Defect RCA Analysis
# ============================================================================

class DefectAnalysisRequest(BaseModel):
    defect_id: str = Field(..., description="Defect UUID")
    error_log: Optional[str] = Field(default=None, description="Error message/stack trace")
    reproduction_steps: Optional[str] = Field(default=None)


class RootCause(BaseModel):
    description: str
    likelihood: float = Field(ge=0, le=1)
    affected_components: List[str]
    suggested_fix: Optional[str] = None


class DefectAnalysisResponse(BaseModel):
    success: bool
    root_causes: List[RootCause]
    confidence_score: float = Field(ge=0, le=1)
    similar_defect_ids: List[str]


# ============================================================================
# Feature 6: Release Notes Generation
# ============================================================================

class ReleaseNotesRequest(BaseModel):
    project_id: str = Field(..., description="Project UUID")
    version: str = Field(..., description="Version number (e.g., 1.2.3)")
    fixed_defect_ids: List[str] = Field(default_factory=list)
    new_features: Optional[List[Dict[str, Any]]] = Field(default=None)


class ReleaseNotesResponse(BaseModel):
    success: bool
    content: str  # Markdown, HTML, or text
    format: str = Field(default="markdown")  # markdown, html, text


# ============================================================================
# Feature 7: Hallucination Detection
# ============================================================================

class HallucinationValidationRequest(BaseModel):
    output_text: str = Field(..., min_length=5)
    output_type: OutputType = Field(...)
    source_context: Optional[str] = Field(default=None, description="RAG context or source material")


class HallucinationRisk(BaseModel):
    risk_type: str  # ungrounded_claim, contradiction, invalid_syntax, variable_undefined
    description: str
    severity: str = Field(default="medium")  # low, medium, high, critical


class HallucinationValidationResponse(BaseModel):
    is_valid: bool
    confidence_score: float = Field(ge=0, le=1)
    hallucination_risks: List[HallucinationRisk]
    recommendations: List[str]


# ============================================================================
# Cost Tracking
# ============================================================================

class LLMCallLogRequest(BaseModel):
    feature: str  # bdd_gen, rca, etc
    model: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    confidence_score: float = Field(ge=0, le=1)


class CostUsage(BaseModel):
    feature: str
    total_calls: int
    total_tokens: int
    total_cost_usd: float
    average_confidence_score: float
