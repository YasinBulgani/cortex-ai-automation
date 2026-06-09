# RLS Compliance Audit — Detailed Findings & Remediation Plan

**Date:** 2026-06-09  
**Auditor:** RLS Compliance Scanner  
**Status:** 🔴 **CRITICAL ISSUES FOUND** (1 permissive policy, 11 domains without explicit checks)

---

## Executive Summary

This audit examined multi-tenancy security across the Neurex platform via:
1. **RLS Policies** — PostgreSQL row-level security enforcement
2. **Service Layer** — Application-level tenant isolation checks

### Key Findings

| Metric | Count | Status |
|--------|-------|--------|
| Total RLS Policies | 4 | ✓ Tracked |
| Permissive Policies (USING TRUE) | **1** | 🔴 **CRITICAL** |
| Restrictive Policies | 3 | ✓ Safe |
| Service Domains Audited | 14 | ✓ Complete |
| Domains with Explicit Tenant Checks | 3 | ✓ Safe |
| Domains Relying Only on RLS | **11** | ⚠ **RISK** |

**Overall Risk Level:** 🔴 **MEDIUM-HIGH** (manageable but needs fixes)

---

## Critical Issue #1: test_management_regression_set_cases (Permissive Policy)

### Vulnerability Details

**Location:** `backend/alembic/versions/20260524_0005_test_management_regression_sets.py:153`

```sql
CREATE POLICY rls_service_layer_owns ON test_management_regression_set_cases USING (TRUE);
```

**What This Means:**
- The `USING (TRUE)` clause evaluates to true for **all rows**, regardless of tenant
- No RLS protection at the database level
- **Service layer MUST enforce tenant isolation** via explicit WHERE clauses

### Risk Assessment

**Severity:** 🔴 **HIGH**

**Attack Vector:**
```
Attacker (tenant_A) → reads regression_set_cases → NO RLS FILTER → sees tenant_B data
```

**Actual Protection Dependency:**
```
Service layer query structure → get_case(db, project_id, item.case_id)
                            → select(RegressionSet).where(RegressionSet.project_id == project_id)
```

The `project_id` check indirectly protects through RLS on the parent `RegressionSet` table, but:
1. **Indirect protection is fragile** — refactoring could break this
2. **No defense-in-depth** — RLS should have its own protection
3. **Code review burden** — maintainers must remember this chain

### Verification

All queries to `test_management_regression_set_cases` go through the parent:

```python
# ✓ SAFE: Always accessed through RegressionSet.cases relationship
regression_set.cases.append(RegressionSetCase(...))
selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case)
```

**However:** If someone refactors to query `RegressionSetCase` directly:

```python
# ❌ VULNERABLE: No tenant check at RLS level
db.scalars(select(RegressionSetCase).where(...)).all()
```

This would immediately leak cross-tenant data.

### Remediation

**Step 1: Create restrictive RLS policy**

```sql
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

**Step 2: Create migration file**

```bash
# Generate new migration
cd backend
alembic revision --autogenerate -m "fix_regression_set_cases_rls_policy"
```

Update the generated migration:

```python
def upgrade() -> None:
    op.execute("""
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
    """)

def downgrade() -> None:
    op.execute("""
        DROP POLICY IF EXISTS rls_tenant_isolation ON test_management_regression_set_cases;
        CREATE POLICY rls_service_layer_owns ON test_management_regression_set_cases USING (TRUE);
    """)
```

**Step 3: Test the fix**

```bash
# Apply migration
alembic upgrade head

# Run test suite to verify no performance regressions
pytest backend/tests/ -v -k regression_set
```

**Step 4: Add integration test**

```python
# tests/integration/test_rls_regression_set_cases.py

def test_regression_set_cases_cross_tenant_prevented(db, org_a, org_b):
    """Verify that RLS blocks cross-tenant access to regression set cases"""
    
    # Create regression sets in different tenants
    set_a = db.add(RegressionSet(..., project_id=org_a.project.id))
    set_b = db.add(RegressionSet(..., project_id=org_b.project.id))
    
    case_a = db.add(RegressionSetCase(..., regression_set_id=set_a.id))
    case_b = db.add(RegressionSetCase(..., regression_set_id=set_b.id))
    db.commit()
    
    # Set tenant context to org_a
    db.execute(sa.text("SET app.current_tenant = :tid"), {"tid": org_a.tenant_id})
    
    # User A should see only their cases
    visible = db.scalars(select(RegressionSetCase)).all()
    assert len(visible) == 1
    assert visible[0].id == case_a.id
    
    # User B should NOT see user A's cases
    db.execute(sa.text("SET app.current_tenant = :tid"), {"tid": org_b.tenant_id})
    visible_b = db.scalars(select(RegressionSetCase)).all()
    assert len(visible_b) == 1
    assert visible_b[0].id == case_b.id
```

---

## Issue #2: Service Layer Without Explicit Tenant Checks (11 domains)

### Summary

These 11 domains rely **entirely on RLS policies** for tenant isolation:

| Domain | Queries | Risk Level |
|--------|---------|-----------|
| api_testing | 4 | ⚠ Medium |
| artifacts | 1 | ✓ Low |
| auth | 1 | ⚠ Medium |
| catalog | 3 | ⚠ Medium |
| jobs | 1 | ✓ Low |
| kiwi_tcms | 8 | 🔴 High |
| nexus_repo | 16 | 🔴 High |
| organizations | 9 | 🔴 High |
| quality | 1 | ✓ Low |
| rules | 1 | ✓ Low |
| tspm | 2 | ⚠ Medium |

### Why This Is Risky

**Assumption:** RLS policies exist and are correct

**Reality:** 
- Not all tables have RLS enabled yet (early migrations lack RLS)
- RLS policies can be accidentally dropped or disabled
- Code refactoring might bypass the intended RLS scope

**Example Vulnerability:**

```python
# Current: Works because RLS blocks it
def list_artifacts(db: Session):
    return db.scalars(select(Artifact)).all()  # RLS filters by tenant

# After refactor: User forgets RLS exists
def list_artifacts(db: Session, skip: int = 0):
    return db.scalars(
        select(Artifact)
        .offset(skip)   # Developer adds pagination
        .limit(100)
    ).all()
    # ❌ Still safe? Yes (RLS still works)
    # But maintainer confidence is zero
```

### Recommendation: Add Explicit Tenant Checks

**For high-risk domains (kiwi_tcms, nexus_repo, organizations):**

Pattern:

```python
def list_items(db: Session, tenant_id: str):  # ← Add tenant_id param
    return db.scalars(
        select(Item)
        .where(Item.tenant_id == tenant_id)  # ← Explicit check
    ).all()
```

**For medium-risk domains (api_testing, catalog, tspm):**

Add tenant context injection:

```python
from app.infra.database import get_tenant_context

def list_items(db: Session, tenant_id: Optional[str] = None):
    if tenant_id is None:
        tenant_id = get_tenant_context()  # From request context
    
    return db.scalars(
        select(Item).where(Item.tenant_id == tenant_id)
    ).all()
```

**For low-risk domains (artifacts, jobs, quality, rules):**

Document the RLS dependency:

```python
def list_artifacts(db: Session):
    """List artifacts.
    
    Note: Tenant isolation via RLS policy on artifacts table.
    See ADR-0005 for multi-tenancy architecture.
    """
    return db.scalars(select(Artifact)).all()
```

---

## Issue #3: RLS Policies Not Enabled on All Tables

### Finding

Many core tables created **before** the multi-tenancy migration (20260514) do **not** have RLS policies:

```
Tables WITH RLS:
  ✓ test_management_regression_sets (restrictive)
  ✓ test_management_regression_set_cases (⚠ permissive)
  ✓ test_management_release_signoffs (restrictive)
  ✓ test_management_requirements (restrictive)

Tables WITHOUT RLS (early migrations):
  ✗ tspm_projects
  ✗ tspm_scenarios
  ✗ tspm_executions
  ✗ api_test_specs
  ✗ datasets
  ... (and ~35 more)
```

These tables rely **entirely on service layer checks** — no database-level protection.

### Why This Matters

The `current_tenant_id()` RLS function was added in migration 20260514, but not retroactively applied to pre-existing tables. These tables have `tenant_id` columns (via upgrade) but **RLS is disabled**.

### Remediation Path

**Option A: Gradual RLS Enablement (Recommended)**
- Add restrictive RLS policies to high-value tables in next sprint
- Prioritize: tspm_projects, api_test_specs, datasets
- Risk: Low (we're just adding guards)

**Option B: Service Layer Validation (Interim)**
- Audit all service queries for explicit tenant checks
- Add linting rule: warn if SELECT without WHERE tenant_id
- Defer RLS until schema stabilizes

### Implementation for High-Priority Tables

```python
# backend/alembic/versions/20260610_0001_enable_rls_legacy_tables.py

def upgrade() -> None:
    legacy_tables = [
        ("tspm_projects", "tenant_id"),
        ("tspm_scenarios", "tenant_id"),
        ("api_test_specs", "tenant_id"),
        ("datasets", "tenant_id"),
    ]
    
    for table, tenant_col in legacy_tables:
        op.execute(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            
            DROP POLICY IF EXISTS rls_tenant_isolation ON {table};
            CREATE POLICY rls_tenant_isolation ON {table}
              USING ({tenant_col} = current_tenant_id()::text);
        """)
```

---

## Part 5: Implementation Roadmap

### Phase 1: Critical (This Sprint)

- [ ] **Fix permissive policy** — test_management_regression_set_cases
  - Create migration 20260610_0001
  - Drop `rls_service_layer_owns`, create `rls_tenant_isolation`
  - Add integration test
  - Verify no performance regressions
  - Estimated effort: 2–3 hours

### Phase 2: Short-term (Next Sprint)

- [ ] **Add explicit tenant checks** to high-risk domains
  - kiwi_tcms/service.py: add tenant_id filtering
  - nexus_repo/service.py: add tenant_id filtering
  - organizations/service.py: add tenant_id filtering
  - Estimated effort: 1 day

- [ ] **Enable RLS on legacy tables**
  - Create migration 20260610_0001
  - Add policies to tspm_*, api_test_specs, datasets
  - Test coverage
  - Estimated effort: 1 day

### Phase 3: Long-term (Roadmap)

- [ ] **Tenant-first schema design**
  - Document ADR-0005 update: every new table gets RLS
  - Add schema review checklist: reject tables without RLS
  - Audit remaining tables without RLS (~30+)

- [ ] **RLS compliance CI/CD gate**
  - Script: fails build if new table created without RLS
  - Script: warns if new permissive policy added
  - Run this audit report on every schema change

- [ ] **Tenant audit logging**
  - Log all RLS-blocked queries (security events)
  - Alert on repeated cross-tenant attempts (incident detection)

---

## Appendix: Multi-Tenancy Architecture Reference

### How Tenant Context Works

```
1. User logs in → JWT issued with tenant_id claim
2. Request arrives → backend/app/deps.py:get_current_user()
3. Session set → db.execute(sa.text("SET LOCAL app.current_tenant = :id"), {"id": tenant_id})
4. RLS policies → USING (tenant_id = current_tenant_id())
5. Query executes → only rows matching tenant_id returned
```

### RLS Policy Checklist

When creating a new table with `tenant_id`:

```sql
-- ✓ DO THIS
CREATE POLICY rls_tenant_isolation ON my_table
  USING (tenant_id = current_tenant_id());

-- ❌ NEVER THIS
CREATE POLICY rls_service_layer_owns ON my_table
  USING (TRUE);  -- No protection!

-- ✓ ALSO VALID (for multi-level hierarchies)
CREATE POLICY rls_tenant_isolation ON my_table
  USING (
    project_id IN (
      SELECT id FROM projects
      WHERE tenant_id = current_tenant_id()
    )
  );
```

### Service Layer Pattern

**Safe:**
```python
def get_user_items(db: Session, user_id: str, tenant_id: str):
    return db.scalars(
        select(Item)
        .where(Item.tenant_id == tenant_id, Item.user_id == user_id)
    ).all()
    # Two checks: explicit tenant + explicit user
```

**Acceptable (relies on RLS):**
```python
def get_user_items(db: Session, user_id: str):
    return db.scalars(
        select(Item).where(Item.user_id == user_id)
    ).all()
    # Only one check: user
    # Assumes RLS filters by tenant
```

**Risky (no checks):**
```python
def get_all_items(db: Session):
    return db.scalars(select(Item)).all()
    # Zero checks at service layer
    # Assumes RLS exists and is enabled
```

---

## Sign-off

| Role | Action | Status |
|------|--------|--------|
| Security Lead | Review findings | ⏳ Pending |
| Backend Lead | Approve remediation | ⏳ Pending |
| QA | Add integration tests | ⏳ Pending |

**Generated by:** RLS Compliance Audit Scanner  
**Timestamp:** 2026-06-09 11:16:14 UTC

---

## References

- **ADR-0005:** Multi-Tenancy via RLS — `docs/adr/0005-multi-tenant-rls.md`
- **RLS Migration:** `backend/alembic/versions/20260514_multi_tenant_rls.py`
- **Current Tenant Function:** `backend/alembic/versions/20260514_multi_tenant_rls.py:91-109`
- **Department: Postgres RLS Docs:** https://www.postgresql.org/docs/current/sql-createpolicy.html
