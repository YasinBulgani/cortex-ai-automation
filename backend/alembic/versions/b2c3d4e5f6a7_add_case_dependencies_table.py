"""add_case_dependencies_table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('test_management_case_dependencies',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('depends_on_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('dep_type', sa.String(32), server_default='blocks', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['test_management_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depends_on_id'], ['test_management_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_id', 'depends_on_id', name='uq_tm_case_deps_case_dep'),
    )
    op.create_index('ix_tm_case_dependencies_case_id', 'test_management_case_dependencies', ['case_id'])
    op.create_index('ix_tm_case_dependencies_depends_on_id', 'test_management_case_dependencies', ['depends_on_id'])


def downgrade() -> None:
    op.drop_index('ix_tm_case_dependencies_depends_on_id', table_name='test_management_case_dependencies')
    op.drop_index('ix_tm_case_dependencies_case_id', table_name='test_management_case_dependencies')
    op.drop_table('test_management_case_dependencies')
