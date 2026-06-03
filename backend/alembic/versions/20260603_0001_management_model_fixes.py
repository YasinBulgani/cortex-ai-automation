"""management model fixes: executed_at, cycle.project_id, composite indexes

Revision ID: 20260603_0001
Revises: 20260602_0001
Create Date: 2026-06-03

Changes:
- Add executed_at to test_management_run_step_results
- Add project_id to test_management_cycles (denormalized for performance)
- Add composite indexes on test_management_cases (project_id, status/archived)
- Add composite indexes on test_management_audit_events (entity, project/created_at)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260603_0001"
down_revision = "20260602_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── TestRunStepResult: add executed_at ────────────────────────────────────
    op.add_column(
        "test_management_run_step_results",
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── TestCycle: add project_id (denormalized) ──────────────────────────────
    op.add_column(
        "test_management_cycles",
        sa.Column("project_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_tm_cycles_project_id",
        "test_management_cycles",
        ["project_id"],
    )
    # Backfill project_id from plan join
    op.execute(
        """
        UPDATE test_management_cycles c
        SET project_id = p.project_id
        FROM test_management_plans p
        WHERE c.plan_id = p.id
          AND c.project_id IS NULL
        """
    )

    # ── TestCase: composite indexes ────────────────────────────────────────────
    op.create_index(
        "ix_tm_cases_project_status",
        "test_management_cases",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_tm_cases_project_archived",
        "test_management_cases",
        ["project_id", "archived"],
    )

    # ── AuditEvent: composite indexes ─────────────────────────────────────────
    op.create_index(
        "ix_tm_audit_entity",
        "test_management_audit_events",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_tm_audit_project_created",
        "test_management_audit_events",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_tm_audit_project_created", "test_management_audit_events")
    op.drop_index("ix_tm_audit_entity", "test_management_audit_events")
    op.drop_index("ix_tm_cases_project_archived", "test_management_cases")
    op.drop_index("ix_tm_cases_project_status", "test_management_cases")
    op.drop_index("ix_tm_cycles_project_id", "test_management_cycles")
    op.drop_column("test_management_cycles", "project_id")
    op.drop_column("test_management_run_step_results", "executed_at")
