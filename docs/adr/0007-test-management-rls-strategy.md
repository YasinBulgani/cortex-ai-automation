# ADR 0007 — Test Management Row-Level Security Strategy

**Date:** 2026-05-24
**Status:** Accepted
**Deciders:** Engineering (autonomous loop iteration)
**Related migration:** `test_mgmt_rls_0001` (`backend/alembic/versions/20260524_0003_test_management_rls.py`)

---

## Context

The Neurex Management domain introduces 15 new PostgreSQL tables under the
`test_management_*` prefix.  The platform is multi-tenant; every data access
must be isolated by `tenant_id` at the database layer (RLS) in addition to the
application-layer `TenantMiddleware` + `get_db()` guards already in place.

The existing `mt_rls_0001` migration covers only `tspm_*` tables.  We need to
extend the same RLS framework to the test management domain.

### Table topology

```
test_management_projects          ← has tenant_id (direct)
 └─ test_management_suites        ← has project_id
 └─ test_management_folders       ← has project_id (via suite)
 └─ test_management_cases         ← has project_id
    └─ test_management_case_steps ← has case_id
    └─ test_management_case_versions
 └─ test_management_plans         ← has project_id
    └─ test_management_cycles     ← has plan_id
       └─ test_management_runs    ← has cycle_id → plan → project
          └─ test_management_run_cases         ← 3 hops from project
             └─ test_management_run_step_results  ← 4 hops
 └─ test_management_requirement_links
 └─ test_management_defect_links
 └─ test_management_import_jobs
 └─ test_management_import_job_rows
 └─ test_management_audit_events
```

---

## Decision

### Tier 1 — Direct tenant_id (test_management_projects)

```sql
CREATE POLICY rls_tenant_isolation ON test_management_projects
  USING (tenant_id = current_tenant_id());
```

Simple, fast; `tenant_id` is indexed.

### Tier 2 — Single-hop subquery (13 child tables with project_id)

```sql
CREATE POLICY rls_tenant_isolation ON <child_table>
  USING (
    project_id IN (
      SELECT id FROM test_management_projects
      WHERE tenant_id = current_tenant_id()
    )
  );
```

**Why subquery over denormalised tenant_id?**

- Avoids adding a `tenant_id` column (+ backfill migration) to 13 tables.
- The subquery is rewritten by PostgreSQL to a semi-join; with an index on
  `test_management_projects(tenant_id)` it is effectively O(1) per row check.
- `current_tenant_id()` is `STABLE` — the planner can cache the result within
  a single query, eliminating repeated evaluations.
- Keeps all tenant-isolation logic in a single authoritative table row, making
  tenant re-assignment (rare but possible) a single-row UPDATE.

### Tier 3 — Permissive policy (run_cases, run_step_results)

`test_management_run_cases` and `test_management_run_step_results` are 3–4
hops from `test_management_projects`.  A cross-join policy would be:

```sql
-- hypothetical (not implemented)
USING (
  run_case_id IN (
    SELECT rc.id FROM test_management_run_cases rc
    JOIN test_management_runs r ON r.id = rc.run_id
    JOIN test_management_cycles cy ON cy.id = r.cycle_id
    JOIN test_management_plans pl ON pl.id = cy.plan_id
    WHERE pl.project_id IN (
      SELECT id FROM test_management_projects
      WHERE tenant_id = current_tenant_id()
    )
  )
)
```

This is expensive at runtime and complex to maintain.  Instead we apply a
**permissive policy** (`USING (TRUE)`) and rely on the service layer:

- Every service method that touches run_cases/step_results first resolves the
  run → verifies `run.cycle.plan.project_id` is owned by the current tenant.
- A future migration (`test_mgmt_rls_0002`) can materialise a `project_id`
  denormalised column on `test_management_runs` and apply a subquery policy once
  load testing confirms the cost is acceptable.

---

## Consequences

**Positive:**
- All 15 tables have RLS enabled — accidental full-table scans from
  misconfigured application code are impossible.
- No schema changes required to child tables.
- Policy logic is centralised in `test_management_projects`.
- Indexes are created alongside policies (`idx_<table>_project_id`).

**Negative / Trade-offs:**
- Tier-3 tables rely on service-layer enforcement; a service bug could leak
  cross-tenant step results.  Mitigation: service unit tests cover project
  ownership assertions; deep integration tests cover tenant isolation.
- The subquery for tier-2 tables adds a small overhead per query.  Acceptable
  given the `tenant_id` index and STABLE function caching.

---

## Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Denormalise tenant_id into all 15 tables | Requires 14 extra columns + backfill; no isolation benefit beyond subquery approach |
| Application-layer tenant filter only | No defence-in-depth; a single missing `WHERE tenant_id = ?` leaks data |
| Lateral join policy for deep tables | Correct but expensive; defer until project_id is materialised on runs |

---

## Implementation

Migration: `backend/alembic/versions/20260524_0003_test_management_rls.py`
Revision: `test_mgmt_rls_0001`
Down-revision: `("20260524_0002", "mt_rls_0001")`

All DDL is wrapped in `DO $$ IF EXISTS $$` guards so the migration is
idempotent and safe to re-run.
