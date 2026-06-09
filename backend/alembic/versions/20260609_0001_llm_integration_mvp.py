"""LLM Integration MVP — Database migration for all 10 features.

Created: 2026-06-09
Includes:
- Feature 1: RAG Foundation (vector store, retrieval logs)
- Feature 2: Model Routing (task-to-model mapping)
- Feature 3: Hallucination Detection (confidence scores)
- Feature 4: Approval Workflow (human-in-loop queues)
- Feature 5: Audit Logging (complete traces)
- Feature 6: Cost Tracking (budget management)
- Feature 7: Rate Limiting (quota enforcement)
- Feature 8: Streaming (session tracking)
- Feature 9: Function Calling (tool definitions)
- Feature 10: Fine-Tuning (dataset preparation)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    """Create tables for LLM Integration MVP."""

    # Feature 1: RAG Foundation
    op.create_table(
        "llm_rag_vectors",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("namespace", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=True),
        sa.Column("document_text", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, default={}, nullable=False),
        sa.Column("embedding", postgresql.JSON, nullable=False),
        sa.Column("similarity_threshold", sa.Numeric(3, 2), default=0.7),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_rag_tenant_namespace", "llm_rag_vectors", ["tenant_id", "namespace"]
    )
    op.create_index("ix_rag_source", "llm_rag_vectors", ["source_type", "source_id"])

    op.create_table(
        "llm_rag_retrievals",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("namespaces", postgresql.JSON, nullable=False),
        sa.Column("top_k", sa.Integer, default=5),
        sa.Column("results_count", sa.Integer, nullable=False),
        sa.Column("latency_ms", sa.Numeric(8, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retrieval_tenant", "llm_rag_retrievals", ["tenant_id"])

    # Feature 2: Model Routing
    op.create_table(
        "llm_model_routing",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column(
            "task_type",
            sa.Enum("coder", "analyst", "fast", "default", name="task_type_enum"),
            nullable=False,
        ),
        sa.Column("primary_model", sa.String(64), nullable=False),
        sa.Column("fallback_models", postgresql.JSON, nullable=False),
        sa.Column("cost_budget_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("max_tokens", sa.Integer, default=2048),
        sa.Column("temperature", sa.Numeric(3, 2), default=0.7),
        sa.Column("enabled", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "task_type", name="uq_routing_tenant_task"),
    )

    # Feature 3: Hallucination Detection
    op.create_table(
        "llm_hallucination_scores",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column(
            "llm_call_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("llm_audit_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=False),
        sa.Column(
            "confidence_level",
            sa.Enum("high", "medium", "low", "uncertain", name="confidence_level_enum"),
            nullable=False,
        ),
        sa.Column("fact_check_passed", sa.Boolean, nullable=True),
        sa.Column("fact_check_details", postgresql.JSONB, nullable=True),
        sa.Column("uncertainty_flags", postgresql.JSON, nullable=False),
        sa.Column("kb_match_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hallucination_tenant", "llm_hallucination_scores", ["tenant_id"])

    # Feature 4: Approval Workflow
    op.create_table(
        "llm_approval_queues",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("feature_type", sa.String(32), nullable=False),
        sa.Column("ai_suggestion", postgresql.JSONB, nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "approved", "rejected", "requires_revision", name="approval_status_enum"
            ),
            default="pending",
        ),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer, default=5),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approval_tenant_status", "llm_approval_queues", ["tenant_id", "status"])
    op.create_index("ix_approval_user", "llm_approval_queues", ["user_id"])

    # Feature 5: Audit Logging
    op.create_table(
        "llm_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("feature_type", sa.String(32), nullable=False),
        sa.Column(
            "task_type",
            sa.Enum("coder", "analyst", "fast", "default", name="task_type_enum"),
            nullable=False,
        ),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("prompt_text", sa.Text, nullable=False),
        sa.Column("response_text", sa.Text, nullable=False),
        sa.Column("tokens_input", sa.Integer, nullable=False),
        sa.Column("tokens_output", sa.Integer, nullable=False),
        sa.Column("latency_ms", sa.Numeric(8, 2), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("user_action", sa.String(16), nullable=False),
        sa.Column("user_feedback", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_tenant_time", "llm_audit_logs", ["tenant_id", "created_at"])
    op.create_index("ix_audit_model", "llm_audit_logs", ["model_used"])

    # Feature 6: Cost Tracking
    op.create_table(
        "llm_cost_records",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("model_name", sa.String(64), nullable=False),
        sa.Column("tokens_input", sa.Integer, nullable=False),
        sa.Column("tokens_output", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cost_tenant_date", "llm_cost_records", ["tenant_id", "date"])

    op.create_table(
        "llm_budget_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("monthly_budget_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("current_spend_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("alert_threshold_pct", sa.Integer, default=80),
        sa.Column("alert_sent", sa.Boolean, default=False),
        sa.Column("alert_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "month", name="uq_budget_tenant_month"),
    )

    # Feature 7: Rate Limiting
    op.create_table(
        "llm_rate_limits",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("requests_per_minute", sa.Integer, default=10),
        sa.Column("requests_per_hour", sa.Integer, default=500),
        sa.Column("requests_per_day", sa.Integer, default=5000),
        sa.Column("concurrent_requests_limit", sa.Integer, default=5),
        sa.Column("enabled", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_quota_tenant_user"),
    )

    op.create_table(
        "llm_rate_limit_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("limit_type", sa.String(16), nullable=False),
        sa.Column("exceeded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("queue_position", sa.Integer, nullable=True),
    )
    op.create_index(
        "ix_ratelimit_tenant_user", "llm_rate_limit_events", ["tenant_id", "user_id"]
    )

    # Feature 8: Streaming Sessions
    op.create_table(
        "llm_streaming_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("request_id", sa.String(64), unique=True, nullable=False),
        sa.Column("feature_type", sa.String(32), nullable=False),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("total_tokens_streamed", sa.Integer, default=0),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), default="active"),
    )
    op.create_index("ix_stream_tenant_user", "llm_streaming_sessions", ["tenant_id", "user_id"])

    # Feature 9: Function Calling
    op.create_table(
        "llm_tool_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("input_schema", postgresql.JSONB, nullable=False),
        sa.Column("output_schema", postgresql.JSONB, nullable=False),
        sa.Column("enabled", sa.Boolean, default=True),
        sa.Column("execution_handler", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "tool_name", name="uq_tool_tenant_name"),
    )

    op.create_table(
        "llm_tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column(
            "llm_call_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("llm_audit_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("input_params", postgresql.JSONB, nullable=False),
        sa.Column("output_result", postgresql.JSONB, nullable=True),
        sa.Column("execution_time_ms", sa.Numeric(8, 2), nullable=False),
        sa.Column("status", sa.String(16), default="success"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_toolcall_tenant", "llm_tool_calls", ["tenant_id"])

    # Feature 10: Fine-Tuning
    op.create_table(
        "llm_finetuning_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("task_type", sa.String(32), nullable=False),
        sa.Column("total_examples", sa.Integer, default=0),
        sa.Column("training_examples", sa.Integer, default=0),
        sa.Column("validation_examples", sa.Integer, default=0),
        sa.Column("test_examples", sa.Integer, default=0),
        sa.Column("status", sa.String(16), default="collecting"),
        sa.Column("s3_path", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_dataset_tenant_name"),
    )

    op.create_table(
        "llm_finetuning_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("llm_finetuning_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("base_model", sa.String(64), nullable=False),
        sa.Column("job_status", sa.String(16), default="queued"),
        sa.Column("provider_job_id", sa.String(128), nullable=True),
        sa.Column("hyperparameters", postgresql.JSONB, nullable=False),
        sa.Column("training_loss", sa.Numeric(8, 6), nullable=True),
        sa.Column("validation_accuracy", sa.Numeric(3, 2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_finetuning_tenant_status", "llm_finetuning_jobs", ["tenant_id", "job_status"]
    )


def downgrade():
    """Drop all LLM Integration tables."""

    op.drop_table("llm_finetuning_jobs")
    op.drop_table("llm_finetuning_datasets")
    op.drop_table("llm_tool_calls")
    op.drop_table("llm_tool_definitions")
    op.drop_table("llm_streaming_sessions")
    op.drop_table("llm_rate_limit_events")
    op.drop_table("llm_rate_limits")
    op.drop_table("llm_budget_alerts")
    op.drop_table("llm_cost_records")
    op.drop_table("llm_audit_logs")
    op.drop_table("llm_approval_queues")
    op.drop_table("llm_hallucination_scores")
    op.drop_table("llm_model_routing")
    op.drop_table("llm_rag_retrievals")
    op.drop_table("llm_rag_vectors")
