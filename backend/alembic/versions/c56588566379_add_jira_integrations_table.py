"""add_jira_integrations_table

Revision ID: c56588566379
Revises: 20260603_0004
Create Date: 2026-06-04 16:06:21.639033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c56588566379'
down_revision: Union[str, None] = '20260603_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'jira_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('jira_url', sa.String(length=500), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('api_token', sa.String(length=1024), nullable=False),
        sa.Column('default_project_key', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_jira_integrations_tenant_id', 'jira_integrations', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_jira_integrations_tenant_id', table_name='jira_integrations')
    op.drop_table('jira_integrations')
