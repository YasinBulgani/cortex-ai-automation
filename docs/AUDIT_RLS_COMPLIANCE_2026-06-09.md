# RLS Compliance Audit

**Generated:** 2026-06-09 11:16:14
**Project:** Cortex AI Automation (Neurex)
**Scope:** Multi-tenancy security audit

---

## Executive Summary

Multi-tenancy security depends on two layers:
1. **RLS (Row-Level Security)** — PostgreSQL enforces isolation at DB layer
2. **Service Layer** — Explicit WHERE clauses for defense-in-depth

### Status Overview

- **Total Policies Found:** 4
- **Restrictive Policies:** 3 ✓
- **Permissive Policies:** 1 ⚠ **ACTION REQUIRED**
- **Service Domains Audited:** 14
- **Domains With Explicit Tenant Checks:** 3
- **Domains Without Tenant Checks:** 11 ⚠

---

## Part 1: RLS Policy Audit

### Restrictive Policies (Safe)

Policies that explicitly check tenant_id or use subqueries to validate tenant context.

| Table | Policy | Status | Using Clause |
|-------|--------|--------|--------------|
| test_management_regression_sets | rls_tenant_isolation | ✓ RESTRICTIVE | project_id IN (SELECT id FROM test_management_projects WHERE tenant_id... |
| test_management_release_signoffs | rls_tenant_isolation | ✓ RESTRICTIVE | project_id IN (SELECT id FROM test_management_projects WHERE tenant_id... |
| test_management_requirements | rls_tenant_isolation | ✓ RESTRICTIVE | project_id IN (SELECT id FROM test_management_projects WHERE tenant_id... |

### Permissive Policies (⚠ Critical)

Policies using `USING (TRUE)` — **service layer MUST enforce tenant isolation**.

| Table | Policy | Status | Using Clause |
|-------|--------|--------|--------------|
| test_management_regression_set_cases | rls_service_layer_owns | ⚠ PERMISSIVE | TRUE |

**Risk:** Any bug in service layer code exposes cross-tenant data.

---

## Part 2: Service Layer Query Audit

### Domains With Explicit Tenant Checks ✓

These services query with explicit `WHERE tenant_id = ...`:

| Domain | Queries | Tenant Mentions |
|--------|---------|-----------------|
| billing | 10 | 21 ✓ |
| privacy | 7 | 35 ✓ |
| test_management | 104 | 6 ✓ |

### Domains Without Explicit Tenant Checks ⚠

These services rely entirely on RLS to prevent cross-tenant access:

| Domain | Queries | Tenant Mentions |
|--------|---------|-----------------|
| api_testing | 4 | 0 |
| artifacts | 1 | 0 |
| auth | 1 | 0 |
| catalog | 3 | 0 |
| jobs | 1 | 0 |
| kiwi_tcms | 8 | 0 |
| nexus_repo | 16 | 0 |
| organizations | 9 | 0 |
| quality | 1 | 0 |
| rules | 1 | 0 |
| tspm | 2 | 0 |

**Recommendation:** Add explicit WHERE clauses for defense-in-depth.

---

## Part 3: Critical Findings

### Finding #1: test_management_regression_set_cases

**Severity:** 🔴 **HIGH**

**Policy:** `rls_service_layer_owns` using `USING (TRUE)` — **permissive**

**Impact:**
- Table has NO RLS protection
- Service layer MUST enforce `project_id IN (SELECT ... WHERE tenant_id = ?)`
- Risk: Typo in service layer → cross-tenant data leak

**Verification:**
```bash
grep -n "regression_set_cases\|RegressionSetCase" \
  backend/app/domains/test_management/service.py | grep tenant
```

**Remediation:**
```sql
-- Change from permissive to restrictive
ALTER TABLE test_management_regression_set_cases
  DROP POLICY rls_service_layer_owns;

CREATE POLICY rls_tenant_isolation ON test_management_regression_set_cases
  USING (
    regression_set_id IN (
      SELECT id FROM test_management_regression_sets
      WHERE project_id IN (
        SELECT id FROM test_management_projects
        WHERE tenant_id = current_tenant_id()
      )
    )
  );
```

---

## Part 4: Multi-Tenancy Architecture Review

### Current Implementation

1. **Tenant Scope:** Organization/Workspace
2. **RLS Function:** `current_tenant_id()` reads from `app.current_tenant` session variable
3. **Enforcement:**
   - Backend sets `SET LOCAL app.current_tenant = <uuid>` in deps.py
   - All requests include `user.tenant_id` from JWT token
4. **Bypass:** Superuser role bypasses RLS (safe for migrations)

### Security Assumptions

- ✓ JWT token decode is secure (verify issuer + signature)
- ✓ Backend sets session variable correctly per request
- ✓ Service layer has no logic errors introducing leaks
- ⚠ Permissive RLS policies are bug-tolerant (service layer MUST have defense)

---

## Part 5: Recommendations

### Immediate (Critical)

1. **Fix `test_management_regression_set_cases` permissive policy**
   - Change `USING (TRUE)` → restrictive policy (see Remediation above)
   - Verify service layer enforces tenant checks
   - Add integration test for cross-tenant prevention

2. **Add explicit WHERE clauses to high-risk domains**
   - domains: api_testing, nexus_repo, kiwi_tcms, organizations
   - Reason: Defense-in-depth — don't rely solely on RLS

### Short-term (1–2 sprints)

3. **Audit all 53 domain services**
   - Create checklist of each domain's tenant isolation strategy
   - Document whether domain is tenant-scoped or global (e.g., shared libraries)

4. **Add RLS compliance test to CI/CD**
   - Generate this report on every schema change
   - Fail build if new permissive policies are added
   - Warn if service layer adds unguarded queries

### Long-term (Roadmap)

5. **Migrate to tenant-first architecture**
   - Every table should have explicit tenant_id FK
   - Every RLS policy should be restrictive (no USING TRUE)
   - Remove need for service layer tenant checks (RLS handles it)

6. **Implement tenant audit logging**
   - Log all cross-tenant query attempts (blocked by RLS)
   - Send alerts for repeated attempts

---

## Appendices

### A: RLS Policy Syntax Reference

```sql
-- Restrictive (Safe)
CREATE POLICY rls_tenant_isolation ON my_table
  USING (tenant_id = current_tenant_id());

-- Permissive (Dangerous)
CREATE POLICY rls_service_layer_owns ON my_table
  USING (TRUE);  -- ❌ No check!

-- Complex (Based on role)
CREATE POLICY rls_shared_with_me ON documents
  USING (
    owner_id = current_user_id() OR
    id IN (
      SELECT document_id FROM document_shares
      WHERE user_id = current_user_id()
    )
  );
```

### B: Service Layer Query Patterns

**Vulnerable Pattern (relies only on RLS):**
```python
def get_items(db: Session):
    return db.scalars(select(Item)).all()  # ❌ No tenant check
```

**Safe Pattern (explicit + RLS defense-in-depth):**
```python
def get_items(db: Session, tenant_id: str):
    return db.scalars(
        select(Item).where(Item.tenant_id == tenant_id)
    ).all()  # ✓ Explicit check
```

### C: Migration Checklist

When adding a new table:

- [ ] Add `tenant_id` UUID FK column
- [ ] Create restrictive RLS policy using `current_tenant_id()`
- [ ] Service layer includes explicit `WHERE tenant_id = ?`
- [ ] Write integration test for cross-tenant access prevention
- [ ] Document in ADR-0005 (multi-tenancy)

---

## Sign-off

| Aspect | Status | Notes |
|--------|--------|-------|
| Policy Count | {len(policies)} | 4 detected |
| Permissive Risk | {len(permissive_policies)} ⚠ | 1 critical (test_management_regression_set_cases) |
| Service Layer Coverage | {len([d for d, v in service_results.items() if v['has_tenant_check']])}/{len(service_results)} | Partial |
| Recommendations | 5 | Critical, Short-term, Long-term |

**Generated by:** RLS Compliance Scanner
**Date:** {datetime.now().strftime('%Y-%m-%d')}
