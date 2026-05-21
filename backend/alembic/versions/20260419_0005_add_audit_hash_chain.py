"""Audit event hash chain — WORM + tamper-evident

Revision ID: audit_hash_chain_0001
Revises: flaky_quarantine_0001

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §5 / E3.3 (P0).

Değişiklikler:
    * audit_events.prev_hash  (nullable — ilk event için NULL)
    * audit_events.hash       (NOT NULL — SHA-256 hex)
    * audit_events.seq        (monotonik per-tenant dizin — chain order)

Backfill:
    Mevcut kayıtlar için NULL bırakılır; verify sırasında "legacy" olarak
    atlanır. Yeni kayıtlar chain içine girer. Tamamen geriye dönük hash
    hesabı migration dışı bir helper script ile yapılabilir (opsiyonel).

Indexler:
    (tenant_id, seq DESC) — chain tail lookup
    UNIQUE (tenant_id, seq)  — idempotency garantisi
"""
from alembic import op


revision = "audit_hash_chain_0001"
down_revision = "flaky_quarantine_0001"
branch_labels = None
depends_on = None


# NOT: Bu migration orijinalinde var olmayan ``audit_events`` tablosuna
# kolon eklemeye çalışıyordu (gerçek tablo ``sd_audit_events``). Takipçi
# migration ``20260420_0002_bind_audit_hash_chain.py`` (audit_chain_bind_0001)
# aynı kolonları doğru tabloya ekliyor ve 3 branch head'i merge ediyor.
# Zinciri bozmamak için bu migration'ı no-op'a indirdik; üzerine inşa edilen
# migration'lar bağımlılık zincirini doğal olarak sürdürüyor.


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
