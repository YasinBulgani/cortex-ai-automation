"""LLM Integration Models — Database schemas for all 10 MVP features."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz
from enum import Enum
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(_tz.utc)


class TaskTypeEnum(str, Enum):
    """Task types for model routing (Feature 2)."""
    CODER = "coder"      # llama3.1:8b-instruct / qwen-coder
    ANALYST = "analyst"  # qwen2.5:14b / claude-3.5-sonnet
    FAST = "fast"        # llama3.1:8b (small, low-latency)
    DEFAULT = "default"  # Auto-select based on query


class ModelEnum(str, Enum):
    """Available models across providers."""
    LLAMA3_1_8B = "llama3.1:8b"
    QWEN2_5_14B = "qwen2.5:14b"
    QWEN_CODER_7B = "qwen2.5-coder:7b"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    CLAUDE_OPUS = "claude-3.5-sonnet"
    GEMINI_PRO = "gemini-2.0-pro"
    GROQ_MIXTRAL = "mixtral-8x7b-32768"


class ConfidenceLevel(str, Enum):
    """Confidence levels for hallucination detection (Feature 3)."""
    HIGH = "high"        # >0.85
    MEDIUM = "medium"    # 0.70-0.85
    LOW = "low"          # <0.70
    UNCERTAIN = "uncertain"  # Needs manual review


class ApprovalStatus(str, Enum):
    """Approval workflow statuses (Feature 4)."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVISION = "requires_revision"


# ============================================================================
# Feature 1: RAG Foundation — Vector DB & Retrieval
# ============================================================================


class RAGVectorStore(Base):
    """Vector store for documents and embeddings (Pinecone/Milvus backend)."""
    __tablename__ = "llm_rag_vectors"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    namespace: Mapped[str] = mapped_column(String(64), nullable=False)  # test_cases, dsl_phrases, requirements
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # test_case, dsl_phrase, requirement, bdd
    source_id: Mapped[str] = mapped_column(String(128), nullable=True)  # Reference to original resource
    document_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # project_id, tags, version
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)  # 1536-dim vector
    similarity_threshold: Mapped[float] = mapped_column(Numeric(3, 2), default=0.7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_rag_tenant_namespace", "tenant_id", "namespace"),
        Index("ix_rag_source", "source_type", "source_id"),
    )


class RAGRetrievalLog(Base):
    """Log of RAG retrievals for observability (Feature 1)."""
    __tablename__ = "llm_rag_retrievals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    namespaces: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    results_count: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_retrieval_tenant", "tenant_id"),)


# ============================================================================
# Feature 2: Model Routing & Cost Optimization
# ============================================================================


class ModelRoutingConfig(Base):
    """Configure which model to use for each task type (Feature 2)."""
    __tablename__ = "llm_model_routing"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(SQLEnum(TaskTypeEnum), nullable=False)
    primary_model: Mapped[str] = mapped_column(String(64), nullable=False)
    fallback_models: Mapped[list[str]] = mapped_column(JSON, nullable=False)  # [model2, model3]
    cost_budget_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    temperature: Mapped[float] = mapped_column(Numeric(3, 2), default=0.7)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_type", name="uq_routing_tenant_task"),
    )


# ============================================================================
# Feature 3: Hallucination Detection
# ============================================================================


class HallucinationScore(Base):
    """Hallucination detection scores and metadata (Feature 3)."""
    __tablename__ = "llm_hallucination_scores"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    llm_call_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("llm_audit_logs.id", ondelete="CASCADE"), nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)  # 0.0-1.0
    confidence_level: Mapped[str] = mapped_column(SQLEnum(ConfidenceLevel), nullable=False)
    fact_check_passed: Mapped[bool] = mapped_column(Boolean, nullable=True)
    fact_check_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)
    uncertainty_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False)  # ["contradiction", "unverifiable"]
    kb_match_score: Mapped[float] = mapped_column(Numeric(3, 2), nullable=True)  # Match against knowledge base
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_hallucination_tenant", "tenant_id"),)


# ============================================================================
# Feature 4: Approval Workflow (Human-in-loop)
# ============================================================================


class ApprovalQueue(Base):
    """AI suggestions awaiting human approval (Feature 4)."""
    __tablename__ = "llm_approval_queues"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)  # Creator
    feature_type: Mapped[str] = mapped_column(String(32), nullable=False)  # test_case_gen, bdd_gen, test_repair
    ai_suggestion: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    reviewer_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10, higher = more urgent
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_approval_tenant_status", "tenant_id", "status"),
        Index("ix_approval_user", "user_id"),
    )


# ============================================================================
# Feature 5: Audit Logging (Full trace)
# ============================================================================


class LLMAuditLog(Base):
    """Complete audit trail for all LLM interactions (Feature 5)."""
    __tablename__ = "llm_audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    feature_type: Mapped[str] = mapped_column(String(32), nullable=False)  # bdd_gen, test_repair, etc.
    task_type: Mapped[str] = mapped_column(SQLEnum(TaskTypeEnum), nullable=False)
    model_used: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    user_action: Mapped[str] = mapped_column(String(16), nullable=False)  # approved, rejected, revised
    user_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_audit_tenant_time", "tenant_id", "created_at"),
        Index("ix_audit_model", "model_used"),
    )


# ============================================================================
# Feature 6: Cost Tracking & Budgeting
# ============================================================================


class CostTrackingRecord(Base):
    """Per-request token count and cost (Feature 6)."""
    __tablename__ = "llm_cost_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_cost_tenant_date", "tenant_id", "date"),)


class BudgetAlert(Base):
    """Budget threshold alerts (Feature 6)."""
    __tablename__ = "llm_budget_alerts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    monthly_budget_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    current_spend_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    alert_threshold_pct: Mapped[int] = mapped_column(Integer, default=80)  # Alert at 80%
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "month", name="uq_budget_tenant_month"),
    )


# ============================================================================
# Feature 7: Rate Limiting & Backpressure
# ============================================================================


class RateLimitQuota(Base):
    """Per-user/org quota for rate limiting (Feature 7)."""
    __tablename__ = "llm_rate_limits"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)  # Per-user limit
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=10)
    requests_per_hour: Mapped[int] = mapped_column(Integer, default=500)
    requests_per_day: Mapped[int] = mapped_column(Integer, default=5000)
    concurrent_requests_limit: Mapped[int] = mapped_column(Integer, default=5)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_quota_tenant_user"),
    )


class RateLimitEvent(Base):
    """Track rate limit hits for observability (Feature 7)."""
    __tablename__ = "llm_rate_limit_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    limit_type: Mapped[str] = mapped_column(String(16), nullable=False)  # rpm, rph, rpd, concurrent
    exceeded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    queue_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (Index("ix_ratelimit_tenant_user", "tenant_id", "user_id"),)


# ============================================================================
# Feature 8: Streaming Responses (SSE)
# ============================================================================


class StreamingSession(Base):
    """Track active streaming sessions (Feature 8)."""
    __tablename__ = "llm_streaming_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    feature_type: Mapped[str] = mapped_column(String(32), nullable=False)
    model_used: Mapped[str] = mapped_column(String(64), nullable=False)
    total_tokens_streamed: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active, completed, failed

    __table_args__ = (Index("ix_stream_tenant_user", "tenant_id", "user_id"),)


# ============================================================================
# Feature 9: Function Calling (Structured Output & Tool Use)
# ============================================================================


class ToolDefinition(Base):
    """Tool definitions for function calling (Feature 9)."""
    __tablename__ = "llm_tool_definitions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # JSON schema
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    execution_handler: Mapped[str] = mapped_column(String(128), nullable=False)  # Module path to executor
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "tool_name", name="uq_tool_tenant_name"),
    )


class ToolCall(Base):
    """Record of tool invocations (Feature 9)."""
    __tablename__ = "llm_tool_calls"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    llm_call_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("llm_audit_logs.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    input_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)
    execution_time_ms: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="success")  # success, failure
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_toolcall_tenant", "tenant_id"),)


# ============================================================================
# Feature 10: Fine-Tuning Ready (Dataset Prep & Training)
# ============================================================================


class FineTuningDataset(Base):
    """Dataset preparation for fine-tuning (Feature 10)."""
    __tablename__ = "llm_finetuning_datasets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)  # test_gen, code_repair, etc.
    total_examples: Mapped[int] = mapped_column(Integer, default=0)
    training_examples: Mapped[int] = mapped_column(Integer, default=0)
    validation_examples: Mapped[int] = mapped_column(Integer, default=0)
    test_examples: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="collecting")  # collecting, ready, training, complete
    s3_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_dataset_tenant_name"),
    )


class FineTuningJob(Base):
    """Fine-tuning job records (Feature 10)."""
    __tablename__ = "llm_finetuning_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True, nullable=False)
    dataset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("llm_finetuning_datasets.id", ondelete="CASCADE"), nullable=False
    )
    base_model: Mapped[str] = mapped_column(String(64), nullable=False)
    job_status: Mapped[str] = mapped_column(String(16), default="queued")  # queued, training, completed, failed
    provider_job_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    hyperparameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    training_loss: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)
    validation_accuracy: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_finetuning_tenant_status", "tenant_id", "job_status"),)
