"""merge_nexus_repo_and_runtime_core

Revision ID: b4682f9d1d6c
Revises: nexus_repo_0001, project_runtime_core_0010
Create Date: 2026-04-24 18:11:20.175056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4682f9d1d6c'
down_revision: Union[str, None] = ('nexus_repo_0001', 'project_runtime_core_0010')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
