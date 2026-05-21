"""Add base_url to tspm_projects

Revision ID: project_base_url_0009
Revises: coverup_scope_0008
"""

from alembic import op

revision = "project_base_url_0009"
down_revision = "coverup_scope_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tspm_projects
        ADD COLUMN IF NOT EXISTS base_url VARCHAR(500) NOT NULL DEFAULT ''
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tspm_projects DROP COLUMN IF EXISTS base_url")
