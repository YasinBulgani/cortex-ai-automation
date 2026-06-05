"""add_parent_id_to_cases

Revision ID: a1b2c3d4e5f6
Revises: f3990e7f3667
Create Date: 2026-06-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f3990e7f3667'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add parent_id self-referential FK to test_management_cases
    op.add_column(
        'test_management_cases',
        sa.Column(
            'parent_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('test_management_cases.id', ondelete='SET NULL'),
            nullable=True,
        )
    )
    op.create_index(
        'ix_test_management_cases_parent_id',
        'test_management_cases',
        ['parent_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_test_management_cases_parent_id', table_name='test_management_cases')
    op.drop_column('test_management_cases', 'parent_id')
