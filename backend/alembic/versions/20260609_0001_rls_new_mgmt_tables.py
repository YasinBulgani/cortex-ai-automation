"""Row-Level Security for newer test_management tables.

Extends test_mgmt_rls_0001 to tables added after the original RLS migration that
were shipped without a tenant-isolation policy (cross-tenant leak risk):

  - test_management_shared_steps          (project_id → projects)
  - mgmt_comments                         (project_id → projects)
  - test_management_exploration_sessions  (project_id → projects)
  - mgmt_design_technique_runs            (project_id → projects)
  - test_management_case_dependencies     (case_id → cases → projects, 2-hop)

Mirrors the existing single-hop subquery strategy and is fully guarded
(_table_exists / _col_exists) so it is a safe no-op where a table/column is absent.

Revision ID: 20260609_0001
Revises: 20260608_0003
Create Date: 2026-06-09 09:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260609_0001"
down_revision: Union[str, None] = "20260608_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables with a direct project_id FK → single-hop subquery policy.
_PROJECT_TABLES = [
    "test_management_shared_steps",
    "mgmt_comments",
    "test_management_exploration_sessions",
    "mgmt_design_technique_runs",
]

# Tables reachable only via case_id → cases.project_id → projects.tenant_id.
_CASE_TABLES = [
    "test_management_case_dependencies",
]


def _table_exists(table: str) -> str:
    return f"EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')"


def _col_exists(table: str, col: str) -> str:
    return (
        f"EXISTS (SELECT 1 FROM information_schema.columns "
        f"WHERE table_name = '{table}' AND column_name = '{col}')"
    )


def upgrade() -> None:
    # Ensure the tenant helper exists. It is normally created by the base RLS
    # migration (mt_rls_0001), but that migration lives on a separate head and
    # may not be present in every deployment — create it defensively (idempotent),
    # mirroring test_mgmt_rls_0001.
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

    for table in _PROJECT_TABLES:
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
                                WHERE tenant_id = current_tenant_id()::text
                            )
                        );

                    CREATE INDEX IF NOT EXISTS idx_{table}_project_id
                        ON {table}(project_id);
                END IF;
            END $$;
        """)

    for table in _CASE_TABLES:
        op.execute(f"""
            DO $$ BEGIN
                IF {_table_exists(table)} AND {_col_exists(table, 'case_id')} THEN
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

                    DROP POLICY IF EXISTS rls_tenant_isolation ON {table};
                    CREATE POLICY rls_tenant_isolation ON {table}
                        USING (
                            case_id IN (
                                SELECT c.id FROM test_management_cases c
                                JOIN test_management_projects p ON c.project_id = p.id
                                WHERE p.tenant_id = current_tenant_id()::text
                            )
                        );

                    CREATE INDEX IF NOT EXISTS idx_{table}_case_id
                        ON {table}(case_id);
                END IF;
            END $$;
        """)


def downgrade() -> None:
    for table in _PROJECT_TABLES + _CASE_TABLES:
        op.execute(f"""
            DO $$ BEGIN
                IF {_table_exists(table)} THEN
                    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
                    DROP POLICY IF EXISTS rls_tenant_isolation ON {table};
                END IF;
            END $$;
        """)
