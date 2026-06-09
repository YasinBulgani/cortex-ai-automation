"""AI Service Database Models."""

from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, UUID as UUIDType, Text, JSON, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class LLMCallLog(Base):
    """Audit log for LLM calls - GDPR/BDDK compliant."""
    __tablename__ = "sd_ai_audit_log"

    id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid4)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    tenant_id = Column(UUIDType(as_uuid=True), nullable=False, index=True)  # RLS
    actor_user_id = Column(UUIDType(as_uuid=True), nullable=False)
    event_type = Column(String(50), nullable=False)  # llm_call, hallucination, approval, tool_call
    feature = Column(String(50), nullable=False)  # bdd_gen, rca, test_improvement, etc
    resource_id = Column(String(255))  # test_case_id, defect_id, project_id
    action = Column(String(100))  # generate, improve, analyze, validate
    input_text = Column(Text)  # User's input (PII masked)
    output_text = Column(Text)  # LLM's output (truncated to 500 chars)
    model = Column(String(50))  # gpt-4, llama3.1:8b, etc
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    cost_usd = Column(Float)  # Numeric(10, 6)
    confidence_score = Column(Float)  # 0-1 confidence
    approved_by_user_id = Column(UUIDType(as_uuid=True))
    approval_decision = Column(String(20))  # approved, rejected
    error_message = Column(Text)
    metadata = Column(JSON)  # flexible storage for extra fields
    ip_address = Column(String(45))  # IPv4 or IPv6
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_ai_audit_tenant_ts", "tenant_id", "ts"),
        Index("idx_ai_audit_feature", "feature"),
        Index("idx_ai_audit_resource", "resource_id"),
    )


class ApprovalQueue(Base):
    """Approval request queue - for risky actions."""
    __tablename__ = "sd_ai_approval_queue"

    id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUIDType(as_uuid=True), nullable=False, index=True)  # RLS
    requestor_id = Column(UUIDType(as_uuid=True), nullable=False)
    feature = Column(String(50), nullable=False)  # code_gen, defect_creation, sql_gen
    action_intent = Column(String(500), nullable=False)  # Human-readable: "Generate automation code for login flow"
    action_payload = Column(JSON, nullable=False)  # The actual data (code, params, etc)
    required_approver_role = Column(String(50), nullable=False)  # qa_lead, dba, project_owner
    status = Column(String(20), default="pending")  # pending, approved, rejected, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Auto-expire after timeout
    approved_by_user_id = Column(UUIDType(as_uuid=True))
    approval_timestamp = Column(DateTime)
    approval_comment = Column(Text)
    executed_at = Column(DateTime)
    result = Column(JSON)  # If executed, store result

    __table_args__ = (
        Index("idx_approval_tenant_status", "tenant_id", "status"),
        Index("idx_approval_expires", "expires_at"),
    )


class CostLog(Base):
    """Cost tracking per feature, tenant, model."""
    __tablename__ = "sd_ai_cost_log"

    id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUIDType(as_uuid=True), nullable=False, index=True)  # RLS
    feature = Column(String(50), nullable=False)  # bdd_gen, rca, etc
    model = Column(String(50), nullable=False)  # gpt-4, llama3.1:8b, groq
    tokens_used = Column(Integer)
    cost_usd = Column(Float)  # Numeric(10, 6)
    ts = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_cost_tenant_feature", "tenant_id", "feature"),
        Index("idx_cost_ts", "ts"),
    )


class HallucinationReport(Base):
    """Track detected hallucinations for analysis."""
    __tablename__ = "sd_ai_hallucination_report"

    id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid4)
    llm_call_id = Column(UUIDType(as_uuid=True), nullable=False)
    tenant_id = Column(UUIDType(as_uuid=True), nullable=False, index=True)  # RLS
    hallucination_type = Column(String(50))  # ungrounded, contradiction, syntax, etc
    description = Column(Text)
    confidence_score = Column(Float)  # How confident we are it's a hallucination
    source_context = Column(Text)  # What it should have been based on
    user_feedback = Column(String(20))  # correct, incorrect, unsure
    ts = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_hallucination_tenant_type", "tenant_id", "hallucination_type"),
    )


class PromptTemplate(Base):
    """Versioned prompt templates for features."""
    __tablename__ = "sd_ai_prompt_template"

    id = Column(UUIDType(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUIDType(as_uuid=True), nullable=False, index=True)  # RLS (optional, shared templates)
    feature = Column(String(50), nullable=False)  # bdd_gen, rca, etc
    version = Column(Integer, default=1)
    name = Column(String(255), nullable=False)
    system_prompt = Column(Text)
    user_prompt_template = Column(Text)  # With {placeholders}
    output_format = Column(String(50))  # json, markdown, text, gherkin
    model_routing = Column(String(50))  # ANALYZE, FAST, CODER, CHAT
    token_budget = Column(Integer)  # Max tokens for this feature
    is_active = Column(Boolean, default=True)
    created_by = Column(UUIDType(as_uuid=True))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_prompt_feature_active", "feature", "is_active"),
    )
