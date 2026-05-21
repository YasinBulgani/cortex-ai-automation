"""Multi-tenant Row-Level Security.

Adds tenant_id to core tables and enables Postgres RLS policies so that
each request only sees rows belonging to the authenticated tenant.

Revision ID: mt_rls_0001
Revises: outbox_0001
Create Date: 2026-05-14

Architecture:
  - tenant_id is a UUID FK → tenants.id
  - JWT claims include tenant_id; backend sets SET LOCAL app.current_tenant
  - RLS POLICY: USING (tenant_id = current_setting('app.current_tenant')::uuid)
  - Superuser / migration user bypasses RLS via BYPASSRLS attribute

ADR: docs/adr/0005-multi-tenant-rls.md
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "mt_rls_0001"
down_revision: Union[str, None] = "outbox_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that get tenant_id and RLS
_TENANT_TABLES = [
    "tspm_projects",
    "tspm_scenarios",
    "tspm_executions",
    "tspm_flows",
    "tspm_regression_sets",
    "tspm_approvals",
    "tspm_imports",
    "tspm_requirements",
    "tspm_schedules",
    "tspm_test_data_sets",
    "tspm_project_members",
]


def upgrade() -> None:
    # 1. Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("archived", sa.Boolean, nullable=False, server_default="false"),
    )

    # 2. Seed a default "local" tenant for existing rows
    op.execute("""
        INSERT INTO tenants (id, slug, display_name, plan)
        VALUES ('00000000-0000-0000-0000-000000000001', 'local', 'Local Development', 'enterprise')
        ON CONFLICT (slug) DO NOTHING;
    """)

    # 3. Add tenant_id to each tenant-owned table
    for table in _TENANT_TABLES:
        # Check if table exists before altering
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}') THEN
                    -- Add column if not already present
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = '{table}' AND column_name = 'tenant_id'
                    ) THEN
                        ALTER TABLE {table}
                            ADD COLUMN tenant_id UUID NOT NULL
                            DEFAULT '00000000-0000-0000-0000-000000000001'
                            REFERENCES tenants(id) ON DELETE CASCADE;
                    END IF;
                END IF;
            END $$;
        """)

    # 4. Create helper function to get current tenant from session config
    op.execute("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID
        LANGUAGE plpgsql STABLE SECURITY DEFINER AS $$
        DECLARE
            _tenant_id TEXT;
        BEGIN
            BEGIN
                _tenant_id := current_setting('app.current_tenant', TRUE);
            EXCEPTION WHEN OTHERS THEN
                -- Not set — fall back to default local tenant
                RETURN '00000000-0000-0000-0000-000000000001'::UUID;
            END;
            IF _tenant_id IS NULL OR _tenant_id = '' THEN
                RETURN '00000000-0000-0000-0000-000000000001'::UUID;
            END IF;
            RETURN _tenant_id::UUID;
        END;
        $$;
    """)

    # 5. Enable RLS + create policies
    for table in _TENANT_TABLES:
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}') THEN
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

                    DROP POLICY IF EXISTS rls_tenant_isolation ON {table};
                    CREATE POLICY rls_tenant_isolation ON {table}
                        USING (tenant_id = current_tenant_id());
                END IF;
            END $$;
        """)

    # 6. Create index for performance
    for table in _TENANT_TABLES:
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = '{table}' AND column_name = 'tenant_id') THEN
                    CREATE INDEX IF NOT EXISTS idx_{table}_tenant_id ON {table}(tenant_id);
                END IF;
            END $$;
        """)


def downgrade() -> None:
    # Remove RLS policies + columns in reverse order
    for table in reversed(_TENANT_TABLES):
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}') THEN
                    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
                    DROP POLICY IF EXISTS rls_tenant_isolation ON {table};
                    ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id;
                END IF;
            END $$;
        """)

    op.execute("DROP FUNCTION IF EXISTS current_tenant_id();")
    op.drop_table("tenants")
