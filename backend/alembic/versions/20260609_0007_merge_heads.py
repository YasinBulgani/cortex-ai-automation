"""Merge database migration branches.

Revision ID: 20260609_0007
Revises: 20260608_0007, 20260609_0006
Create Date: 2026-06-09

Merges the two migration heads:
- 20260608_0007 (mobile sessions + exploration sessions)
- 20260609_0006 (DB fixes: constraints, indexes, cascade patterns)
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "20260609_0007_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("20260608_0007", "20260609_0006")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No operations - this is a pure merge commit
    pass


def downgrade() -> None:
    # No operations - downgrade is a no-op for merge commits
    pass
