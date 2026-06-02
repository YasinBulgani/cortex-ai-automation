"""Add M-1/M-2/M-9 design technique tables.

Revision ID: mgmt_design_tech_0001
Revises: org_teams_0001
Create Date: 2026-05-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "mgmt_design_tech_0001"
down_revision: str = "org_teams_0001"
branch_labels = None
depends_on = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())

    if "mgmt_design_technique_runs" not in existing:
        op.create_table(
            "mgmt_design_technique_runs",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, server_default=DEFAULT_TENANT_ID),
            sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=True),
            sa.Column("requirement_id", UUID(as_uuid=False), sa.ForeignKey("test_management_requirements.id", ondelete="SET NULL"), nullable=True),
            sa.Column("technique", sa.String(16), nullable=False),
            sa.Column("input_spec", JSONB(), nullable=False, server_default="{}"),
            sa.Column("generated_cases", JSONB(), nullable=False, server_default="[]"),
            sa.Column("llm_trace_id", sa.String(64), nullable=True),
            sa.Column("source", sa.String(16), nullable=False, server_default="manual"),
            sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    op.create_index("ix_mgmt_design_runs_tenant_id", "mgmt_design_technique_runs", ["tenant_id"], if_not_exists=True)
    op.create_index("ix_mgmt_design_runs_tenant_tech", "mgmt_design_technique_runs", ["tenant_id", "technique"], if_not_exists=True)
    op.create_index("ix_mgmt_design_runs_req", "mgmt_design_technique_runs", ["requirement_id"], if_not_exists=True)

    if "mgmt_design_input_fields" not in existing:
        op.create_table(
            "mgmt_design_input_fields",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("run_id", UUID(as_uuid=False), sa.ForeignKey("mgmt_design_technique_runs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("data_type", sa.String(32), nullable=False),
            sa.Column("min_value", sa.String(128), nullable=True),
            sa.Column("max_value", sa.String(128), nullable=True),
            sa.Column("allowed_set", JSONB(), nullable=True),
            sa.Column("nullable", sa.Boolean(), nullable=False, server_default="false"),
        )
    op.create_index("ix_mgmt_design_input_fields_run_id", "mgmt_design_input_fields", ["run_id"], if_not_exists=True)

    if "mgmt_design_partitions" not in existing:
        op.create_table(
            "mgmt_design_partitions",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("run_id", UUID(as_uuid=False), sa.ForeignKey("mgmt_design_technique_runs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("field_id", UUID(as_uuid=False), sa.ForeignKey("mgmt_design_input_fields.id", ondelete="CASCADE"), nullable=False),
            sa.Column("partition_label", sa.String(128), nullable=False),
            sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("sample_value", sa.String(256), nullable=True),
        )
    op.create_index("ix_mgmt_design_partitions_run_id", "mgmt_design_partitions", ["run_id"], if_not_exists=True)

    if "mgmt_case_param_sets" not in existing:
        op.create_table(
            "mgmt_case_param_sets",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, server_default=DEFAULT_TENANT_ID),
            sa.Column("case_id", UUID(as_uuid=False), sa.ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("schema_json", JSONB(), nullable=False, server_default="{}"),
            sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    op.create_index("ix_mgmt_case_param_sets_tenant_id", "mgmt_case_param_sets", ["tenant_id"], if_not_exists=True)
    op.create_index("ix_mgmt_case_param_sets_case_id", "mgmt_case_param_sets", ["case_id"], if_not_exists=True)

    if "mgmt_case_data_rows" not in existing:
        op.create_table(
            "mgmt_case_data_rows",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("param_set_id", UUID(as_uuid=False), sa.ForeignKey("mgmt_case_param_sets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("values", JSONB(), nullable=False),
            sa.Column("expected", JSONB(), nullable=False, server_default="{}"),
            sa.Column("source_type", sa.String(16), nullable=False, server_default="manual"),
            sa.Column("category", sa.String(32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    op.create_index("ix_mgmt_case_data_rows_param_set_id", "mgmt_case_data_rows", ["param_set_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_mgmt_case_data_rows_param_set_id", table_name="mgmt_case_data_rows")
    op.drop_table("mgmt_case_data_rows")
    op.drop_index("ix_mgmt_case_param_sets_case_id", table_name="mgmt_case_param_sets")
    op.drop_index("ix_mgmt_case_param_sets_tenant_id", table_name="mgmt_case_param_sets")
    op.drop_table("mgmt_case_param_sets")
    op.drop_index("ix_mgmt_design_partitions_run_id", table_name="mgmt_design_partitions")
    op.drop_table("mgmt_design_partitions")
    op.drop_index("ix_mgmt_design_input_fields_run_id", table_name="mgmt_design_input_fields")
    op.drop_table("mgmt_design_input_fields")
    op.drop_index("ix_mgmt_design_runs_req", table_name="mgmt_design_technique_runs")
    op.drop_index("ix_mgmt_design_runs_tenant_tech", table_name="mgmt_design_technique_runs")
    op.drop_index("ix_mgmt_design_runs_tenant_id", table_name="mgmt_design_technique_runs")
    op.drop_table("mgmt_design_technique_runs")
