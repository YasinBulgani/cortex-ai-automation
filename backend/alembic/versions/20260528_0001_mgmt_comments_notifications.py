"""Add management threaded comments and notifications tables.

Revision ID: mgmt_comments_notif_0001
Revises: perf_indexes_v2_0001
Create Date: 2026-05-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "mgmt_comments_notif_0001"
down_revision: str = "perf_indexes_v2_0001"
branch_labels = None
depends_on = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())

    if "mgmt_comments" not in existing:
        op.create_table(
            "mgmt_comments",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, server_default=DEFAULT_TENANT_ID),
            sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=True),
            sa.Column("entity_type", sa.String(64), nullable=False),
            sa.Column("entity_id", UUID(as_uuid=False), nullable=False),
            sa.Column("author_id", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("parent_id", UUID(as_uuid=False), sa.ForeignKey("mgmt_comments.id", ondelete="CASCADE"), nullable=True),
            sa.Column("body_md", sa.Text(), nullable=False),
            sa.Column("mentions", JSONB(), nullable=False, server_default="[]"),
            sa.Column("reactions", JSONB(), nullable=False, server_default="{}"),
            sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    op.create_index("ix_mgmt_comments_tenant_id", "mgmt_comments", ["tenant_id"], if_not_exists=True)
    op.create_index("ix_mgmt_comments_project_id", "mgmt_comments", ["project_id"], if_not_exists=True)
    op.create_index("ix_mgmt_comments_entity", "mgmt_comments", ["entity_type", "entity_id"], if_not_exists=True)
    op.create_index("ix_mgmt_comments_tenant_created", "mgmt_comments", ["tenant_id", "created_at"], if_not_exists=True)
    op.create_index("ix_mgmt_comments_parent", "mgmt_comments", ["parent_id"], if_not_exists=True)

    if "mgmt_notifications" not in existing:
        op.create_table(
            "mgmt_notifications",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False, server_default=DEFAULT_TENANT_ID),
            sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=True),
            sa.Column("kind", sa.String(64), nullable=False),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("link_path", sa.String(512), nullable=True),
            sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
            sa.Column("source_trace", JSONB(), nullable=False, server_default="{}"),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    op.create_index("ix_mgmt_notif_tenant_id", "mgmt_notifications", ["tenant_id"], if_not_exists=True)
    op.create_index("ix_mgmt_notif_user_id", "mgmt_notifications", ["user_id"], if_not_exists=True)
    op.create_index("ix_mgmt_notif_project_id", "mgmt_notifications", ["project_id"], if_not_exists=True)
    op.create_index("ix_mgmt_notif_user_unread", "mgmt_notifications", ["user_id", "read_at"], if_not_exists=True)
    op.create_index("ix_mgmt_notif_created", "mgmt_notifications", ["created_at"], if_not_exists=True)
    op.create_index("ix_mgmt_notif_user_archived", "mgmt_notifications", ["user_id", "archived_at"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_mgmt_notif_user_archived", table_name="mgmt_notifications")
    op.drop_index("ix_mgmt_notif_created", table_name="mgmt_notifications")
    op.drop_index("ix_mgmt_notif_user_unread", table_name="mgmt_notifications")
    op.drop_index("ix_mgmt_notif_project_id", table_name="mgmt_notifications")
    op.drop_index("ix_mgmt_notif_user_id", table_name="mgmt_notifications")
    op.drop_index("ix_mgmt_notif_tenant_id", table_name="mgmt_notifications")
    op.drop_table("mgmt_notifications")
    op.drop_index("ix_mgmt_comments_parent", table_name="mgmt_comments")
    op.drop_index("ix_mgmt_comments_tenant_created", table_name="mgmt_comments")
    op.drop_index("ix_mgmt_comments_entity", table_name="mgmt_comments")
    op.drop_index("ix_mgmt_comments_project_id", table_name="mgmt_comments")
    op.drop_index("ix_mgmt_comments_tenant_id", table_name="mgmt_comments")
    op.drop_table("mgmt_comments")
