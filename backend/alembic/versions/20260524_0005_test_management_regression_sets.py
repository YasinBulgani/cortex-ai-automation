"""Add test management regression set tables.

Revision ID: 20260524_0005
Revises: user_mfa_totp_0001
Create Date: 2026-05-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260524_0005"
down_revision = "user_mfa_totp_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_management_regression_sets",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("set_type", sa.String(32), nullable=False, server_default="regression"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_filters", JSONB, nullable=False, server_default="{}"),
        sa.Column("selection_summary", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "name", name="uq_tm_regression_sets_project_name"),
    )
    op.create_index("ix_tm_regression_sets_project_id", "test_management_regression_sets", ["project_id"])

    op.create_table(
        "test_management_regression_set_cases",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("regression_set_id", UUID(as_uuid=False), sa.ForeignKey("test_management_regression_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("case_key_snapshot", sa.String(64), nullable=False, server_default=""),
        sa.Column("title_snapshot", sa.String(500), nullable=False, server_default=""),
        sa.Column("priority_snapshot", sa.String(32), nullable=False, server_default=""),
        sa.Column("severity_snapshot", sa.String(32), nullable=False, server_default=""),
        sa.Column("type_snapshot", sa.String(64), nullable=False, server_default=""),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("include_mode", sa.String(32), nullable=False, server_default="suggested"),
        sa.UniqueConstraint("regression_set_id", "case_id", name="uq_tm_regression_set_cases_set_case"),
    )
    op.create_index("ix_tm_regression_set_cases_set_id", "test_management_regression_set_cases", ["regression_set_id"])
    op.create_index("ix_tm_regression_set_cases_case_id", "test_management_regression_set_cases", ["case_id"])
    op.add_column("test_management_runs", sa.Column("source_type", sa.String(32), nullable=False, server_default="manual"))
    op.add_column("test_management_runs", sa.Column("source_ref", UUID(as_uuid=False), nullable=True))
    op.add_column("test_management_runs", sa.Column("scope_snapshot", JSONB, nullable=False, server_default="{}"))
    op.add_column("test_management_run_cases", sa.Column("case_snapshot", JSONB, nullable=False, server_default="{}"))
    op.add_column("test_management_defect_links", sa.Column("severity", sa.String(32), nullable=False, server_default="major"))
    op.add_column("test_management_defect_links", sa.Column("priority", sa.String(32), nullable=False, server_default="P2"))
    op.add_column("test_management_defect_links", sa.Column("assignee_id", UUID(as_uuid=False), nullable=True))
    op.add_column("test_management_defect_links", sa.Column("root_cause", sa.String(100), nullable=True))
    op.add_column("test_management_defect_links", sa.Column("retest_status", sa.String(32), nullable=False, server_default="not_ready"))
    op.add_column("test_management_defect_links", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("test_management_defect_links", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("test_management_defect_links", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_foreign_key(
        "fk_tm_defect_links_assignee_id",
        "test_management_defect_links",
        "sd_users",
        ["assignee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "test_management_release_signoffs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_name", sa.String(200), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="signed"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("report_snapshot", JSONB, nullable=False, server_default="{}"),
        sa.Column("signed_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tm_release_signoffs_project_id", "test_management_release_signoffs", ["project_id"])
    op.create_table(
        "test_management_requirements",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_source", sa.String(32), nullable=False, server_default="internal"),
        sa.Column("external_key", sa.String(200), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("owner_id", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("acceptance_criteria", JSONB, nullable=False, server_default="[]"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "external_source", "external_key", name="uq_tm_requirements_project_source_key"),
    )
    op.create_index("ix_tm_requirements_project_id", "test_management_requirements", ["project_id"])
    op.add_column("test_management_requirement_links", sa.Column("requirement_id", UUID(as_uuid=False), nullable=True))
    op.create_index("ix_tm_requirement_links_requirement_id", "test_management_requirement_links", ["requirement_id"])
    op.create_foreign_key(
        "fk_tm_requirement_links_requirement_id",
        "test_management_requirement_links",
        "test_management_requirements",
        ["requirement_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("""
        ALTER TABLE test_management_release_signoffs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE test_management_release_signoffs FORCE ROW LEVEL SECURITY;
        CREATE POLICY rls_tenant_isolation ON test_management_release_signoffs
            USING (
                project_id IN (
                    SELECT id FROM test_management_projects
                    WHERE tenant_id = current_tenant_id()
                )
            );
        ALTER TABLE test_management_requirements ENABLE ROW LEVEL SECURITY;
        ALTER TABLE test_management_requirements FORCE ROW LEVEL SECURITY;
        CREATE POLICY rls_tenant_isolation ON test_management_requirements
            USING (
                project_id IN (
                    SELECT id FROM test_management_projects
                    WHERE tenant_id = current_tenant_id()
                )
            );
        ALTER TABLE test_management_regression_sets ENABLE ROW LEVEL SECURITY;
        ALTER TABLE test_management_regression_sets FORCE ROW LEVEL SECURITY;
        CREATE POLICY rls_tenant_isolation ON test_management_regression_sets
            USING (
                project_id IN (
                    SELECT id FROM test_management_projects
                    WHERE tenant_id = current_tenant_id()
                )
            );
        ALTER TABLE test_management_regression_set_cases ENABLE ROW LEVEL SECURITY;
        CREATE POLICY rls_service_layer_owns ON test_management_regression_set_cases USING (TRUE);
    """)


def downgrade() -> None:
    op.drop_constraint("fk_tm_requirement_links_requirement_id", "test_management_requirement_links", type_="foreignkey")
    op.drop_index("ix_tm_requirement_links_requirement_id", table_name="test_management_requirement_links")
    op.drop_column("test_management_requirement_links", "requirement_id")
    op.drop_column("test_management_runs", "scope_snapshot")
    op.drop_column("test_management_runs", "source_ref")
    op.drop_column("test_management_runs", "source_type")
    op.drop_column("test_management_run_cases", "case_snapshot")
    op.drop_constraint("fk_tm_defect_links_assignee_id", "test_management_defect_links", type_="foreignkey")
    op.drop_column("test_management_defect_links", "updated_at")
    op.drop_column("test_management_defect_links", "verified_at")
    op.drop_column("test_management_defect_links", "resolved_at")
    op.drop_column("test_management_defect_links", "retest_status")
    op.drop_column("test_management_defect_links", "root_cause")
    op.drop_column("test_management_defect_links", "assignee_id")
    op.drop_column("test_management_defect_links", "priority")
    op.drop_column("test_management_defect_links", "severity")
    op.execute("""
        ALTER TABLE test_management_release_signoffs DISABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS rls_tenant_isolation ON test_management_release_signoffs;
        ALTER TABLE test_management_requirements DISABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS rls_tenant_isolation ON test_management_requirements;
        ALTER TABLE test_management_regression_set_cases DISABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS rls_service_layer_owns ON test_management_regression_set_cases;
        ALTER TABLE test_management_regression_sets DISABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS rls_tenant_isolation ON test_management_regression_sets;
    """)
    op.drop_index("ix_tm_requirements_project_id", table_name="test_management_requirements")
    op.drop_table("test_management_requirements")
    op.drop_index("ix_tm_release_signoffs_project_id", table_name="test_management_release_signoffs")
    op.drop_table("test_management_release_signoffs")
    op.drop_index("ix_tm_regression_set_cases_case_id", table_name="test_management_regression_set_cases")
    op.drop_index("ix_tm_regression_set_cases_set_id", table_name="test_management_regression_set_cases")
    op.drop_table("test_management_regression_set_cases")
    op.drop_index("ix_tm_regression_sets_project_id", table_name="test_management_regression_sets")
    op.drop_table("test_management_regression_sets")
