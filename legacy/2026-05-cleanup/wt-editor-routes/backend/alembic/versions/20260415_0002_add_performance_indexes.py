"""Add performance indexes for high-frequency query columns

Sık kullanılan kolonlara composite index ekler:
  - tspm_scenarios(project_id, status)
  - tspm_scenarios(project_id, created_at)
  - tspm_executions(project_id, status)
  - tspm_executions(project_id, created_at)
  - tspm_execution_results(execution_id, status)
  - tspm_execution_metrics(project_id, executed_at)
  - tspm_approvals(project_id, status)
  - tspm_project_members(user_id)        ← list_projects JOIN için kritik
  - tspm_project_members(project_id)     ← üye listeleme için

Revision ID: perf_indexes_0001
Revises: mobile_0001
"""

from alembic import op

revision = "perf_indexes_0001"
down_revision = "mobile_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_tspm_scenarios_project_status",
        "tspm_scenarios",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_tspm_scenarios_project_created",
        "tspm_scenarios",
        ["project_id", "created_at"],
    )

    op.create_index(
        "ix_tspm_executions_project_status",
        "tspm_executions",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_tspm_executions_project_created",
        "tspm_executions",
        ["project_id", "created_at"],
    )

    op.create_index(
        "ix_tspm_execution_results_exec_status",
        "tspm_execution_results",
        ["execution_id", "status"],
    )

    op.create_index(
        "ix_tspm_execution_metrics_project_ts",
        "tspm_execution_metrics",
        ["project_id", "executed_at"],
    )

    op.create_index(
        "ix_tspm_approvals_project_status",
        "tspm_approvals",
        ["project_id", "status"],
    )

    # Bu iki index list_projects() JOIN sorgusunu dramatik şekilde hızlandırır
    op.create_index(
        "ix_tspm_project_members_user_id",
        "tspm_project_members",
        ["user_id"],
    )
    op.create_index(
        "ix_tspm_project_members_project_id",
        "tspm_project_members",
        ["project_id"],
    )

    op.create_index(
        "ix_tspm_requirements_project_created",
        "tspm_requirements",
        ["project_id", "created_at"],
    )

    op.create_index(
        "ix_tspm_scenario_requirements_req_id",
        "tspm_scenario_requirements",
        ["requirement_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tspm_scenario_requirements_req_id", "tspm_scenario_requirements")
    op.drop_index("ix_tspm_requirements_project_created", "tspm_requirements")
    op.drop_index("ix_tspm_project_members_project_id", "tspm_project_members")
    op.drop_index("ix_tspm_project_members_user_id", "tspm_project_members")
    op.drop_index("ix_tspm_approvals_project_status", "tspm_approvals")
    op.drop_index("ix_tspm_execution_metrics_project_ts", "tspm_execution_metrics")
    op.drop_index("ix_tspm_execution_results_exec_status", "tspm_execution_results")
    op.drop_index("ix_tspm_executions_project_created", "tspm_executions")
    op.drop_index("ix_tspm_executions_project_status", "tspm_executions")
    op.drop_index("ix_tspm_scenarios_project_created", "tspm_scenarios")
    op.drop_index("ix_tspm_scenarios_project_status", "tspm_scenarios")
