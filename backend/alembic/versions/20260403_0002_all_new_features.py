"""All new feature tables: RBAC, requirements, versions, schedules, metrics, integrations, api-testing, test-data.

Revision ID: all_new_features_0002
Revises: 86656e38793d
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "all_new_features_0002"
down_revision = "86656e38793d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RBAC: role permissions
    op.create_table(
        "sd_role_permissions",
        sa.Column("role_id", UUID(as_uuid=False), sa.ForeignKey("sd_roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission", sa.String(128), primary_key=True),
    )

    # RBAC: project members
    op.create_table(
        "tspm_project_members",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    # Requirements
    op.create_table(
        "tspm_requirements",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    op.create_table(
        "tspm_scenario_requirements",
        sa.Column("scenario_id", UUID(as_uuid=False), sa.ForeignKey("tspm_scenarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("requirement_id", UUID(as_uuid=False), sa.ForeignKey("tspm_requirements.id", ondelete="CASCADE"), primary_key=True),
    )

    # Scenario versions
    op.create_table(
        "tspm_scenario_versions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("scenario_id", UUID(as_uuid=False), sa.ForeignKey("tspm_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("steps", JSONB, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("changed_by", UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    # Execution metrics
    op.create_table(
        "tspm_execution_metrics",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_id", UUID(as_uuid=False), sa.ForeignKey("tspm_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pass_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    # Schedules
    op.create_table(
        "tspm_schedules",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("regression_set_id", UUID(as_uuid=False), sa.ForeignKey("tspm_regression_sets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scenario_ids", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    # Test data sets
    op.create_table(
        "tspm_test_data_sets",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("columns", JSONB, nullable=True),
        sa.Column("rows", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    op.create_table(
        "tspm_scenario_data_bindings",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("scenario_id", UUID(as_uuid=False), sa.ForeignKey("tspm_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_set_id", UUID(as_uuid=False), sa.ForeignKey("tspm_test_data_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parameter_mapping", JSONB, nullable=True),
    )

    # Integrations
    op.create_table(
        "tspm_integrations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    # API testing
    op.create_table(
        "tspm_api_collections",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("base_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("headers", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    op.create_table(
        "tspm_api_requests",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("collection_id", UUID(as_uuid=False), sa.ForeignKey("tspm_api_collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("method", sa.String(16), nullable=False, server_default="GET"),
        sa.Column("path", sa.String(1000), nullable=False, server_default="/"),
        sa.Column("headers", JSONB, nullable=True),
        sa.Column("body", JSONB, nullable=True),
        sa.Column("assertions", JSONB, nullable=True),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "tspm_api_test_runs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("collection_id", UUID(as_uuid=False), sa.ForeignKey("tspm_api_collections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("results", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )


def downgrade() -> None:
    op.drop_table("tspm_api_test_runs")
    op.drop_table("tspm_api_requests")
    op.drop_table("tspm_api_collections")
    op.drop_table("tspm_integrations")
    op.drop_table("tspm_scenario_data_bindings")
    op.drop_table("tspm_test_data_sets")
    op.drop_table("tspm_schedules")
    op.drop_table("tspm_execution_metrics")
    op.drop_table("tspm_scenario_versions")
    op.drop_table("tspm_scenario_requirements")
    op.drop_table("tspm_requirements")
    op.drop_table("tspm_project_members")
    op.drop_table("sd_role_permissions")
