"""Pydantic schemas for LLM Integration MVP."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# Feature 1: RAG Foundation
# ============================================================================


class RAGVectorInput(BaseModel):
    """Input for storing vectors in RAG (Feature 1)."""
    namespace: str = Field(..., description="rag namespace (test_cases, dsl_phrases, requirements)")
    source_type: str = Field(..., description="test_case, dsl_phrase, requirement, bdd")
    source_id: Optional[str] = Field(None, description="Reference to original resource")
    document_text: str = Field(..., description="Text to embed")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGVectorResponse(BaseModel):
    """RAG vector record."""
    id: str
    namespace: str
    source_type: str
    source_id: Optional[str]
    document_text: str
    metadata: Dict[str, Any]
    similarity_threshold: float
    created_at: datetime


class RAGRetrievalQuery(BaseModel):
    """Query RAG vectors (Feature 1)."""
    query: str = Field(..., description="Search query")
    namespaces: List[str] = Field(default=["test_cases"], description="Which namespaces to search")
    top_k: int = Field(default=5, ge=1, le=50)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)


class RAGRetrievalResult(BaseModel):
    """Retrieval result with similarity score."""
    vector_id: str
    source_type: str
    source_id: Optional[str]
    document_text: str
    similarity_score: float
    metadata: Dict[str, Any]


class RAGRetrievalResponse(BaseModel):
    """RAG retrieval response (Feature 1)."""
    results: List[RAGRetrievalResult]
    total_results: int
    latency_ms: float
    retrieval_log_id: str


# ============================================================================
# Feature 2: Model Routing
# ============================================================================


class ModelRoutingConfig(BaseModel):
    """Configure task-to-model routing (Feature 2)."""
    task_type: str = Field(..., description="coder, analyst, fast, default")
    primary_model: str = Field(..., description="Primary model name")
    fallback_models: List[str] = Field(default_factory=list, description="Fallback model chain")
    cost_budget_usd: float = Field(default=10.0, ge=0)
    max_tokens: int = Field(default=2048, ge=256, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    enabled: bool = Field(default=True)


class ModelRoutingResponse(BaseModel):
    """Model routing configuration response."""
    id: str
    task_type: str
    primary_model: str
    fallback_models: List[str]
    cost_budget_usd: float
    created_at: datetime


class ModelSelectionRequest(BaseModel):
    """Request model selection for a task (Feature 2)."""
    task_type: Optional[str] = Field(None, description="Preferred task type")
    query_length: int = Field(default=0, description="Length of query in chars")
    complexity_level: str = Field(default="medium", description="low, medium, high")


class ModelSelectionResponse(BaseModel):
    """Model selection result."""
    selected_model: str
    task_type: str
    reasoning: str
    estimated_cost_usd: float
    estimated_latency_ms: int


# ============================================================================
# Feature 3: Hallucination Detection
# ============================================================================


class HallucinationCheckRequest(BaseModel):
    """Request hallucination check on text (Feature 3)."""
    text: str = Field(..., description="Text to check for hallucinations")
    context: Optional[str] = Field(None, description="Additional context for verification")
    fact_check: bool = Field(default=True, description="Enable fact-checking against KB")


class FactCheckResult(BaseModel):
    """Fact-check result for a claim."""
    claim: str
    verified: bool
    confidence: float
    sources: List[str] = Field(default_factory=list)


class HallucinationScore(BaseModel):
    """Hallucination detection result (Feature 3)."""
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str = Field(..., description="high, medium, low, uncertain")
    fact_check_passed: Optional[bool] = Field(None)
    fact_check_details: Optional[List[FactCheckResult]] = Field(None)
    uncertainty_flags: List[str] = Field(default_factory=list)
    kb_match_score: Optional[float] = Field(None)
    recommendation: str = Field(..., description="approve, review_required, reject")


# ============================================================================
# Feature 4: Approval Workflow
# ============================================================================


class ApprovalQueueItem(BaseModel):
    """Item in approval queue (Feature 4)."""
    feature_type: str = Field(..., description="test_case_gen, bdd_gen, test_repair")
    ai_suggestion: Dict[str, Any] = Field(...)
    priority: int = Field(default=5, ge=1, le=10)


class ApprovalQueueResponse(BaseModel):
    """Approval queue item response."""
    id: str
    feature_type: str
    ai_suggestion: Dict[str, Any]
    status: str
    priority: int
    created_at: datetime
    updated_at: datetime


class ApprovalDecision(BaseModel):
    """User decision on approval (Feature 4)."""
    status: str = Field(..., description="approved, rejected, requires_revision")
    notes: Optional[str] = Field(None)


class ApprovalListResponse(BaseModel):
    """List of pending approvals."""
    total_count: int
    pending_count: int
    items: List[ApprovalQueueResponse]


# ============================================================================
# Feature 5: Audit Logging
# ============================================================================


class AuditLogEntry(BaseModel):
    """Audit log entry (Feature 5)."""
    id: str
    feature_type: str
    task_type: str
    model_used: str
    tokens_input: int
    tokens_output: int
    latency_ms: float
    cost_usd: float
    user_action: str = Field(..., description="approved, rejected, revised")
    user_feedback: Optional[str] = Field(None)
    created_at: datetime


class AuditLogQuery(BaseModel):
    """Query audit logs (Feature 5)."""
    feature_type: Optional[str] = Field(None)
    model_used: Optional[str] = Field(None)
    user_action: Optional[str] = Field(None)
    start_date: Optional[datetime] = Field(None)
    end_date: Optional[datetime] = Field(None)
    limit: int = Field(default=100, ge=1, le=1000)


class AuditLogResponse(BaseModel):
    """Audit log response."""
    total_count: int
    logs: List[AuditLogEntry]


# ============================================================================
# Feature 6: Cost Tracking
# ============================================================================


class CostRecord(BaseModel):
    """Cost record for single request (Feature 6)."""
    model_name: str
    tokens_input: int
    tokens_output: int
    cost_usd: float


class CostSummary(BaseModel):
    """Cost summary (Feature 6)."""
    period: str = Field(..., description="day, week, month, year")
    total_cost_usd: float
    total_tokens: int
    request_count: int
    avg_cost_per_request: float
    model_breakdown: Dict[str, float]


class BudgetStatus(BaseModel):
    """Budget status and alerts (Feature 6)."""
    month: str = Field(..., description="YYYY-MM")
    monthly_budget_usd: float
    current_spend_usd: float
    remaining_usd: float
    percentage_used: float
    alert_threshold_pct: int
    alert_triggered: bool


# ============================================================================
# Feature 7: Rate Limiting
# ============================================================================


class RateLimitConfig(BaseModel):
    """Rate limit configuration (Feature 7)."""
    requests_per_minute: int = Field(default=10, ge=1)
    requests_per_hour: int = Field(default=500, ge=1)
    requests_per_day: int = Field(default=5000, ge=1)
    concurrent_requests_limit: int = Field(default=5, ge=1)
    enabled: bool = Field(default=True)


class RateLimitStatus(BaseModel):
    """Current rate limit status (Feature 7)."""
    rpm_remaining: int
    rph_remaining: int
    rpd_remaining: int
    concurrent_active: int
    concurrent_limit: int
    reset_at: Optional[datetime] = None


class RateLimitExceeded(BaseModel):
    """Rate limit exceeded response (Feature 7)."""
    error: str = Field(default="Rate limit exceeded")
    limit_type: str = Field(..., description="rpm, rph, rpd, concurrent")
    reset_at: datetime
    queue_position: Optional[int] = None


# ============================================================================
# Feature 8: Streaming Responses
# ============================================================================


class StreamingRequest(BaseModel):
    """Request for streaming response (Feature 8)."""
    feature_type: str = Field(..., description="test_gen, code_review, etc.")
    task_type: str = Field(default="default", description="coder, analyst, fast")
    prompt: str = Field(...)
    model_override: Optional[str] = Field(None)


class StreamingToken(BaseModel):
    """Single token in stream (Feature 8)."""
    token: str
    tokens_so_far: int
    latency_ms: float


# ============================================================================
# Feature 9: Function Calling
# ============================================================================


class ToolDefinitionRequest(BaseModel):
    """Define a tool for function calling (Feature 9)."""
    tool_name: str = Field(..., max_length=64)
    description: str = Field(...)
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for inputs")
    output_schema: Dict[str, Any] = Field(..., description="JSON schema for outputs")
    execution_handler: str = Field(..., description="Module path to executor")


class ToolDefinitionResponse(BaseModel):
    """Tool definition response."""
    id: str
    tool_name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    enabled: bool
    created_at: datetime


class ToolCallRequest(BaseModel):
    """Request tool execution (Feature 9)."""
    tool_name: str = Field(...)
    input_params: Dict[str, Any] = Field(...)


class ToolCallResult(BaseModel):
    """Tool execution result (Feature 9)."""
    tool_name: str
    input_params: Dict[str, Any]
    output_result: Dict[str, Any]
    execution_time_ms: float
    status: str = Field(..., description="success, failure")
    error_message: Optional[str] = Field(None)


class FunctionCallingResponse(BaseModel):
    """Function calling response (Feature 9)."""
    main_response: str
    tool_calls: List[ToolCallResult] = Field(default_factory=list)
    total_latency_ms: float


# ============================================================================
# Feature 10: Fine-Tuning
# ============================================================================


class FineTuningDatasetCreate(BaseModel):
    """Create fine-tuning dataset (Feature 10)."""
    name: str = Field(..., max_length=128)
    description: Optional[str] = Field(None)
    task_type: str = Field(..., description="test_gen, code_repair, etc.")


class FineTuningDatasetResponse(BaseModel):
    """Fine-tuning dataset response."""
    id: str
    name: str
    task_type: str
    total_examples: int
    status: str = Field(..., description="collecting, ready, training, complete")
    created_at: datetime
    updated_at: datetime


class TrainingExample(BaseModel):
    """Training example for fine-tuning (Feature 10)."""
    input_text: str = Field(...)
    output_text: str = Field(...)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FineTuningJobCreate(BaseModel):
    """Create fine-tuning job (Feature 10)."""
    dataset_id: str = Field(...)
    base_model: str = Field(...)
    hyperparameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "learning_rate": 2e-5,
            "num_epochs": 3,
            "batch_size": 4,
        }
    )


class FineTuningJobResponse(BaseModel):
    """Fine-tuning job response."""
    id: str
    dataset_id: str
    base_model: str
    job_status: str = Field(..., description="queued, training, completed, failed")
    training_loss: Optional[float] = Field(None)
    validation_accuracy: Optional[float] = Field(None)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
