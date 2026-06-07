"""add_remaining_columns_qa_session

QA oturumu sırasında doğrudan ALTER TABLE ile eklenen sütunları
migration zincirinde resmi hale getirir.

Revision ID: 20260606_0004
Revises: 20260606_0003
Create Date: 2026-06-06 06:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from alembic import op

revision: str = "20260606_0004"
down_revision: Union[str, None] = "20260606_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(conn, table: str, col: str) -> bool:
    res = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": col},
    )
    return res.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    res = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=:t"
        ),
        {"t": table},
    )
    return res.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── test_management_projects ───────────────────────────────────────────
    if not _col_exists(conn, "test_management_projects", "settings_data"):
        op.add_column("test_management_projects", sa.Column("settings_data", sa.JSON(), nullable=True))

    # ── test_management_requirements ───────────────────────────────────────
    req_cols = {
        "description": sa.Text(),
        "priority": sa.String(32),
        "status": sa.String(32),
        "url": sa.String(1000),
        "source_updated_at": sa.DateTime(timezone=True),
        "owner_id": PG_UUID(as_uuid=False),
        "version_no": sa.Integer(),
        "acceptance_criteria": JSONB(),
        "tags": JSONB(),
        "updated_at": sa.DateTime(timezone=True),
        "external_source": sa.String(32),
        "external_key": sa.String(128),
    }
    for col_name, col_type in req_cols.items():
        if not _col_exists(conn, "test_management_requirements", col_name):
            op.add_column("test_management_requirements", sa.Column(col_name, col_type, nullable=True))

    # ── test_management_cycles: project_id VARCHAR → UUID ─────────────────
    res = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='test_management_cycles' AND column_name='project_id'"
        )
    )
    row = res.fetchone()
    if row and row[0] == "character varying":
        conn.execute(sa.text(
            "ALTER TABLE test_management_cycles "
            "ALTER COLUMN project_id TYPE uuid USING project_id::uuid"
        ))

    # ── cicd_jenkins_connections ───────────────────────────────────────────
    jenkins_cols = {
        "owner_user_id": sa.String(64),
        "last_status": sa.String(32),
        "last_tested_at": sa.DateTime(timezone=True),
        "last_error": sa.Text(),
    }
    for col_name, col_type in jenkins_cols.items():
        if not _col_exists(conn, "cicd_jenkins_connections", col_name):
            op.add_column("cicd_jenkins_connections", sa.Column(col_name, col_type, nullable=True))

    # ── sd_apitest_cases quarantine columns ───────────────────────────────
    apitest_cols = {
        "quarantined": sa.Boolean(),
        "quarantined_at": sa.DateTime(timezone=True),
        "quarantine_reason": sa.Text(),
        "is_flaky": sa.Boolean(),
        "flaky_count": sa.Integer(),
        "flaky_rate": sa.Float(),
    }
    if _table_exists(conn, "sd_apitest_cases"):
        for col_name, col_type in apitest_cols.items():
            if not _col_exists(conn, "sd_apitest_cases", col_name):
                op.add_column("sd_apitest_cases", sa.Column(col_name, col_type, nullable=True))

    # ── sd_apitest_* tables (CREATE IF NOT EXISTS) ────────────────────────
    if not _table_exists(conn, "sd_apitest_environments"):
        conn.execute(sa.text("""
        CREATE TABLE sd_apitest_environments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES tspm_projects(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            variables JSONB NOT NULL DEFAULT '{}',
            sensitive_keys JSONB NOT NULL DEFAULT '[]',
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """))


def downgrade() -> None:
    pass
