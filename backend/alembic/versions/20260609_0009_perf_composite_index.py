"""Add composite index for test case filtering performance.

Revision ID: 20260609_0009_perf_composite_index
Revises: 20260609_0008_fix_project_member_type
Create Date: 2026-06-09 14:00:00.000000

The query pattern `WHERE project_id = ? AND status = ? AND archived = FALSE`
occurs frequently in test case listing. The existing individual indexes on
(project_id), (project_id, status), and (project_id, archived) are insufficient.

This migration adds a composite index covering all three columns to enable
index-only scans for these queries.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '20260609_0009_perf_composite_index'
down_revision = '20260609_0008_fix_project_member_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add composite index for project + status + archived filtering."""
    # Add composite index covering common filter columns
    op.create_index(
        'ix_tm_cases_project_status_archived',
        'test_management_cases',
        ['project_id', 'status', 'archived'],
    )


def downgrade() -> None:
    """Remove composite index."""
    op.drop_index(
        'ix_tm_cases_project_status_archived',
        table_name='test_management_cases',
    )
