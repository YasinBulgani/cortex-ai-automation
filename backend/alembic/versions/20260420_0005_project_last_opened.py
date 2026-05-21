"""tspm_projects.last_opened_at — son açılma zamanı (ana sayfa "Son Proje" kartı için)

Revision ID: project_last_opened_0001
Revises: scenario_quality_llm_0001

Bağlam:
    Ana sayfadaki "Son Açılan Proje" kartı bugüne kadar yalnızca tarayıcı
    ``localStorage["bgts_active_project"]`` ile çalışıyordu. Bu, farklı cihaz /
    sekme / oturum yenilemesinden sonra kaybolan, doğrulanamayan bir kaynak.

    Bu migration ``tspm_projects.last_opened_at`` (nullable timestamptz) alanı
    ekler. Backend yeni ``POST /projects/{id}/touch`` uç noktası üzerinden
    kullanıcı projeye girdiğinde günceller; liste çıkışında bu alana göre
    sıralama yapılabilir.

Geriye uyumluluk:
    NULL kabul eder; mevcut kayıtlar güncelleme isteği gelene kadar NULL
    kalır, "son açılan" listesinde de arkada konumlanır.
"""
from alembic import op


revision = "project_last_opened_0001"
down_revision = "scenario_quality_llm_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tspm_projects
            ADD COLUMN IF NOT EXISTS last_opened_at TIMESTAMP WITH TIME ZONE
        """
    )
    # Ana sayfa sorgusu: WHERE archived = FALSE ORDER BY last_opened_at DESC NULLS LAST
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tspm_projects_last_opened_at
            ON tspm_projects (last_opened_at DESC NULLS LAST)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tspm_projects_last_opened_at")
    op.execute("ALTER TABLE tspm_projects DROP COLUMN IF EXISTS last_opened_at")
