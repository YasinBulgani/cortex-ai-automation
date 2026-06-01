"""Add MFA/TOTP columns to sd_users.

Revision ID: user_mfa_totp_0001
Revises: test_mgmt_rls_0001
Create Date: 2026-05-24
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

# ── Revision identifiers ──────────────────────────────────────────────────────

revision: str = "user_mfa_totp_0001"
down_revision: Union[str, tuple[str, ...]] = "test_mgmt_rls_0001"
branch_labels = None
depends_on = None


# ── Migrations ────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # Add totp_secret column (nullable — NULL means MFA not configured)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_users' AND column_name = 'totp_secret'
            ) THEN
                ALTER TABLE sd_users ADD COLUMN totp_secret VARCHAR(64);
            END IF;
        END $$;
        """
    )

    # Add mfa_enabled column (default FALSE — not enabled until user verifies)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_users' AND column_name = 'mfa_enabled'
            ) THEN
                ALTER TABLE sd_users ADD COLUMN mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
        END $$;
        """
    )

    # Add mfa_backup_codes column (JSON array of hashed backup codes)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_users' AND column_name = 'mfa_backup_codes'
            ) THEN
                ALTER TABLE sd_users ADD COLUMN mfa_backup_codes TEXT;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE sd_users
            DROP COLUMN IF EXISTS mfa_backup_codes,
            DROP COLUMN IF EXISTS mfa_enabled,
            DROP COLUMN IF EXISTS totp_secret;
        """
    )
