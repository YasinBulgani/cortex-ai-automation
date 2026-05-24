# ADR-0005: Multi-Tenant Row-Level Security

**Status:** Accepted  
**Date:** 2026-05-14  
**Author:** Platform Team

---

## Context

Neurex QA is expanding from a single-tenant (on-prem / self-hosted) to a multi-tenant SaaS architecture. Multiple organizations (tenants) need complete data isolation: one tenant must never be able to read, write, or even infer the existence of another tenant's data.

Options considered:

| Approach | Isolation | Complexity | Performance |
|----------|-----------|------------|-------------|
| Application-layer WHERE clause | Medium | Low (but error-prone) | Good |
| Separate DB per tenant | Maximum | Very High | Operational nightmare |
| **Postgres Row-Level Security (RLS)** | **Maximum** | **Medium** | **Good** |
| Separate schema per tenant | High | High | Good |

---

## Decision

Use **PostgreSQL Row-Level Security (RLS)** with a `tenant_id UUID` column on all tenant-owned tables.

### Mechanism

```sql
-- Session variable set at request start
SET LOCAL app.current_tenant = '<uuid>';

-- RLS policy (auto-applied to every query)
CREATE POLICY rls_tenant_isolation ON tspm_projects
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

The FastAPI `TenantMiddleware` extracts `tenant_id` from the JWT `tenant` claim and stores it in `request.state`. The DB session layer executes `SET LOCAL app.current_tenant` before the first query.

---

## Implementation

### Migration: `mt_rls_0001`
- Creates `tenants` table
- Adds `tenant_id UUID NOT NULL` to 11 core tables
- Enables `ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`
- Creates `current_tenant_id()` helper function
- Seeds a default local-dev tenant (`00000000-...0001`)

### Middleware: `app/core/tenant_middleware.py`
- Runs on every request (O(1) JWT parsing, no DB call)
- Validated UUID format — no SQL injection possible
- Falls back to local-dev tenant when no claim present

### Default Tenant
Local development and migrations run under tenant `00000000-0000-0000-0000-000000000001` (`slug=local`). This preserves all existing data.

---

## Consequences

**Positive:**
- Data isolation enforced at the DB layer, not application layer — impossible to bypass via missing WHERE clause
- No performance overhead for small-medium tenant counts (single index scan on `tenant_id`)
- Transparent to most application queries

**Negative:**
- `FORCE ROW LEVEL SECURITY` means the DB superuser also sees filtered rows when RLS is active (must use `BYPASSRLS` role for migrations)
- Cross-tenant reporting (admin dashboard) requires a privileged role
- Alembic migrations must run under a `BYPASSRLS` user

**Mitigations:**
- Migration user has `BYPASSRLS` attribute
- Admin context uses a separate connection with `SET ROLE admin_role`

---

## Affected Tables

1. `tspm_projects`
2. `tspm_scenarios`
3. `tspm_executions`
4. `tspm_flows`
5. `tspm_regression_sets`
6. `tspm_approvals`
7. `tspm_imports`
8. `tspm_requirements`
9. `tspm_schedules`
10. `tspm_test_data_sets`
11. `tspm_project_members`
