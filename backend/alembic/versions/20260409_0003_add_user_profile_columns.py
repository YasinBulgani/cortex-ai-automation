"""Add full_name, phone, department columns to sd_users

Revision ID: user_profile_0003
Revises: all_new_features_0002
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa

revision = "user_profile_0003"
down_revision = "all_new_features_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sd_users", sa.Column("full_name", sa.String(200), nullable=True))
    op.add_column("sd_users", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("sd_users", sa.Column("department", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("sd_users", "department")
    op.drop_column("sd_users", "phone")
    op.drop_column("sd_users", "full_name")
