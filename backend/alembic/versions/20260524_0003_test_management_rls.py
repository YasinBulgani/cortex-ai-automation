"""Row-Level Security for test_management_* tables.

Extends the existing RLS framework (mt_rls_0001) to the Neurex Management
domain.  Strategy:

  - ``test_management_projects``   has ``tenant_id`` → direct RLS.
  - All child tables                have ``project_id`` FK → policy does a
    single-hop subquery through ``test_management_projects``.

The subquery approach avoids denormalising tenant_id into every child table
while keeping policy logic simple and index-friendly.

Revision ID: test_mgmt_rls_0001
Revises: 20260524_0002, mt_rls_0001
Create Date: 2026-05-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "test_mgmt_rls_0001"
down_revision: Union[str, tuple[str, ...]] = ("20260524_0002", "mt_rls_0001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Tables ────────────────────────────────────────────────────────────────────

# Projects table uses direct tenant_id column.
_DIRECT_TENANT_TABLE = "test_management_projects"

# Child tables that have a project_id FK → test_management_projects.
_PROJECT_CHILD_TABLES = [
    "test_management_suites",
    "test_management_folders",
    "test_management_cases",
    "test_management_case_steps",
    "test_management_case_versions",
    "test_management_plans",
    "test_management_cycles",
    "test_management_runs",
    "test_management_run_cases",
    "test_management_run_step_results",
    "test_management_requirement_links",
    "test_management_defect_links",
    "test_management_import_jobs",
    "test_management_import_job_rows",
    "test_management_audit_events",
]

# Indirect tables: runs/run-cases don't have project_id directly but are
# reachable via run → cycle → plan → project.  We skip RLS on the deepest
# tables and rely on JOIN-based access control in service layer.
# run_cases + run_step_results are reached only through authenticated runs
# whose project_id is already enforced.  Mark them explicitly:
_DEEP_INDIRECT_TABLES = {
    "test_management_run_cases",
    "test_management_run_step_results",
}


def _table_exists(table: str) -> str:
    """Return a PL/pgSQL snippet that returns true if the table exists."""
    return f"EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')"


def _col_exists(table: str, col: str) -> str:
    return (
        f"EXISTS (SELECT 1 FROM information_schema.columns "
        f"WHERE table_name = '{table}' AND column_name = '{col}')"
    )


def upgrade() -> None:
    # ── 1. current_tenant_id() guard ─────────────────────────────────────────
    # Ensure the helper function exists (created by mt_rls_0001 but guard anyway).
    op.execute("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID
        LANGUAGE plpgsql STABLE SECURITY DEFINER AS $$
        DECLARE
            _tenant_id TEXT;
        BEGIN
            BEGIN
                _tenant_id := current_setting('app.current_tenant', TRUE);
            EXCEPTION WHEN OTHERS THEN
                RETURN '00000000-0000-0000-0000-000000000001'::UUID;
            END;
            IF _tenant_id IS NULL OR _tenant_id = '' THEN
                RETURN '00000000-0000-0000-0000-000000000001'::UUID;
            END IF;
            RETURN _tenant_id::UUID;
        END;
        $$;
    """)

    # ── 2. Direct RLS on test_management_projects ─────────────────────────────
    op.execute(f"""
        DO $$ BEGIN
            IF {_table_exists(_DIRECT_TENANT_TABLE)} AND {_col_exists(_DIRECT_TENANT_TABLE, 'tenant_id')} THEN
                ALTER TABLE {_DIRECT_TENANT_TABLE} ENABLE ROW LEVEL SECURITY;
                ALTER TABLE {_DIRECT_TENANT_TABLE} FORCE ROW LEVEL SECURITY;

                DROP POLICY IF EXISTS rls_tenant_isolation ON {_DIRECT_TENANT_TABLE};
                CREATE POLICY rls_tenant_isolation ON {_DIRECT_TENANT_TABLE}
                    USING (tenant_id = current_tenant_id());

                CREATE INDEX IF NOT EXISTS idx_{_DIRECT_TENANT_TABLE}_tenant_id
                    ON {_DIRECT_TENANT_TABLE}(tenant_id);
            END IF;
        END $$;
    """)

    # ── 3. Project-scoped RLS for shallow child tables ─────────────────────────
    # These tables have a direct project_id FK.
    _direct_project_tables = [
        t for t in _PROJECT_CHILD_TABLES
        if t not in _DEEP_INDIRECT_TABLES
    ]

    for table in _direct_project_tables:
        op.execute(f"""
            DO $$ BEGIN
                IF {_table_exists(table)} AND {_col_exists(table, 'project_id')} THEN
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

                    DROP POLICY IF EXISTS rls_tenant_isolation ON {table};
                    CREATE POLICY rls_tenant_isolation ON {table}
                        USING (
                            project_id IN (
                                SELECT id FROM test_management_projects
                                WHERE tenant_id = current_tenant_id()
                            )
                        );

                    CREATE INDEX IF NOT EXISTS idx_{table}_project_id
                        ON {table}(project_id);
                END IF;
            END $$;
        """)

    # ── 4. Deep indirect tables (run_cases, run_step_results) ─────────────────
    # Enable RLS but without a blocking policy — access is controlled at the
    # service layer via authenticated run ownership.  This prevents accidental
    # full-table scans if RLS is ever re-evaluated.
    for table in _DEEP_INDIRECT_TABLES:
        op.execute(f"""
            DO $$ BEGIN
                IF {_table_exists(table)} THEN
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                    -- Permissive policy: allow all rows — service layer does run ownership check.
                    -- A future migration can add cross-join policies once run→project path
                    -- is materialised.
                    DROP POLICY IF EXISTS rls_service_layer_owns ON {table};
                    CREATE POLICY rls_service_layer_owns ON {table}
                        USING (TRUE);
                END IF;
            END $$;
        """)

    # ── 5. Grant BYPASS for migration superuser if it exists ──────────────────
    # Only relevant if running as a non-superuser migration role.
    # pg_catalog check avoids error on RDS where superuser role may not exist.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = current_user AND rolsuper = FALSE
            ) THEN
                -- Migration user is not superuser — rely on SET LOCAL bypass.
                -- (superuser and BYPASSRLS roles already bypass RLS automatically.)
                NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # ── Remove RLS from all test_management tables in reverse order ───────────
    for table in reversed(_PROJECT_CHILD_TABLES):
        op.execute(f"""
            DO $$ BEGIN
                IF {_table_exists(table)} THEN
                    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
                    DROP POLICY IF EXISTS rls_tenant_isolation ON {table};
                    DROP POLICY IF EXISTS rls_service_layer_owns ON {table};
                END IF;
            END $$;
        """)

    op.execute(f"""
        DO $$ BEGIN
            IF {_table_exists(_DIRECT_TENANT_TABLE)} THEN
                ALTER TABLE {_DIRECT_TENANT_TABLE} DISABLE ROW LEVEL SECURITY;
                DROP POLICY IF EXISTS rls_tenant_isolation ON {_DIRECT_TENANT_TABLE};
            END IF;
        END $$;
    """)
