"""Add foreign key constraint to ProjectMember.project_id.

Revision ID: project_members_fk_001
Revises: rls_new_mgmt_tables_001
Create Date: 2026-06-09

Adds missing ForeignKey constraint from sd_project_members.project_id
to test_management_projects.id with CASCADE delete.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "project_members_fk_001"
down_revision: Union[str, None] = "rls_new_mgmt_tables_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add foreign key constraint to project_id
    op.create_foreign_key(
        "fk_project_members_project_id",
        "sd_project_members",
        "test_management_projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop the foreign key constraint
    op.drop_constraint(
        "fk_project_members_project_id",
        "sd_project_members",
        type_="foreignkey",
    )
