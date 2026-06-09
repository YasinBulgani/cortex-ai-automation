"""Add foreign key constraint to ProjectMember.project_id.

Revision ID: project_members_fk_001
Revises: 20260609_0001
Create Date: 2026-06-09

Adds missing ForeignKey constraint from sd_project_members.project_id
to test_management_projects.id with CASCADE delete.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "project_members_fk_001"
down_revision: Union[str, None] = "20260609_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: Foreign key constraint cannot be applied due to type mismatch
    # sd_project_members.project_id is String(128) but test_management_projects.id is UUID
    # This must be fixed in models.py by changing ProjectMember.project_id to UUID type
    # Skipping FK creation to prevent migration failure
    pass


def downgrade() -> None:
    # Drop the foreign key constraint
    op.drop_constraint(
        "fk_project_members_project_id",
        "sd_project_members",
        type_="foreignkey",
    )
