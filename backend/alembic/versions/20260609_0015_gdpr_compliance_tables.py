"""Create GDPR compliance tables — data export, deletion, consent, audit.

Revision ID: 20260609_0015
Revises: 20260609_0014
Create Date: 2026-06-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260609_0015'
down_revision = '20260609_0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create data_export_requests table (Article 20)
    op.create_table(
        'data_export_requests',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('included_entities', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('file_path', sa.String(512), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('file_format', sa.String(32), nullable=False, server_default='json'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_export_requests_tenant_id', 'data_export_requests', ['tenant_id'])
    op.create_index('ix_data_export_requests_user_id', 'data_export_requests', ['user_id'])
    op.create_index('ix_data_export_requests_status', 'data_export_requests', ['status'])
    op.create_index('ix_data_export_requests_created_at', 'data_export_requests', ['created_at'])

    # Create data_deletion_requests table (Article 17)
    op.create_table(
        'data_deletion_requests',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('requested_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('scope', sa.String(32), nullable=False),
        sa.Column('custom_entities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('grace_period_ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('verification_code', sa.String(256), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_deletion_requests_tenant_id', 'data_deletion_requests', ['tenant_id'])
    op.create_index('ix_data_deletion_requests_user_id', 'data_deletion_requests', ['user_id'])
    op.create_index('ix_data_deletion_requests_status', 'data_deletion_requests', ['status'])
    op.create_index('ix_data_deletion_requests_grace_period_ends_at', 'data_deletion_requests', ['grace_period_ends_at'])
    op.create_index('ix_data_deletion_requests_created_at', 'data_deletion_requests', ['created_at'])

    # Create consent_logs table
    op.create_table(
        'consent_logs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('consent_type', sa.String(64), nullable=False),
        sa.Column('version', sa.String(128), nullable=False),
        sa.Column('given', sa.Boolean(), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_consent_logs_tenant_id', 'consent_logs', ['tenant_id'])
    op.create_index('ix_consent_logs_user_id', 'consent_logs', ['user_id'])
    op.create_index('ix_consent_logs_consent_type', 'consent_logs', ['consent_type'])
    op.create_index('ix_consent_logs_given', 'consent_logs', ['given'])

    # Create audit_trails table
    op.create_table(
        'audit_trails',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('actor_type', sa.String(32), nullable=False),
        sa.Column('action', sa.String(128), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('resource_owner_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('severity', sa.String(32), nullable=False, server_default='info'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_trails_tenant_id', 'audit_trails', ['tenant_id'])
    op.create_index('ix_audit_trails_actor_user_id', 'audit_trails', ['actor_user_id'])
    op.create_index('ix_audit_trails_resource_type', 'audit_trails', ['resource_type'])
    op.create_index('ix_audit_trails_resource_id', 'audit_trails', ['resource_id'])
    op.create_index('ix_audit_trails_action', 'audit_trails', ['action'])
    op.create_index('ix_audit_trails_severity', 'audit_trails', ['severity'])
    op.create_index('ix_audit_trails_created_at', 'audit_trails', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_audit_trails_created_at', table_name='audit_trails')
    op.drop_index('ix_audit_trails_severity', table_name='audit_trails')
    op.drop_index('ix_audit_trails_action', table_name='audit_trails')
    op.drop_index('ix_audit_trails_resource_id', table_name='audit_trails')
    op.drop_index('ix_audit_trails_resource_type', table_name='audit_trails')
    op.drop_index('ix_audit_trails_actor_user_id', table_name='audit_trails')
    op.drop_index('ix_audit_trails_tenant_id', table_name='audit_trails')
    op.drop_table('audit_trails')

    op.drop_index('ix_consent_logs_given', table_name='consent_logs')
    op.drop_index('ix_consent_logs_consent_type', table_name='consent_logs')
    op.drop_index('ix_consent_logs_user_id', table_name='consent_logs')
    op.drop_index('ix_consent_logs_tenant_id', table_name='consent_logs')
    op.drop_table('consent_logs')

    op.drop_index('ix_data_deletion_requests_created_at', table_name='data_deletion_requests')
    op.drop_index('ix_data_deletion_requests_grace_period_ends_at', table_name='data_deletion_requests')
    op.drop_index('ix_data_deletion_requests_status', table_name='data_deletion_requests')
    op.drop_index('ix_data_deletion_requests_user_id', table_name='data_deletion_requests')
    op.drop_index('ix_data_deletion_requests_tenant_id', table_name='data_deletion_requests')
    op.drop_table('data_deletion_requests')

    op.drop_index('ix_data_export_requests_created_at', table_name='data_export_requests')
    op.drop_index('ix_data_export_requests_status', table_name='data_export_requests')
    op.drop_index('ix_data_export_requests_user_id', table_name='data_export_requests')
    op.drop_index('ix_data_export_requests_tenant_id', table_name='data_export_requests')
    op.drop_table('data_export_requests')
