"""Add Kiwi TCMS integration tables.

Revision ID: 20260603_0003
Revises: 20260603_0002
Create Date: 2026-06-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260603_0003"
down_revision = "20260603_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())

    if "kiwi_connections" not in existing:
        op.create_table(
            "kiwi_connections",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("base_url", sa.String(500), nullable=False),
            sa.Column("username", sa.String(200), nullable=False),
            sa.Column("secret", sa.String(1024), nullable=True),
            sa.Column("kiwi_product_id", sa.Integer(), nullable=True),
            sa.Column("verify_ssl", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("status", sa.String(32), nullable=False, server_default="unconfigured"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("project_id", name="uq_kiwi_connections_project"),
        )
    op.create_index("ix_kiwi_connections_project_id", "kiwi_connections", ["project_id"], if_not_exists=True)

    if "kiwi_sync_jobs" not in existing:
        op.create_table(
            "kiwi_sync_jobs",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("connection_id", UUID(as_uuid=False), sa.ForeignKey("kiwi_connections.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("mode", sa.String(16), nullable=False, server_default="import"),
            sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
            sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("totals", JSONB, nullable=False, server_default="{}"),
            sa.Column("rq_job_id", sa.String(64), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
    op.create_index("ix_kiwi_sync_jobs_connection_id", "kiwi_sync_jobs", ["connection_id"], if_not_exists=True)
    op.create_index("ix_kiwi_sync_jobs_project_id", "kiwi_sync_jobs", ["project_id"], if_not_exists=True)
    op.create_index("ix_kiwi_sync_jobs_project_created", "kiwi_sync_jobs", ["project_id", "created_at"], if_not_exists=True)

    if "kiwi_id_maps" not in existing:
        op.create_table(
            "kiwi_id_maps",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("connection_id", UUID(as_uuid=False), sa.ForeignKey("kiwi_connections.id", ondelete="CASCADE"), nullable=False),
            sa.Column("entity_type", sa.String(32), nullable=False),
            sa.Column("external_id", sa.String(64), nullable=False),
            sa.Column("internal_id", UUID(as_uuid=False), nullable=False),
            sa.Column("fingerprint", sa.String(64), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("connection_id", "entity_type", "external_id", name="uq_kiwi_id_maps_conn_type_ext"),
        )
    op.create_index("ix_kiwi_id_maps_connection_id", "kiwi_id_maps", ["connection_id"], if_not_exists=True)
    op.create_index("ix_kiwi_id_maps_internal", "kiwi_id_maps", ["entity_type", "internal_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("kiwi_id_maps")
    op.drop_table("kiwi_sync_jobs")
    op.drop_table("kiwi_connections")
