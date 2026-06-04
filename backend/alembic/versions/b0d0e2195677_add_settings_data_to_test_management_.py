"""add_settings_data_to_test_management_projects

Revision ID: b0d0e2195677
Revises: c56588566379
Create Date: 2026-06-04 23:26:29.609230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b0d0e2195677'
down_revision: Union[str, None] = 'c56588566379'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kullanıcı ayarları için JSON sütunu ekle
    op.add_column(
        'test_management_projects',
        sa.Column('settings_data', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('test_management_projects', 'settings_data')
