"""add_web_vitals_samples

Creates web_vitals_samples — raw Core Web Vitals measurements feeding
GET /products/web/perf-metrics (page-level p75 aggregation). Populated by a
RUM beacon or synthetic perf runs; the endpoint falls back to demo data when
the table is empty. Project is optional (tenant-wide RUM allowed), no RLS.

Idempotent (CREATE TABLE/INDEX IF NOT EXISTS) so fresh builds and re-runs are
safe — consistent with the rest of the 2026-06-08 migration batch.

Revision ID: 20260608_0007
Revises: 20260608_0006
Create Date: 2026-06-08 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = '20260608_0007'
down_revision: Union[str, None] = '20260608_0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS web_vitals_samples (
            id UUID PRIMARY KEY,
            project_id UUID,
            page_url VARCHAR(1000) NOT NULL,
            page_label VARCHAR(200),
            lcp DOUBLE PRECISION,
            inp DOUBLE PRECISION,
            cls DOUBLE PRECISION,
            fcp DOUBLE PRECISION,
            tbt DOUBLE PRECISION,
            sampled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_web_vitals_samples_page_time "
        "ON web_vitals_samples (page_url, sampled_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_web_vitals_samples_project "
        "ON web_vitals_samples (project_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_web_vitals_samples_sampled_at "
        "ON web_vitals_samples (sampled_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS web_vitals_samples")
