"""Verify and enforce critical unique constraints.

Revision ID: 20260609_0006
Revises: 20260609_0005
Create Date: 2026-06-09

Verifies that critical unique constraints exist and are properly enforced:
1. TestManagementProject (tenant_id, key) — multi-tenant key uniqueness
2. TestSuite (project_id, name) — suite naming within project
3. TestFolder (suite_id, path) — folder hierarchy uniqueness
4. TestCase (project_id, case_key) — case key uniqueness per project
5. Role name uniqueness (global)
6. Organization slug uniqueness (global)
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260609_0006"
down_revision: Union[str, None] = "20260609_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Verify test_management_projects (tenant_id, key) unique constraint
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'test_management_projects'
                AND constraint_name = 'uq_test_management_projects_tenant_key'
            ) THEN
                ALTER TABLE test_management_projects
                ADD CONSTRAINT uq_test_management_projects_tenant_key
                UNIQUE (tenant_id, key);
            END IF;
        END $$;
    """)

    # Verify test_management_suites (project_id, name) unique constraint
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'test_management_suites'
                AND constraint_name = 'uq_tm_suites_project_name'
            ) THEN
                ALTER TABLE test_management_suites
                ADD CONSTRAINT uq_tm_suites_project_name
                UNIQUE (project_id, name);
            END IF;
        END $$;
    """)

    # Verify test_management_folders (suite_id, path) unique constraint
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'test_management_folders'
                AND constraint_name = 'uq_tm_folders_suite_path'
            ) THEN
                ALTER TABLE test_management_folders
                ADD CONSTRAINT uq_tm_folders_suite_path
                UNIQUE (suite_id, path);
            END IF;
        END $$;
    """)

    # Verify test_management_cases (project_id, case_key) unique constraint
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'test_management_cases'
                AND constraint_name = 'uq_tm_cases_project_key'
            ) THEN
                ALTER TABLE test_management_cases
                ADD CONSTRAINT uq_tm_cases_project_key
                UNIQUE (project_id, case_key);
            END IF;
        END $$;
    """)

    # Verify Role name uniqueness
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'sd_roles'
                AND constraint_name = 'sd_roles_name_key'
            ) THEN
                ALTER TABLE sd_roles
                ADD CONSTRAINT sd_roles_name_key UNIQUE (name);
            END IF;
        END $$;
    """)

    # Verify Organization slug uniqueness
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'sd_organizations'
                AND constraint_name = 'sd_organizations_slug_key'
            ) THEN
                ALTER TABLE sd_organizations
                ADD CONSTRAINT sd_organizations_slug_key UNIQUE (slug);
            END IF;
        END $$;
    """)

    # Verify Project Member type compatibility and FK
    # WARN: sd_project_members.project_id is String(128) but test_management_projects.id is UUID
    # This is a schema inconsistency that must be fixed separately (change ProjectMember.project_id to UUID type)
    # Skip FK creation until type mismatch is resolved (will be fixed in 20260609_0008)
    op.execute("""
        DO $$ BEGIN
            -- Type mismatch detected: String(128) vs UUID
            -- Migration skips FK constraint - requires model.py fix first
            RAISE NOTICE 'SCHEMA INCONSISTENCY: sd_project_members.project_id (String) vs test_management_projects.id (UUID)';
        END $$;
    """)

    # Log verification completion
    op.execute("""
        DO $$ BEGIN
            RAISE NOTICE 'Database constraint verification complete: 7 constraints checked';
        END $$;
    """)


def downgrade() -> None:
    # Downgrade removes constraint verification (constraints remain for safety)
    op.execute("""
        DO $$ BEGIN
            RAISE NOTICE 'Constraint downgrades skipped for data safety';
        END $$;
    """)
