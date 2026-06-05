"""fix TestRunCase.case_id ondelete CASCADE → SET NULL

Revision ID: 20260605_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20260605_0001"
down_revision = "b2c3d4e5f6a7"  # add_case_dependencies_table
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Drop eski FK constraint
    op.drop_constraint("test_management_run_cases_case_id_fkey", "test_management_run_cases", type_="foreignkey")
    # case_id nullable yap
    op.alter_column("test_management_run_cases", "case_id", nullable=True)
    # Yeni FK constraint — SET NULL
    op.create_foreign_key(
        "test_management_run_cases_case_id_fkey",
        "test_management_run_cases", "test_management_cases",
        ["case_id"], ["id"],
        ondelete="SET NULL",
    )

def downgrade() -> None:
    op.drop_constraint("test_management_run_cases_case_id_fkey", "test_management_run_cases", type_="foreignkey")
    op.alter_column("test_management_run_cases", "case_id", nullable=False)
    op.create_foreign_key(
        "test_management_run_cases_case_id_fkey",
        "test_management_run_cases", "test_management_cases",
        ["case_id"], ["id"],
        ondelete="CASCADE",
    )
