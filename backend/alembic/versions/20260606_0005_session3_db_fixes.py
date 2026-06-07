"""session3_db_fixes

Oturum 3 QA sırasında doğrudan DB'ye eklenen değişiklikleri resmi hale getirir:
  - llm_traces eksik sütunlar
  - sd_organizations demo seed verisi (fixture, not migration data — sadece not)

Revision ID: 20260606_0005
Revises: 20260606_0004
Create Date: 2026-06-06 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from alembic import op

revision: str = "20260606_0005"
down_revision: Union[str, None] = "20260606_0004"
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


def upgrade() -> None:
    conn = op.get_bind()

    # ── llm_traces eksik sütunlar ──────────────────────────────────────────
    llm_cols = {
        "run_id": sa.String(36),
        "agent_name": sa.String(128),
        "provider": sa.String(64),
        "prompt_id": sa.String(64),
        "prompt_version": sa.Integer(),
        "user_id": PG_UUID(as_uuid=False),
    }
    for col_name, col_type in llm_cols.items():
        if not _col_exists(conn, "llm_traces", col_name):
            op.add_column("llm_traces", sa.Column(col_name, col_type, nullable=True))

    # ── sd_organizations: demo tenant için varsayılan org ─────────────────
    # Eğer yoksa ekle; migration idempotent
    conn.execute(sa.text("""
        INSERT INTO sd_organizations (id, name, slug, plan_code, settings, created_at)
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            'Neurex QA Organization',
            'neurex-qa',
            'professional',
            '{"features":["test_management","api_testing","ai_agents","mobile_testing"]}',
            NOW()
        )
        ON CONFLICT (id) DO NOTHING
    """))


def downgrade() -> None:
    for col in ["run_id", "agent_name", "provider", "prompt_id", "prompt_version", "user_id"]:
        try:
            op.drop_column("llm_traces", col)
        except Exception:
            pass
