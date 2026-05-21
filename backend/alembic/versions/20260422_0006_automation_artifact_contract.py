"""tspm_automation_artifacts — target/provenance/validation contract

Revision ID: automation_artifact_contract_0001
Revises: project_last_opened_0001

Bağlam:
    Visium ürünleşme planında otomasyon çıktıları yalnızca "dosya üretildi"
    seviyesinde kalmamalı; hangi hedefe ait olduğu (Playwright / MaviYaka),
    gerçek mi yoksa yardımcı/simulated mi olduğu ve doğrulama durumu birlikte
    taşınmalı.

Bu migration:
    * ``target``             — shared | playwright | maviyaka
    * ``provenance``         — real | simulated | fallback | stub
    * ``validation_status``  — pending | validated | failed | not_applicable
    * ``generated_by``       — ai_gateway / provider adı vb.

Geriye uyumluluk:
    Mevcut kayıtlar ``shared + real + pending`` ile korunur.
"""

from alembic import op


revision = "automation_artifact_contract_0001"
down_revision = "project_last_opened_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alembic'in varsayılan version_num kolon uzunluğu 32 karakterdir. Bu
    # revision ID daha uzun olduğu için migration sonunda version update'i
    # kesilmesin diye kolonu zincirin bu noktasında genişletiyoruz.
    op.execute(
        """
        ALTER TABLE IF EXISTS alembic_version
            ALTER COLUMN version_num TYPE VARCHAR(255)
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_automation_artifacts
            ADD COLUMN IF NOT EXISTS target VARCHAR(32) NOT NULL DEFAULT 'shared'
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_automation_artifacts
            ADD COLUMN IF NOT EXISTS provenance VARCHAR(32) NOT NULL DEFAULT 'real'
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_automation_artifacts
            ADD COLUMN IF NOT EXISTS validation_status VARCHAR(32) NOT NULL DEFAULT 'pending'
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_automation_artifacts
            ADD COLUMN IF NOT EXISTS generated_by VARCHAR(64)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tspm_automation_artifacts_target
            ON tspm_automation_artifacts (target)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tspm_automation_artifacts_provenance
            ON tspm_automation_artifacts (provenance)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tspm_automation_artifacts_provenance")
    op.execute("DROP INDEX IF EXISTS idx_tspm_automation_artifacts_target")
    op.execute("ALTER TABLE tspm_automation_artifacts DROP COLUMN IF EXISTS generated_by")
    op.execute("ALTER TABLE tspm_automation_artifacts DROP COLUMN IF EXISTS validation_status")
    op.execute("ALTER TABLE tspm_automation_artifacts DROP COLUMN IF EXISTS provenance")
    op.execute("ALTER TABLE tspm_automation_artifacts DROP COLUMN IF EXISTS target")
