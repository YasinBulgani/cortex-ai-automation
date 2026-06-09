"""Create webhook configuration and delivery tables.

Revision ID: 20260609_0013
Revises: 20260609_0012
Create Date: 2026-06-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260609_0013'
down_revision = '20260609_0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhook_configs table
    op.create_table(
        'webhook_configs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('webhook_type', sa.String(32), nullable=False),
        sa.Column('provider', sa.String(64), nullable=True),
        sa.Column('target_url', sa.String(512), nullable=False),
        sa.Column('secret', sa.String(256), nullable=False),
        sa.Column('events', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('rate_limit_per_day', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('retry_backoff_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('auth_method', sa.String(32), nullable=True),
        sa.Column('auth_credentials', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhook_configs_tenant_id', 'webhook_configs', ['tenant_id'])
    op.create_index('ix_webhook_configs_provider', 'webhook_configs', ['provider'])
    op.create_index('ix_webhook_configs_is_active', 'webhook_configs', ['is_active'])
    op.create_unique_constraint(
        'uq_webhook_tenant_url_type',
        'webhook_configs',
        ['tenant_id', 'target_url', 'webhook_type']
    )

    # Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('webhook_config_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('event_type', sa.String(128), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('entity_type', sa.String(64), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('http_status_code', sa.Integer(), nullable=True),
        sa.Column('request_body', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['webhook_config_id'], ['webhook_configs.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhook_deliveries_webhook_config_id', 'webhook_deliveries', ['webhook_config_id'])
    op.create_index('ix_webhook_deliveries_tenant_id', 'webhook_deliveries', ['tenant_id'])
    op.create_index('ix_webhook_deliveries_status', 'webhook_deliveries', ['status'])
    op.create_index('ix_webhook_deliveries_created_at', 'webhook_deliveries', ['created_at'])

    # Create webhook_logs table
    op.create_table(
        'webhook_logs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('webhook_config_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhook_logs_tenant_id', 'webhook_logs', ['tenant_id'])
    op.create_index('ix_webhook_logs_webhook_config_id', 'webhook_logs', ['webhook_config_id'])
    op.create_index('ix_webhook_logs_action', 'webhook_logs', ['action'])
    op.create_index('ix_webhook_logs_created_at', 'webhook_logs', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_webhook_logs_created_at', table_name='webhook_logs')
    op.drop_index('ix_webhook_logs_action', table_name='webhook_logs')
    op.drop_index('ix_webhook_logs_webhook_config_id', table_name='webhook_logs')
    op.drop_index('ix_webhook_logs_tenant_id', table_name='webhook_logs')
    op.drop_table('webhook_logs')

    op.drop_index('ix_webhook_deliveries_created_at', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_status', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_tenant_id', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_webhook_config_id', table_name='webhook_deliveries')
    op.drop_table('webhook_deliveries')

    op.drop_constraint('uq_webhook_tenant_url_type', 'webhook_configs', type_='unique')
    op.drop_index('ix_webhook_configs_is_active', table_name='webhook_configs')
    op.drop_index('ix_webhook_configs_provider', table_name='webhook_configs')
    op.drop_index('ix_webhook_configs_tenant_id', table_name='webhook_configs')
    op.drop_table('webhook_configs')
