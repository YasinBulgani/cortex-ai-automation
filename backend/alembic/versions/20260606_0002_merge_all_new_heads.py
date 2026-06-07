"""merge_all_new_heads

QA analizi sırasında oluşan 2 migration branch'ını tek head'de birleştirir.
Schema değişikliği yoktur — sadece merge.

Branch 1: 20260606_0001 (missing tables + columns)
Branch 2: 20260605_0001 (fix_runcase_cascade → shared_steps → case_deps → parent_id → settings_data)

Revision ID: 20260606_0002
Revises: 20260606_0001, 20260605_0001
Create Date: 2026-06-06 01:00:00.000000

"""
from typing import Sequence, Union

revision: str = "20260606_0002"
down_revision: Union[str, tuple, None] = ("20260606_0001", "20260605_0001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
