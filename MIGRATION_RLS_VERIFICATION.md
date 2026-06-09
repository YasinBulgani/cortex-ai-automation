# Migration RLS Verification Report

**Date:** 2026-06-09  
**Migration:** `20260609_0001_rls_new_mgmt_tables.py`  
**Status:** VERIFIED & ENHANCED

---

## Overview

Fixed missing Multi-Tenant RLS (Row-Level Security) policies on 5 new management tables that were created without proper tenant isolation, creating a cross-tenant data leak risk.

---

## Tables Fixed (5 Total)

### 1. test_management_shared_steps
- **Location:** `backend/alembic/versions/20260606_0003_create_missing_feature_tables.py`
- **Schema:** `(id, project_id, name, description, action, expected, ...)`
- **RLS Path:** Direct single-hop: `project_id → test_management_projects.tenant_id`
- **Policy:** `rls_tenant_isolation` with USING + WITH CHECK clauses

### 2. mgmt_comments
- **Location:** `backend/alembic/versions/20260528_0001_mgmt_comments_notifications.py`
- **Schema:** `(id, tenant_id, project_id, entity_type, entity_id, body_md, ...)`
- **RLS Path:** Direct single-hop: `project_id → test_management_projects.tenant_id`
- **Policy:** `rls_tenant_isolation` with USING + WITH CHECK clauses

### 3. test_management_exploration_sessions
- **Location:** `backend/alembic/versions/20260608_0003_add_exploration_sessions.py`
- **Schema:** `(id, project_id, tester_id, duration_seconds, ...)`
- **RLS Path:** Direct single-hop: `project_id → test_management_projects.tenant_id`
- **Policy:** `rls_tenant_isolation` with USING + WITH CHECK clauses

### 4. mgmt_design_technique_runs
- **Location:** `backend/alembic/versions/20260528_0004_mgmt_design_techniques.py`
- **Schema:** `(id, tenant_id, project_id, technique, input_spec, generated_cases, ...)`
- **RLS Path:** Direct single-hop: `project_id → test_management_projects.tenant_id`
- **Policy:** `rls_tenant_isolation` with USING + WITH CHECK clauses

### 5. test_management_case_dependencies
- **Location:** `backend/alembic/versions/b2c3d4e5f6a7_add_case_dependencies_table.py`
- **Schema:** `(id, case_id, depends_on_id, dep_type, created_at)`
- **RLS Path:** Two-hop indirect: `case_id → test_management_cases.project_id → test_management_projects.tenant_id`
- **Policy:** `rls_tenant_isolation` with USING + WITH CHECK clauses via JOIN

---

## Migration Implementation

**File:** `/backend/alembic/versions/20260609_0001_rls_new_mgmt_tables.py`

### Key Features

1. **Defensive Guards**
   - `_table_exists()` check: skips gracefully if table not present
   - `_col_exists()` check: skips gracefully if expected column missing
   - Wrapped in PL/pgSQL DO blocks for safe no-op behavior

2. **RLS Policy Pattern**
   ```sql
   CREATE POLICY rls_tenant_isolation ON {table}
       USING (...)           -- SELECT/DELETE filtering
       WITH CHECK (...);     -- INSERT/UPDATE constraint enforcement
   ```
   - **USING clause:** Controls which rows can be selected or deleted
   - **WITH CHECK clause:** Ensures inserted/updated rows belong to current tenant
   - Both use identical subqueries for consistency

3. **current_tenant_id() Helper**
   - Reads `app.current_tenant` session variable
   - Falls back to default local tenant `00000000-0000-0000-0000-000000000001` if unset
   - `SECURITY DEFINER` so it works across RLS boundaries

4. **Index Creation**
   - `idx_{table}_project_id` for single-hop tables (query performance)
   - `idx_{table}_case_id` for two-hop tables (query performance)

5. **Downgrade Path**
   - Disables RLS and drops policies cleanly
   - Safe to re-run if migration fails partway

---

## RLS Policy Details

### Single-Hop Tables (4 tables)

**Subquery Logic:**
```sql
project_id IN (
    SELECT id FROM test_management_projects
    WHERE tenant_id = current_tenant_id()::text
)
```

**Result:** Only rows from projects owned by the current tenant are visible/modifiable.

### Two-Hop Tables (1 table: case_dependencies)

**Subquery Logic:**
```sql
case_id IN (
    SELECT c.id FROM test_management_cases c
    JOIN test_management_projects p ON c.project_id = p.id
    WHERE p.tenant_id = current_tenant_id()::text
)
```

**Result:** Only dependencies on cases from projects owned by the current tenant are visible/modifiable.

---

## Test Coverage

**Test File:** `/backend/tests/integration/test_rls_new_mgmt_tables.py`

### Test Classes (5 × 2 tests = 10 total)

1. **TestSharedStepsRLS**
   - `test_shared_steps_visible_to_own_tenant()` — Tenant A sees own steps ✓
   - `test_shared_steps_hidden_from_other_tenant()` — Tenant B blocked from A's steps ✓

2. **TestMgmtCommentsRLS**
   - `test_comments_visible_to_own_tenant()` — Tenant A sees own comments ✓
   - `test_comments_hidden_from_other_tenant()` — Tenant B blocked from A's comments ✓

3. **TestExplorationSessionsRLS**
   - `test_sessions_visible_to_own_tenant()` — Tenant A sees own sessions ✓
   - `test_sessions_hidden_from_other_tenant()` — Tenant B blocked from A's sessions ✓

4. **TestDesignTechniqueRunsRLS**
   - `test_runs_visible_to_own_tenant()` — Tenant A sees own runs ✓
   - `test_runs_hidden_from_other_tenant()` — Tenant B blocked from A's runs ✓

5. **TestCaseDependenciesRLS**
   - `test_dependencies_visible_to_own_tenant()` — Tenant A sees own dependencies ✓
   - `test_dependencies_hidden_from_other_tenant()` — Tenant B blocked from A's dependencies ✓

### Running Tests

```bash
# Run all RLS tests for new mgmt tables
pytest backend/tests/integration/test_rls_new_mgmt_tables.py -v

# Run with postgres available
make docker-up  # Ensure postgres:5432 running
pytest backend/tests/integration/test_rls_new_mgmt_tables.py -v --tb=short
```

---

## Verification Checklist

- [x] All 5 tables have RLS ENABLED
- [x] All 5 tables have FORCE ROW LEVEL SECURITY set
- [x] All policies use USING + WITH CHECK clauses (not just USING)
- [x] Subqueries correctly filter by `current_tenant_id()`
- [x] Single-hop tables (4) use project_id subqueries
- [x] Two-hop table (1) uses case→project JOIN subquery
- [x] Indexes created for query performance
- [x] Helper function `current_tenant_id()` is idempotent
- [x] Migration guards against missing tables/columns
- [x] Downgrade path tested (PL/pgSQL safe)
- [x] Cross-tenant access scenarios tested (10 test cases)

---

## Security Impact

### Before (VULNERABILITY)
- Queries on these 5 tables had NO RLS filtering
- Tenant A user could read/write Tenant B's:
  - Shared steps
  - Comments
  - Exploration sessions
  - Design technique runs
  - Case dependencies

### After (FIXED)
- All 5 tables now enforce RLS via `current_tenant_id()` session variable
- Tenant A user can ONLY access rows where:
  - `project_id` belongs to a Tenant A project (single-hop)
  - OR `case_id` belongs to a Tenant A case (two-hop)
- INSERT/UPDATE operations validated via WITH CHECK clause
- DELETE/SELECT filtered via USING clause

---

## Deployment Instructions

1. **Ensure migration is in the correct order:**
   ```bash
   # Check revision chain
   alembic current  # Should show 20260608_0003
   ```

2. **Apply migration:**
   ```bash
   alembic upgrade head
   # Or via make target:
   make migrate
   ```

3. **Verify RLS policies exist:**
   ```sql
   SELECT schemaname, tablename
   FROM pg_tables
   WHERE tablename IN ('test_management_shared_steps', 'mgmt_comments',
                        'test_management_exploration_sessions', 'mgmt_design_technique_runs',
                        'test_management_case_dependencies')
   ORDER BY tablename;

   -- Check policies:
   SELECT tablename, policyname, USING, WITH_CHECK
   FROM pg_policies
   WHERE tablename IN (...)
   ORDER BY tablename;
   ```

4. **Run integration tests:**
   ```bash
   pytest backend/tests/integration/test_rls_new_mgmt_tables.py -v
   ```

---

## Files Modified

| File | Change |
|------|--------|
| `/backend/alembic/versions/20260609_0001_rls_new_mgmt_tables.py` | Enhanced with WITH CHECK clauses |
| `/backend/tests/integration/test_rls_new_mgmt_tables.py` | Created (10 test cases) |

---

## References

- **ADR:** docs/adr/0005-multi-tenant-rls.md
- **Related Migration:** `20260524_0003_test_management_rls.py` (original RLS pattern)
- **Related Migration:** `20260514_multi_tenant_rls.py` (base multi-tenant RLS setup)

---

## Known Limitations

None identified. All 5 tables are now properly isolated.

---

## Future Work

- Monitor for performance impact on large tables (explore partial indexes if needed)
- Consider adding RLS audit logging via `pg_stat_statements` in production
- Document RLS policy review process for new tables in developer guide
