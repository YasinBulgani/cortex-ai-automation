"""Create AI service tables - LLM audit, approvals, cost tracking."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260609_0011'
down_revision = '20260609_0010_fix_db_med_issues'
branch_labels = None
depends_on = None


def upgrade():
    """Create AI service tables."""
    # sd_ai_audit_log — LLM call audit trail
    op.create_table(
        'sd_ai_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('feature', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('action', sa.String(100)),
        sa.Column('input_text', sa.Text()),
        sa.Column('output_text', sa.Text()),
        sa.Column('model', sa.String(50)),
        sa.Column('tokens_input', sa.Integer()),
        sa.Column('tokens_output', sa.Integer()),
        sa.Column('cost_usd', sa.Float()),
        sa.Column('confidence_score', sa.Float()),
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('approval_decision', sa.String(20)),
        sa.Column('error_message', sa.Text()),
        sa.Column('metadata', postgresql.JSON()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('created_at', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['sd_organizations.id']),
    )
    op.create_index('idx_ai_audit_tenant_ts', 'sd_ai_audit_log', ['tenant_id', 'ts'])
    op.create_index('idx_ai_audit_feature', 'sd_ai_audit_log', ['feature'])
    op.create_index('idx_ai_audit_resource', 'sd_ai_audit_log', ['resource_id'])

    # sd_ai_approval_queue — Approval workflow
    op.create_table(
        'sd_ai_approval_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requestor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feature', sa.String(50), nullable=False),
        sa.Column('action_intent', sa.String(500), nullable=False),
        sa.Column('action_payload', postgresql.JSON(), nullable=False),
        sa.Column('required_approver_role', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('approval_timestamp', sa.DateTime()),
        sa.Column('approval_comment', sa.Text()),
        sa.Column('executed_at', sa.DateTime()),
        sa.Column('result', postgresql.JSON()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['sd_organizations.id']),
    )
    op.create_index('idx_approval_tenant_status', 'sd_ai_approval_queue', ['tenant_id', 'status'])
    op.create_index('idx_approval_expires', 'sd_ai_approval_queue', ['expires_at'])

    # sd_ai_cost_log — Cost tracking per feature/tenant/model
    op.create_table(
        'sd_ai_cost_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feature', sa.String(50), nullable=False),
        sa.Column('model', sa.String(50), nullable=False),
        sa.Column('tokens_used', sa.Integer()),
        sa.Column('cost_usd', sa.Float()),
        sa.Column('ts', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['sd_organizations.id']),
    )
    op.create_index('idx_cost_tenant_feature', 'sd_ai_cost_log', ['tenant_id', 'feature'])
    op.create_index('idx_cost_ts', 'sd_ai_cost_log', ['ts'])

    # sd_ai_hallucination_report — Track detected hallucinations
    op.create_table(
        'sd_ai_hallucination_report',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('llm_call_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hallucination_type', sa.String(50)),
        sa.Column('description', sa.Text()),
        sa.Column('confidence_score', sa.Float()),
        sa.Column('source_context', sa.Text()),
        sa.Column('user_feedback', sa.String(20)),
        sa.Column('ts', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['sd_organizations.id']),
    )
    op.create_index('idx_hallucination_tenant_type', 'sd_ai_hallucination_report', ['tenant_id', 'hallucination_type'])

    # sd_ai_prompt_template — Versioned prompt templates
    op.create_table(
        'sd_ai_prompt_template',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True)),
        sa.Column('feature', sa.String(50), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('system_prompt', sa.Text()),
        sa.Column('user_prompt_template', sa.Text()),
        sa.Column('output_format', sa.String(50)),
        sa.Column('model_routing', sa.String(50)),
        sa.Column('token_budget', sa.Integer()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_prompt_feature_active', 'sd_ai_prompt_template', ['feature', 'is_active'])


def downgrade():
    """Drop AI service tables."""
    op.drop_table('sd_ai_prompt_template')
    op.drop_table('sd_ai_hallucination_report')
    op.drop_table('sd_ai_cost_log')
    op.drop_table('sd_ai_approval_queue')
    op.drop_table('sd_ai_audit_log')
