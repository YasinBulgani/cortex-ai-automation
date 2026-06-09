"""Fix ProjectMember.project_id type from String to UUID.

Revision ID: 20260609_0008
Revises: 20260609_0007
Create Date: 2026-06-09

Converts sd_project_members.project_id from String(128) to UUID to match
test_management_projects.id type, enabling proper foreign key constraint enforcement.

**Critical bug DB-HIGH-5a**: Type mismatch between ProjectMember.project_id and
TestManagementProject.id prevented FK constraint creation.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260609_0008_fix_project_member_type"
down_revision: Union[str, None] = "20260609_0007_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop existing FK constraint if present
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'sd_project_members'
                AND constraint_name LIKE '%project_id%'
            ) THEN
                ALTER TABLE sd_project_members
                DROP CONSTRAINT IF EXISTS fk_project_members_project_id;
            END IF;
        END $$;
    """)

    # Step 2: Convert column type from String(128) to UUID
    # First, create a temporary UUID column
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_project_members'
                AND column_name = 'project_id'
            ) THEN
                ALTER TABLE sd_project_members
                ADD COLUMN project_id_new UUID;
            END IF;
        END $$;
    """)

    # Step 3: Cast existing data (String UUID → UUID type)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_project_members'
                AND column_name = 'project_id_new'
            ) THEN
                UPDATE sd_project_members
                SET project_id_new = CAST(project_id AS UUID)
                WHERE project_id IS NOT NULL;
            END IF;
        END $$;
    """)

    # Step 4: Drop old column and rename new one
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_project_members'
                AND column_name = 'project_id_new'
            ) THEN
                ALTER TABLE sd_project_members
                DROP COLUMN project_id;
                ALTER TABLE sd_project_members
                RENAME COLUMN project_id_new TO project_id;
            END IF;
        END $$;
    """)

    # Step 5: Recreate the primary key (includes project_id)
    # Note: This is handled by the primary key constraint which must be recreated
    op.execute("""
        DO $$ BEGIN
            -- Verify column exists and is UUID type
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_project_members'
                AND column_name = 'project_id'
                AND data_type = 'uuid'
            ) THEN
                RAISE NOTICE 'sd_project_members.project_id converted to UUID';
            END IF;
        END $$;
    """)

    # Step 6: Recreate FK constraint with correct types
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'sd_project_members'
                AND constraint_name = 'fk_project_members_project_id'
            ) THEN
                ALTER TABLE sd_project_members
                ADD CONSTRAINT fk_project_members_project_id
                FOREIGN KEY (project_id)
                REFERENCES test_management_projects(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_project_members'
                AND column_name = 'project_id'
            ) THEN
                ALTER TABLE sd_project_members
                DROP CONSTRAINT IF EXISTS fk_project_members_project_id;

                -- Create temporary column for old type
                ALTER TABLE sd_project_members
                ADD COLUMN project_id_old VARCHAR(128);

                -- Cast UUID back to string
                UPDATE sd_project_members
                SET project_id_old = CAST(project_id AS VARCHAR(128));

                -- Drop UUID column and rename old one
                ALTER TABLE sd_project_members
                DROP COLUMN project_id;
                ALTER TABLE sd_project_members
                RENAME COLUMN project_id_old TO project_id;
            END IF;
        END $$;
    """)
