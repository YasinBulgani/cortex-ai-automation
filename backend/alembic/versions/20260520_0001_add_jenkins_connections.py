"""Add Jenkins outbound connections table.

Revision ID: jenkins_connections_0001
Revises: add_tenant_id_users_0001
"""

from alembic import op


revision = "jenkins_connections_0001"
down_revision = "add_tenant_id_users_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cicd_jenkins_connections (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name          VARCHAR(128) NOT NULL,
            base_url      VARCHAR(512) NOT NULL,
            username      VARCHAR(256) NOT NULL,
            token_encrypted TEXT NOT NULL,
            owner_user_id UUID NULL,
            tenant_id     VARCHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
            last_status   VARCHAR(32) NOT NULL DEFAULT 'unknown',
            last_tested_at TIMESTAMPTZ NULL,
            last_error    TEXT NOT NULL DEFAULT '',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jenkins_conn_tenant
        ON cicd_jenkins_connections (tenant_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_jenkins_conn_tenant_name
        ON cicd_jenkins_connections (tenant_id, name)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_jenkins_conn_tenant_name")
    op.execute("DROP INDEX IF EXISTS idx_jenkins_conn_tenant")
    op.execute("DROP TABLE IF EXISTS cicd_jenkins_connections")
