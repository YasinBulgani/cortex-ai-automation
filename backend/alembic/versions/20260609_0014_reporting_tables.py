"""Create reporting, scheduled reports, and export tables.

Revision ID: 20260609_0014
Revises: 20260609_0013
Create Date: 2026-06-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260609_0014'
down_revision = '20260609_0013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create report_templates table
    op.create_table(
        'report_templates',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_type', sa.String(64), nullable=False),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_global', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_templates_tenant_id', 'report_templates', ['tenant_id'])
    op.create_index('ix_report_templates_template_type', 'report_templates', ['template_type'])
    op.create_unique_constraint(
        'uq_report_template_tenant_name',
        'report_templates',
        ['tenant_id', 'name']
    )

    # Create scheduled_reports table
    op.create_table(
        'scheduled_reports',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('cron_schedule', sa.String(128), nullable=False),
        sa.Column('delivery_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('delivery_recipients', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('project_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scheduled_reports_tenant_id', 'scheduled_reports', ['tenant_id'])
    op.create_index('ix_scheduled_reports_is_active', 'scheduled_reports', ['is_active'])
    op.create_index('ix_scheduled_reports_next_scheduled_at', 'scheduled_reports', ['next_scheduled_at'])

    # Create report_generations table
    op.create_table(
        'report_generations',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('scheduled_report_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('report_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('report_summary', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(512), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scheduled_report_id'], ['scheduled_reports.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_generations_scheduled_report_id', 'report_generations', ['scheduled_report_id'])
    op.create_index('ix_report_generations_tenant_id', 'report_generations', ['tenant_id'])
    op.create_index('ix_report_generations_status', 'report_generations', ['status'])
    op.create_index('ix_report_generations_created_at', 'report_generations', ['created_at'])

    # Create data_export_jobs table
    op.create_table(
        'data_export_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('export_format', sa.String(32), nullable=False),
        sa.Column('entity_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('project_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('date_range', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_path', sa.String(512), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_export_jobs_tenant_id', 'data_export_jobs', ['tenant_id'])
    op.create_index('ix_data_export_jobs_status', 'data_export_jobs', ['status'])
    op.create_index('ix_data_export_jobs_created_by', 'data_export_jobs', ['created_by'])
    op.create_index('ix_data_export_jobs_created_at', 'data_export_jobs', ['created_at'])

    # Create retention_policies table
    op.create_table(
        'retention_policies',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('archive_before_delete', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('archive_location', sa.String(512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_retention_policies_tenant_id', 'retention_policies', ['tenant_id'])
    op.create_index('ix_retention_policies_entity_type', 'retention_policies', ['entity_type'])
    op.create_unique_constraint(
        'uq_retention_policy_tenant_entity',
        'retention_policies',
        ['tenant_id', 'entity_type']
    )


def downgrade() -> None:
    op.drop_constraint('uq_retention_policy_tenant_entity', 'retention_policies', type_='unique')
    op.drop_index('ix_retention_policies_entity_type', table_name='retention_policies')
    op.drop_index('ix_retention_policies_tenant_id', table_name='retention_policies')
    op.drop_table('retention_policies')

    op.drop_index('ix_data_export_jobs_created_at', table_name='data_export_jobs')
    op.drop_index('ix_data_export_jobs_created_by', table_name='data_export_jobs')
    op.drop_index('ix_data_export_jobs_status', table_name='data_export_jobs')
    op.drop_index('ix_data_export_jobs_tenant_id', table_name='data_export_jobs')
    op.drop_table('data_export_jobs')

    op.drop_index('ix_report_generations_created_at', table_name='report_generations')
    op.drop_index('ix_report_generations_status', table_name='report_generations')
    op.drop_index('ix_report_generations_tenant_id', table_name='report_generations')
    op.drop_index('ix_report_generations_scheduled_report_id', table_name='report_generations')
    op.drop_table('report_generations')

    op.drop_index('ix_scheduled_reports_next_scheduled_at', table_name='scheduled_reports')
    op.drop_index('ix_scheduled_reports_is_active', table_name='scheduled_reports')
    op.drop_index('ix_scheduled_reports_tenant_id', table_name='scheduled_reports')
    op.drop_table('scheduled_reports')

    op.drop_constraint('uq_report_template_tenant_name', 'report_templates', type_='unique')
    op.drop_index('ix_report_templates_template_type', table_name='report_templates')
    op.drop_index('ix_report_templates_tenant_id', table_name='report_templates')
    op.drop_table('report_templates')
