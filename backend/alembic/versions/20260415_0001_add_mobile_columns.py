"""Add mobile columns to tspm_executions

tspm_executions tablosuna mobil koşum için 3 nullable kolon ekler:
  - platform     : "ios" | "android" | null
  - device_name  : cihaz görüntü adı
  - app_upload_id: engine'e yüklenen APK/IPA upload_id

Revision ID: mobile_0001
Revises: api_testing_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "mobile_0001"
down_revision = "api_testing_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tspm_executions",
        sa.Column("platform", sa.String(32), nullable=True),
    )
    op.add_column(
        "tspm_executions",
        sa.Column("device_name", sa.String(200), nullable=True),
    )
    op.add_column(
        "tspm_executions",
        sa.Column("app_upload_id", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tspm_executions", "app_upload_id")
    op.drop_column("tspm_executions", "device_name")
    op.drop_column("tspm_executions", "platform")
