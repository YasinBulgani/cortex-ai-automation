"""TspmExecution.simulated — engine-down simülasyon koşumlarını işaretle.

Revision ID: tspm_execution_simulated_0001
Revises: llm_correlation_0001

Bağlam:
    Engine (Flask) erişilemediğinde backend `_simulate_run` deterministik bir
    sonuç üretir (scenario başlığına göre hash tabanlı pass/fail). Bu yol
    daha önce SSE `summary` event'inde bildiriliyordu ancak execution kaydı
    DB'den tekrar okunduğunda (execution listesi, project dashboard,
    report/summary) simülasyon/gerçek ayrımı kayboluyordu — UI "yeşil çubuk"
    gösterip kullanıcıyı yanıltıyordu.

    Bu migration `tspm_executions.simulated` bayrağını kalıcı hale getirir.
    Geçmişe dönük kayıtlar default FALSE kalır (geriye uyumlu).
"""

from alembic import op


revision = "tspm_execution_simulated_0001"
down_revision = "llm_correlation_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS: lokal dev ortamlarında ya da paralel migration'larda
    # sessiz geçmek için. Dönüş tipi kısa: BOOLEAN + server_default false.
    op.execute(
        """
        ALTER TABLE tspm_executions
            ADD COLUMN IF NOT EXISTS simulated BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    # Sorgu optimizasyonu — dashboard "gerçek koşumlar" filtrelemesi için.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tspm_executions_simulated
            ON tspm_executions (simulated)
            WHERE simulated = TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tspm_executions_simulated")
    op.execute("ALTER TABLE tspm_executions DROP COLUMN IF EXISTS simulated")
