"""Add critical composite indexes for query performance.

Revision ID: 20260609_0005
Revises: 20260609_0004_5
Create Date: 2026-06-09

Adds composite indexes to improve query performance for:
1. Test case filtering by project + status (frequent dashboard queries)
2. Test case archival filtering (project + archived flag)
3. Audit log tenant + entity + time queries
4. Project member project_id lookups (new FK constraint)
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260609_0005"
down_revision: Union[str, None] = "20260609_0004_5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index for case status queries (already in model via __table_args__)
    # Ensure it exists
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tm_cases_project_status
            ON test_management_cases(project_id, status)
            WHERE status != 'deleted';
    """)

    # Composite index for archived cases (already in model)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tm_cases_project_archived
            ON test_management_cases(project_id, archived)
            WHERE archived = false;
    """)

    # Index for project member lookups (now that FK is enforced)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_project_members_project_id
            ON sd_project_members(project_id)
            WHERE project_id IS NOT NULL;
    """)

    # Composite index for case dependencies (if table exists)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'test_management_case_dependencies'
            ) THEN
                CREATE INDEX IF NOT EXISTS ix_tm_case_deps_case_depends
                    ON test_management_case_dependencies(case_id, depends_on_id);
            END IF;
        END $$;
    """)

    # Audit log composite index for efficient tenant filtering
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'sd_audit_log'
            ) THEN
                CREATE INDEX IF NOT EXISTS ix_audit_log_tenant_type_time
                    ON sd_audit_log(tenant_id, entity_type, created_at DESC)
                    WHERE tenant_id IS NOT NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tm_cases_project_status;")
    op.execute("DROP INDEX IF EXISTS ix_tm_cases_project_archived;")
    op.execute("DROP INDEX IF EXISTS ix_project_members_project_id;")
    op.execute("DROP INDEX IF EXISTS ix_tm_case_deps_case_depends;")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_tenant_type_time;")
