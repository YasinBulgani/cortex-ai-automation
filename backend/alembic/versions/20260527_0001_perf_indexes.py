"""Add performance indexes for frequently queried columns.

Bu migration, sorgularda sık kullanılan kolonlara index ekler:
- tspm_scenarios.project_id        → LIST/COUNT sorguları için
- tspm_executions.project_id       → JOIN ve COUNT sorguları için
- tspm_executions.status           → aktif koşu filtresi için
- tspm_execution_metrics.project_id  → dashboard aggregation için
- tspm_execution_metrics.executed_at → haftalık trend tarih filtresi için
- tspm_execution_results.execution_id → execution result GROUP BY için
- tspm_execution_results.status      → passed/failed COUNT için
- tspm_approvals.project_id          → pending approval COUNT için
- tspm_approvals.status              → pending approval filtresi için
- tspm_project_members.user_id       → kullanıcının erişebildiği projeler için

Revision ID: perf_indexes_v2_0001
Revises: 20260524_0005
Create Date: 2026-05-27
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "perf_indexes_v2_0001"
down_revision: str = "20260524_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tspm_scenarios ────────────────────────────────────────────────────────
    op.create_index(
        "ix_tspm_scenarios_project_id",
        "tspm_scenarios",
        ["project_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_tspm_scenarios_project_status",
        "tspm_scenarios",
        ["project_id", "status"],
        if_not_exists=True,
    )

    # ── tspm_executions ───────────────────────────────────────────────────────
    op.create_index(
        "ix_tspm_executions_project_id",
        "tspm_executions",
        ["project_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_tspm_executions_status",
        "tspm_executions",
        ["status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_tspm_executions_project_created",
        "tspm_executions",
        ["project_id", "created_at"],
        if_not_exists=True,
    )

    # ── tspm_execution_metrics ────────────────────────────────────────────────
    op.create_index(
        "ix_tspm_exec_metrics_project_id",
        "tspm_execution_metrics",
        ["project_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_tspm_exec_metrics_project_executed",
        "tspm_execution_metrics",
        ["project_id", "executed_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_tspm_exec_metrics_executed_at",
        "tspm_execution_metrics",
        ["executed_at"],
        if_not_exists=True,
    )

    # ── tspm_execution_results ────────────────────────────────────────────────
    op.create_index(
        "ix_tspm_exec_results_execution_id",
        "tspm_execution_results",
        ["execution_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_tspm_exec_results_exec_status",
        "tspm_execution_results",
        ["execution_id", "status"],
        if_not_exists=True,
    )

    # ── tspm_approvals ────────────────────────────────────────────────────────
    op.create_index(
        "ix_tspm_approvals_project_id",
        "tspm_approvals",
        ["project_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_tspm_approvals_project_status",
        "tspm_approvals",
        ["project_id", "status"],
        if_not_exists=True,
    )

    # ── tspm_project_members ──────────────────────────────────────────────────
    op.create_index(
        "ix_tspm_project_members_user_id",
        "tspm_project_members",
        ["user_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_tspm_project_members_project_id",
        "tspm_project_members",
        ["project_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_tspm_project_members_project_id", table_name="tspm_project_members", if_exists=True)
    op.drop_index("ix_tspm_project_members_user_id", table_name="tspm_project_members", if_exists=True)
    op.drop_index("ix_tspm_approvals_project_status", table_name="tspm_approvals", if_exists=True)
    op.drop_index("ix_tspm_approvals_project_id", table_name="tspm_approvals", if_exists=True)
    op.drop_index("ix_tspm_exec_results_exec_status", table_name="tspm_execution_results", if_exists=True)
    op.drop_index("ix_tspm_exec_results_execution_id", table_name="tspm_execution_results", if_exists=True)
    op.drop_index("ix_tspm_exec_metrics_executed_at", table_name="tspm_execution_metrics", if_exists=True)
    op.drop_index("ix_tspm_exec_metrics_project_executed", table_name="tspm_execution_metrics", if_exists=True)
    op.drop_index("ix_tspm_exec_metrics_project_id", table_name="tspm_execution_metrics", if_exists=True)
    op.drop_index("ix_tspm_executions_project_created", table_name="tspm_executions", if_exists=True)
    op.drop_index("ix_tspm_executions_status", table_name="tspm_executions", if_exists=True)
    op.drop_index("ix_tspm_executions_project_id", table_name="tspm_executions", if_exists=True)
    op.drop_index("ix_tspm_scenarios_project_status", table_name="tspm_scenarios", if_exists=True)
    op.drop_index("ix_tspm_scenarios_project_id", table_name="tspm_scenarios", if_exists=True)
