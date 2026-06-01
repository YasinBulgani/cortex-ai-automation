"""Add Neurex Management manual test tables.

Revision ID: 20260524_0002
Revises: 20260524_0001, billing_processed_webhooks_0001, jenkins_connections_0001
Create Date: 2026-05-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260524_0002"
down_revision = ("20260524_0001", "billing_processed_webhooks_0001", "jenkins_connections_0001")
branch_labels = None
depends_on = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "test_management_projects",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, server_default=DEFAULT_TENANT_ID),
        sa.Column("tspm_project_id", UUID(as_uuid=False), sa.ForeignKey("tspm_projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("key", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "key", name="uq_test_management_projects_tenant_key"),
    )
    op.create_index("ix_test_management_projects_tenant_id", "test_management_projects", ["tenant_id"])
    op.create_index("ix_test_management_projects_tspm_project_id", "test_management_projects", ["tspm_project_id"])

    op.create_table(
        "test_management_suites",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "name", name="uq_tm_suites_project_name"),
    )
    op.create_index("ix_tm_suites_project_id", "test_management_suites", ["project_id"])

    op.create_table(
        "test_management_folders",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("suite_id", UUID(as_uuid=False), sa.ForeignKey("test_management_suites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=False), sa.ForeignKey("test_management_folders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("path", sa.String(1000), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("suite_id", "path", name="uq_tm_folders_suite_path"),
    )
    op.create_index("ix_tm_folders_suite_id", "test_management_folders", ["suite_id"])

    op.create_table(
        "test_management_cases",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("suite_id", UUID(as_uuid=False), sa.ForeignKey("test_management_suites.id", ondelete="SET NULL"), nullable=True),
        sa.Column("folder_id", UUID(as_uuid=False), sa.ForeignKey("test_management_folders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("case_key", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("test_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("severity", sa.String(32), nullable=False, server_default="major"),
        sa.Column("type", sa.String(64), nullable=False, server_default="functional"),
        sa.Column("automation_status", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("source_ref", sa.String(200), nullable=True),
        sa.Column("owner_id", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("custom_fields", JSONB, nullable=False, server_default="{}"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_run_status", sa.String(32), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_id", UUID(as_uuid=False), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "case_key", name="uq_tm_cases_project_key"),
    )
    op.create_index("ix_tm_cases_project_id", "test_management_cases", ["project_id"])
    op.create_index("ix_tm_cases_suite_id", "test_management_cases", ["suite_id"])
    op.create_index("ix_tm_cases_folder_id", "test_management_cases", ["folder_id"])

    op.create_table(
        "test_management_case_steps",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column("test_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("case_id", "step_no", name="uq_tm_case_steps_case_step"),
    )
    op.create_index("ix_tm_case_steps_case_id", "test_management_case_steps", ["case_id"])

    op.create_table(
        "test_management_case_versions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("changed_fields", JSONB, nullable=False, server_default="[]"),
        sa.Column("snapshot_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "version_no", name="uq_tm_case_versions_case_version"),
    )
    op.create_index("ix_tm_case_versions_case_id", "test_management_case_versions", ["case_id"])

    op.create_table(
        "test_management_plans",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("plan_type", sa.String(32), nullable=False, server_default="regression"),
        sa.Column("release_name", sa.String(200), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("scope_summary", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tm_plans_project_id", "test_management_plans", ["project_id"])

    op.create_table(
        "test_management_cycles",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("plan_id", UUID(as_uuid=False), sa.ForeignKey("test_management_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("environment", sa.String(100), nullable=True),
        sa.Column("build_version", sa.String(100), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tm_cycles_plan_id", "test_management_cycles", ["plan_id"])

    op.create_table(
        "test_management_runs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("cycle_id", UUID(as_uuid=False), sa.ForeignKey("test_management_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_started"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tm_runs_cycle_id", "test_management_runs", ["cycle_id"])

    op.create_table(
        "test_management_run_cases",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=False), sa.ForeignKey("test_management_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_version_no", sa.Integer(), nullable=False),
        sa.Column("assigned_to", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_run"),
        sa.Column("actual_result", sa.Text(), nullable=True),
        sa.Column("execution_notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.UniqueConstraint("run_id", "case_id", name="uq_tm_run_cases_run_case"),
    )
    op.create_index("ix_tm_run_cases_run_id", "test_management_run_cases", ["run_id"])
    op.create_index("ix_tm_run_cases_case_id", "test_management_run_cases", ["case_id"])

    op.create_table(
        "test_management_run_step_results",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("run_case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_run_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_run"),
        sa.Column("actual_result", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_case_id", "step_no", name="uq_tm_run_step_results_case_step"),
    )
    op.create_index("ix_tm_run_step_results_run_case_id", "test_management_run_step_results", ["run_case_id"])

    op.create_table(
        "test_management_execution_evidence",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("run_case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_run_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_result_id", UUID(as_uuid=False), sa.ForeignKey("test_management_run_step_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("artifact_id", UUID(as_uuid=False), sa.ForeignKey("sd_artifacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False, server_default="other"),
        sa.Column("storage_url", sa.String(1000), nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tm_execution_evidence_run_case_id", "test_management_execution_evidence", ["run_case_id"])

    op.create_table(
        "test_management_requirement_links",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_source", sa.String(32), nullable=False, server_default="internal"),
        sa.Column("external_key", sa.String(200), nullable=False),
        sa.Column("title_snapshot", sa.String(500), nullable=False),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("coverage_status", sa.String(32), nullable=False, server_default="covered"),
    )
    op.create_index("ix_tm_requirement_links_project_id", "test_management_requirement_links", ["project_id"])
    op.create_index("ix_tm_requirement_links_case_id", "test_management_requirement_links", ["case_id"])

    op.create_table(
        "test_management_defect_links",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("run_case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_run_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_result_id", UUID(as_uuid=False), sa.ForeignKey("test_management_run_step_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("external_source", sa.String(32), nullable=False, server_default="internal"),
        sa.Column("external_key", sa.String(200), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(100), nullable=False, server_default="open"),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tm_defect_links_run_case_id", "test_management_defect_links", ["run_case_id"])

    op.create_table(
        "test_management_import_jobs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="preview"),
        sa.Column("mapping", JSONB, nullable=False, server_default="{}"),
        sa.Column("totals", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tm_import_jobs_project_id", "test_management_import_jobs", ["project_id"])

    op.create_table(
        "test_management_import_job_rows",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=False), sa.ForeignKey("test_management_import_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("parsed_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("validation_errors", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="ready"),
        sa.Column("conflict_key", sa.String(200), nullable=True),
    )
    op.create_index("ix_tm_import_job_rows_job_id", "test_management_import_job_rows", ["job_id"])

    op.create_table(
        "test_management_audit_events",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=False), nullable=True),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tm_audit_events_project_id", "test_management_audit_events", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_tm_audit_events_project_id", table_name="test_management_audit_events")
    op.drop_table("test_management_audit_events")
    op.drop_index("ix_tm_import_job_rows_job_id", table_name="test_management_import_job_rows")
    op.drop_table("test_management_import_job_rows")
    op.drop_index("ix_tm_import_jobs_project_id", table_name="test_management_import_jobs")
    op.drop_table("test_management_import_jobs")
    op.drop_index("ix_tm_defect_links_run_case_id", table_name="test_management_defect_links")
    op.drop_table("test_management_defect_links")
    op.drop_index("ix_tm_requirement_links_case_id", table_name="test_management_requirement_links")
    op.drop_index("ix_tm_requirement_links_project_id", table_name="test_management_requirement_links")
    op.drop_table("test_management_requirement_links")
    op.drop_index("ix_tm_execution_evidence_run_case_id", table_name="test_management_execution_evidence")
    op.drop_table("test_management_execution_evidence")
    op.drop_index("ix_tm_run_step_results_run_case_id", table_name="test_management_run_step_results")
    op.drop_table("test_management_run_step_results")
    op.drop_index("ix_tm_run_cases_case_id", table_name="test_management_run_cases")
    op.drop_index("ix_tm_run_cases_run_id", table_name="test_management_run_cases")
    op.drop_table("test_management_run_cases")
    op.drop_index("ix_tm_runs_cycle_id", table_name="test_management_runs")
    op.drop_table("test_management_runs")
    op.drop_index("ix_tm_cycles_plan_id", table_name="test_management_cycles")
    op.drop_table("test_management_cycles")
    op.drop_index("ix_tm_plans_project_id", table_name="test_management_plans")
    op.drop_table("test_management_plans")
    op.drop_index("ix_tm_case_versions_case_id", table_name="test_management_case_versions")
    op.drop_table("test_management_case_versions")
    op.drop_index("ix_tm_case_steps_case_id", table_name="test_management_case_steps")
    op.drop_table("test_management_case_steps")
    op.drop_index("ix_tm_cases_folder_id", table_name="test_management_cases")
    op.drop_index("ix_tm_cases_suite_id", table_name="test_management_cases")
    op.drop_index("ix_tm_cases_project_id", table_name="test_management_cases")
    op.drop_table("test_management_cases")
    op.drop_index("ix_tm_folders_suite_id", table_name="test_management_folders")
    op.drop_table("test_management_folders")
    op.drop_index("ix_tm_suites_project_id", table_name="test_management_suites")
    op.drop_table("test_management_suites")
    op.drop_index("ix_test_management_projects_tspm_project_id", table_name="test_management_projects")
    op.drop_index("ix_test_management_projects_tenant_id", table_name="test_management_projects")
    op.drop_table("test_management_projects")
