"""Audit hash chain — gerçek tabloya bağlama + head merge (Dalga 0 · BDDK)

Revision ID: audit_chain_bind_0001
Revises: few_shot_bank_0001, tspm_execution_simulated_0001, synthetic_platform_0001

Bağlam:
    1) 20260419_0005 migration'u ``audit_events`` tablosuna hash/prev_hash/
       seq/tenant_id ekliyordu ANCAK o tablo hiçbir yerde CREATE edilmiyor.
       Gerçek tablo ORM modelinde ``sd_audit_events``
       (``app.infra.models.AuditEvent``). Bu yüzden ``audit/chain.py``
       append_event'ı çağrılınca tablosuz kalıyor ve ``audit/service.py``
       log_audit'i tamper-evident değil.
    2) Aynı anda 3 branch head mevcut: few_shot_bank, tspm_execution_simulated,
       synthetic_platform. Bunlar önce bir merge'de birleşmeli.

Düzeltme:
    * 3 head'i merge et
    * Hash-chain kolonlarını ``sd_audit_events`` üstüne ekle (idempotent)
    * chain.py bu migration sonrası ``sd_audit_events`` üstünde birleşir

Backfill:
    Mevcut satırlar için kolonlar NULL kalır; verify_chain "legacy" olarak
    atlar (geriye dönük uyum). Yeni kayıtlar monotonik seq'le zincire girer.
"""
from alembic import op


revision = "audit_chain_bind_0001"
# Birden fazla down_revision → Alembic merge migration
down_revision = (
    "few_shot_bank_0001",
    "tspm_execution_simulated_0001",
    "synthetic_platform_0001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Hash-chain kolonları ``sd_audit_events`` üzerinde ───────────────
    op.execute(
        """
        ALTER TABLE sd_audit_events
        ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64)
        """
    )
    op.execute(
        """
        ALTER TABLE sd_audit_events
        ADD COLUMN IF NOT EXISTS hash VARCHAR(64)
        """
    )
    op.execute(
        """
        ALTER TABLE sd_audit_events
        ADD COLUMN IF NOT EXISTS seq BIGINT
        """
    )
    op.execute(
        """
        ALTER TABLE sd_audit_events
        ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sd_audit_tenant_seq
        ON sd_audit_events(tenant_id, seq DESC)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_sd_audit_tenant_seq_unique
        ON sd_audit_events(tenant_id, seq) WHERE seq IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_sd_audit_tenant_seq_unique")
    op.execute("DROP INDEX IF EXISTS idx_sd_audit_tenant_seq")
    op.execute("ALTER TABLE sd_audit_events DROP COLUMN IF EXISTS tenant_id")
    op.execute("ALTER TABLE sd_audit_events DROP COLUMN IF EXISTS seq")
    op.execute("ALTER TABLE sd_audit_events DROP COLUMN IF EXISTS hash")
    op.execute("ALTER TABLE sd_audit_events DROP COLUMN IF EXISTS prev_hash")
