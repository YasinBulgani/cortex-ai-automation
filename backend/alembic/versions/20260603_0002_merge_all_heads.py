"""Merge all migration branch heads into a single timeline.

Revision ID: 20260603_0002
Revises: 20260603_0001, 20260524_0005, agents_v2_workflow_durability_0001,
         approval_draft_0005, few_shot_bank_0001, llm_traces_0002,
         nexus_repo_0001, project_runtime_core_0010, syndata_0001,
         synthetic_platform_0001, tspm_execution_simulated_0001
Create Date: 2026-06-03

This merge has no schema changes — it only consolidates 11 parallel heads
into one so that `alembic upgrade head` works without ambiguity.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260603_0002"
down_revision: Union[str, tuple, None] = (
    "20260603_0001",
    "20260528_0005",
    "agents_v2_workflow_durability_0001",
    "automation_brain_runs_0001",
    "few_shot_bank_0001",
    "synthetic_platform_0001",
    "tspm_execution_simulated_0001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
