"""Create analytics and slack integration tables.

Revision ID: 20260609_0012
Revises: 20260609_0011_db_optimization_suite
Create Date: 2026-06-09 15:00:00.000000

Analytics event schema, Slack subscriptions, notification queue, delivery logs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260609_0012'
down_revision = '20260609_0011_db_optimization_suite'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AnalyticsEvent table — test runs, defects, coverage changes
    op.create_table(
        'analytics_events',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('event_name', sa.String(128), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('entity_type', sa.String(64), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('event_data', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_analytics_events_tenant', 'tenant_id'),
        sa.Index('idx_analytics_events_type', 'event_type'),
        sa.Index('idx_analytics_events_timestamp', 'timestamp'),
        sa.Index('idx_analytics_events_project', 'project_id'),
        sa.Index('idx_analytics_events_user', 'user_id'),
        sa.Index('idx_analytics_events_tenant_type_ts', 'tenant_id', 'event_type', 'timestamp'),
    )

    # AnalyticsMetric table — aggregated metrics (daily, weekly, monthly)
    op.create_table(
        'analytics_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('metric_name', sa.String(128), nullable=False),
        sa.Column('metric_category', sa.String(64), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('metric_unit', sa.String(32), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('period', sa.String(32), nullable=False),  # "daily", "weekly", "monthly"
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_analytics_metrics_tenant', 'tenant_id'),
        sa.Index('idx_analytics_metrics_name', 'metric_name'),
        sa.Index('idx_analytics_metrics_date', 'date'),
        sa.Index('idx_analytics_metrics_project', 'project_id'),
        sa.Index('idx_analytics_metrics_tenant_name_date', 'tenant_id', 'metric_name', 'date'),
    )

    # SlackSubscription table — per-channel event subscriptions
    op.create_table(
        'slack_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('workspace_id', sa.String(64), nullable=False),
        sa.Column('channel_id', sa.String(64), nullable=False),
        sa.Column('channel_name', sa.String(128), nullable=True),
        sa.Column('event_types', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('webhook_url', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_slack_subscriptions_tenant', 'tenant_id'),
        sa.Index('idx_slack_subscriptions_workspace', 'workspace_id'),
        sa.Index('idx_slack_subscriptions_channel', 'channel_id'),
        sa.Index('idx_slack_subscriptions_active', 'is_active'),
        sa.UniqueConstraint('tenant_id', 'workspace_id', 'channel_id', name='uq_slack_sub_tenant_ws_ch'),
    )

    # SlackNotificationQueue — outbox pattern for retries
    op.create_table(
        'slack_notification_queue',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('webhook_url', sa.Text(), nullable=False),
        sa.Column('message_body', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, default='pending'),  # pending, sent, failed, dlq
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['slack_subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['analytics_events.id'], ondelete='CASCADE'),
        sa.Index('idx_slack_queue_tenant', 'tenant_id'),
        sa.Index('idx_slack_queue_status', 'status'),
        sa.Index('idx_slack_queue_subscription', 'subscription_id'),
        sa.Index('idx_slack_queue_status_tenant', 'status', 'tenant_id'),
        sa.Index('idx_slack_queue_last_attempt', 'last_attempt_at'),
    )

    # SlackDeliveryLog — audit trail for all Slack messages
    op.create_table(
        'slack_delivery_logs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('notification_queue_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('channel_id', sa.String(64), nullable=False),
        sa.Column('channel_name', sa.String(128), nullable=True),
        sa.Column('message_ts', sa.String(64), nullable=True),  # Slack message timestamp
        sa.Column('message_text', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('response_metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_slack_delivery_tenant', 'tenant_id'),
        sa.Index('idx_slack_delivery_channel', 'channel_id'),
        sa.Index('idx_slack_delivery_success', 'success'),
        sa.Index('idx_slack_delivery_timestamp', 'timestamp'),
        sa.Index('idx_slack_delivery_queue_id', 'notification_queue_id'),
    )

    # SlackDailyDigest — scheduled digest table
    op.create_table(
        'slack_daily_digests',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('digest_date', sa.Date(), nullable=False),
        sa.Column('digest_data', postgresql.JSONB(), nullable=False),
        sa.Column('message_ts', sa.String(64), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['slack_subscriptions.id'], ondelete='CASCADE'),
        sa.Index('idx_slack_digest_tenant', 'tenant_id'),
        sa.Index('idx_slack_digest_subscription', 'subscription_id'),
        sa.Index('idx_slack_digest_date', 'digest_date'),
        sa.Index('idx_slack_digest_sent', 'sent_at'),
        sa.UniqueConstraint('tenant_id', 'subscription_id', 'digest_date', name='uq_slack_digest_tenant_sub_date'),
    )


def downgrade() -> None:
    op.drop_table('slack_daily_digests')
    op.drop_table('slack_delivery_logs')
    op.drop_table('slack_notification_queue')
    op.drop_table('slack_subscriptions')
    op.drop_table('analytics_metrics')
    op.drop_table('analytics_events')
