"""Merge automation brain and agents workflow migration heads.

Revision ID: automation_agents_merge_0001
Revises: automation_brain_runs_0001, agents_v2_workflow_durability_0001
Create Date: 2026-05-18
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "automation_agents_merge_0001"
down_revision: Union[str, tuple[str, ...], None] = (
    "automation_brain_runs_0001",
    "agents_v2_workflow_durability_0001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
