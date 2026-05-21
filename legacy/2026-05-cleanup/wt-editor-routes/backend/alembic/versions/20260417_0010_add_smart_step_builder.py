"""Smart Step Builder: step_phrases, excel_uploads, step_parameters tabloları
   + manual_test_steps.action_template sütunu (engine SQLite ayrıca yönetiliyor)

Revision ID: 20260417_0010
Revises: 20260417_0009
Create Date: 2026-04-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260417_0010"
down_revision = "project_base_url_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. tspm_step_phrases ─────────────────────────────────────────────
    op.create_table(
        "tspm_step_phrases",
        sa.Column("id",         UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False),
                  sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text",       sa.String(500), nullable=False),
        sa.Column("category",   sa.String(16),  nullable=False),          # given|when|then|action
        sa.Column("use_count",  sa.Integer, server_default="0", nullable=False),
        sa.Column("source",     sa.String(32), server_default="seed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_step_phrases_project_category",
                    "tspm_step_phrases", ["project_id", "category"])
    op.create_index("ix_step_phrases_use_count",
                    "tspm_step_phrases", ["use_count"])

    # ── 2. tspm_excel_uploads ────────────────────────────────────────────
    op.create_table(
        "tspm_excel_uploads",
        sa.Column("id",          UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id",  UUID(as_uuid=False),
                  sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename",    sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(512), nullable=False),
        sa.Column("columns",     JSONB, nullable=True),           # [{"key":"A","label":"isim"}]
        sa.Column("row_count",   sa.Integer, server_default="0", nullable=False),
        sa.Column("file_size",   sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_excel_uploads_project",
                    "tspm_excel_uploads", ["project_id"])

    # ── 3. tspm_step_parameters ──────────────────────────────────────────
    op.create_table(
        "tspm_step_parameters",
        sa.Column("id",               UUID(as_uuid=False), primary_key=True),
        sa.Column("step_id",          sa.String(100), nullable=False),
        sa.Column("step_type",        sa.String(32),  nullable=False),   # manual_step|scenario_step
        sa.Column("project_id",       UUID(as_uuid=False),
                  sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word",             sa.String(200), nullable=False),
        sa.Column("position",         sa.Integer, server_default="0", nullable=False),
        sa.Column("source_type",      sa.String(16), server_default="static", nullable=False),
        sa.Column("random_type",      sa.String(32),  nullable=True),
        sa.Column("excel_upload_id",  UUID(as_uuid=False),
                  sa.ForeignKey("tspm_excel_uploads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("excel_column",     sa.String(100), nullable=True),
        sa.Column("excel_row_index",  sa.Integer, server_default="0", nullable=False),
        sa.Column("test_data_set_id", UUID(as_uuid=False),
                  sa.ForeignKey("tspm_test_data_sets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("test_data_field",  sa.String(200), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_step_parameters_step",
                    "tspm_step_parameters", ["step_id", "step_type"])
    op.create_index("ix_step_parameters_project",
                    "tspm_step_parameters", ["project_id"])

    # ── 4. tspm_scenarios → step_template sütunu ─────────────────────────
    # Senaryolarda adım metni "step_text" alanında tutuluyor.
    # step_template = parametreli versiyon "[url] adresine gidilir"
    # NULL ise parametre yok, orijinal step_text kullanılır.
    op.add_column(
        "tspm_scenarios",
        sa.Column("step_templates", JSONB, nullable=True,
                  comment="Senaryo adımlarının parametreli template versiyonları {step_index: template}"),
    )


def downgrade() -> None:
    op.drop_column("tspm_scenarios", "step_templates")
    op.drop_index("ix_step_parameters_project", "tspm_step_parameters")
    op.drop_index("ix_step_parameters_step", "tspm_step_parameters")
    op.drop_table("tspm_step_parameters")
    op.drop_index("ix_excel_uploads_project", "tspm_excel_uploads")
    op.drop_table("tspm_excel_uploads")
    op.drop_index("ix_step_phrases_use_count", "tspm_step_phrases")
    op.drop_index("ix_step_phrases_project_category", "tspm_step_phrases")
    op.drop_table("tspm_step_phrases")
