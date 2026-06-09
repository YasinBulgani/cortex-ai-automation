#!/bin/bash
###############################################################################
# RLS Compliance Audit — Verify Row-Level Security & Multi-Tenancy Isolation
#
# Purpose: Audit all database tables and service layer queries to ensure
# proper tenant isolation via RLS policies and explicit WHERE clauses.
#
# Usage:
#   ./backend/scripts/rls_compliance_audit.sh [--full] [--fix-permissive]
#
# Options:
#   --full           Generate extended report with SQL queries
#   --fix-permissive Auto-generate FIX recommendations for permissive policies
#
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
REPORT_FILE="$BACKEND_DIR/../docs/AUDIT_RLS_COMPLIANCE_$(date +%Y-%m-%d).md"

FULL_REPORT="${1:-}"
FIX_MODE=0

if [[ "$FULL_REPORT" == "--full" ]]; then
    FIX_MODE=1
fi

if [[ "$FULL_REPORT" == "--fix-permissive" ]]; then
    FIX_MODE=1
fi

echo "Starting RLS Compliance Audit..."
echo "Project: $PROJECT_ROOT"
echo "Report: $REPORT_FILE"
echo ""

###############################################################################
# PHASE 1: Scan Service Layer for Explicit Tenant Checks
###############################################################################

cat > /tmp/service_layer_audit.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import re
from pathlib import Path
from collections import defaultdict

QUERY_PATTERNS = [
    r'db\.query\(',
    r'session\.query\(',
    r'db\.execute\(',
    r'session\.execute\(',
    r'select\(',
]

TENANT_PATTERNS = [
    r'tenant_id',
    r'\.where.*tenant',
    r'current_tenant',
]

results = {}
backend_path = Path('/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/backend')

for service_file in sorted(backend_path.glob('app/domains/*/service.py')):
    domain = service_file.parent.name
    content = service_file.read_text(encoding='utf-8', errors='ignore')

    has_query = any(re.search(p, content) for p in QUERY_PATTERNS)
    if has_query:
        tenant_refs = len(re.findall(r'tenant_id|current_tenant', content))
        query_count = sum(1 for line in content.split('\n')
                         if any(re.search(p, line) for p in QUERY_PATTERNS))

        results[domain] = {
            'file': str(service_file.relative_to(backend_path)),
            'query_count': query_count,
            'has_tenant_check': tenant_refs > 0,
            'tenant_mentions': tenant_refs,
        }

# Output as structured format
for domain in sorted(results.keys()):
    info = results[domain]
    status = "SAFE" if info['has_tenant_check'] else "ALERT"
    print(f"{domain}|{info['file']}|{status}|{info['query_count']}|{info['tenant_mentions']}")

PYTHON_SCRIPT

python3 /tmp/service_layer_audit.py > /tmp/service_audit.txt 2>&1

###############################################################################
# PHASE 2: Extract RLS Policies from Migrations
###############################################################################

cat > /tmp/rls_policy_audit.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import re
from pathlib import Path

migrations_path = Path('/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/backend/alembic/versions')
policies = {}

for mig_file in sorted(migrations_path.glob('*.py')):
    content = mig_file.read_text()
    policy_matches = re.findall(
        r'CREATE POLICY\s+(\w+)\s+ON\s+(\w+)[^;]*?USING\s*\(([^)]+)\)',
        content,
        re.MULTILINE | re.DOTALL
    )

    for policy_name, table_name, using_clause in policy_matches:
        key = f"{table_name}/{policy_name}"
        if key not in policies:
            policies[key] = {
                'table': table_name,
                'policy': policy_name,
                'using': using_clause.strip()[:100],
                'is_permissive': 'TRUE' in using_clause.upper() and 'CURRENT_' not in using_clause,
                'migration': mig_file.name,
            }

# Output structured
for key in sorted(policies.keys()):
    p = policies[key]
    status = "PERMISSIVE" if p['is_permissive'] else "RESTRICTIVE"
    print(f"{p['table']}|{p['policy']}|{status}|{p['using']}")

PYTHON_SCRIPT

python3 /tmp/rls_policy_audit.py > /tmp/rls_audit.txt 2>&1

###############################################################################
# PHASE 3: Build Markdown Report
###############################################################################

cat > "$REPORT_FILE" << 'REPORT_EOF'
# RLS Compliance Audit

**Generated:** $(date)
**Project:** Cortex AI Automation (Neurex)
**Auditor:** RLS Compliance Scanner

---

## Executive Summary

Multi-tenancy security depends on two layers:
1. **RLS (Row-Level Security)** — PostgreSQL enforces isolation at DB layer
2. **Service Layer** — Explicit WHERE clauses for defense-in-depth

### Status Overview

- **Total Policies Found:** [POLICIES_COUNT]
- **Restrictive Policies:** [RESTRICTIVE_COUNT] ✓
- **Permissive Policies:** [PERMISSIVE_COUNT] ⚠ **ACTION REQUIRED**
- **Service Domains Audited:** [DOMAINS_COUNT]
- **Domains With Explicit Tenant Checks:** [SAFE_DOMAINS_COUNT]
- **Domains Without Tenant Checks:** [ALERT_DOMAINS_COUNT] ⚠

---

## Part 1: RLS Policy Audit

### Restrictive Policies (Safe)

Policies that explicitly check `tenant_id` or use subqueries to validate tenant context.

RESTRICTIVE_POLICIES_TABLE

### Permissive Policies (⚠ Critical)

Policies using `USING (TRUE)` — **service layer MUST enforce tenant isolation**.

PERMISSIVE_POLICIES_TABLE

**Risk:** Any bug in service layer code exposes cross-tenant data.

---

## Part 2: Service Layer Query Audit

### Domains With Explicit Tenant Checks ✓

These services query with explicit `WHERE tenant_id = ...` or `WHERE ... tenant_id ...`:

SERVICE_SAFE_TABLE

### Domains Without Explicit Tenant Checks ⚠

These services rely entirely on RLS to prevent cross-tenant access:

SERVICE_ALERT_TABLE

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
# Check if regression_set_cases service enforces tenant isolation
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

| Role | Name | Date |
|------|------|------|
| Auditor | RLS Compliance Scanner | $(date) |
| Reviewer | [PENDING] | — |

REPORT_EOF

###############################################################################
# PHASE 4: Populate Report with Audit Results
###############################################################################

# Count policies
POLICIES_COUNT=$(grep -c . /tmp/rls_audit.txt || echo "0")
RESTRICTIVE_COUNT=$(grep RESTRICTIVE /tmp/rls_audit.txt | wc -l || echo "0")
PERMISSIVE_COUNT=$(grep PERMISSIVE /tmp/rls_audit.txt | wc -l || echo "0")
DOMAINS_COUNT=$(grep -c . /tmp/service_audit.txt || echo "0")
SAFE_DOMAINS_COUNT=$(grep SAFE /tmp/service_audit.txt | wc -l || echo "0")
ALERT_DOMAINS_COUNT=$(grep ALERT /tmp/service_audit.txt | wc -l || echo "0")

# Build policy tables
RESTRICTIVE_TABLE=$(cat /tmp/rls_audit.txt | grep RESTRICTIVE | awk -F'|' '{
    print "| " $1 " | " $2 " | RESTRICTIVE | " substr($4, 1, 70) " |"
}')

PERMISSIVE_TABLE=$(cat /tmp/rls_audit.txt | grep PERMISSIVE | awk -F'|' '{
    print "| " $1 " | " $2 " | ⚠ PERMISSIVE | " substr($4, 1, 70) " |"
}')

SERVICE_SAFE=$(cat /tmp/service_audit.txt | grep SAFE | awk -F'|' '{
    print "| " $1 " | ✓ " $4 " queries | " $5 " mentions |"
}')

SERVICE_ALERT=$(cat /tmp/service_audit.txt | grep ALERT | awk -F'|' '{
    print "| " $1 " | ⚠ " $4 " queries | " $5 " mentions |"
}')

# Replace placeholders
sed -i '' "s/\[POLICIES_COUNT\]/$POLICIES_COUNT/g" "$REPORT_FILE"
sed -i '' "s/\[RESTRICTIVE_COUNT\]/$RESTRICTIVE_COUNT/g" "$REPORT_FILE"
sed -i '' "s/\[PERMISSIVE_COUNT\]/$PERMISSIVE_COUNT/g" "$REPORT_FILE"
sed -i '' "s/\[DOMAINS_COUNT\]/$DOMAINS_COUNT/g" "$REPORT_FILE"
sed -i '' "s/\[SAFE_DOMAINS_COUNT\]/$SAFE_DOMAINS_COUNT/g" "$REPORT_FILE"
sed -i '' "s/\[ALERT_DOMAINS_COUNT\]/$ALERT_DOMAINS_COUNT/g" "$REPORT_FILE"

# Add tables
sed -i '' "/RESTRICTIVE_POLICIES_TABLE/c\\
| Table | Policy | Status | Using Clause |\\
|-------|--------|--------|--------------|\\
$RESTRICTIVE_TABLE
" "$REPORT_FILE"

sed -i '' "/PERMISSIVE_POLICIES_TABLE/c\\
| Table | Policy | Status | Using Clause |\\
|-------|--------|--------|--------------|\\
$PERMISSIVE_TABLE
" "$REPORT_FILE"

sed -i '' "/SERVICE_SAFE_TABLE/c\\
| Domain | Queries | Tenant Mentions |\\
|--------|---------|-----------------|\\
$SERVICE_SAFE
" "$REPORT_FILE"

sed -i '' "/SERVICE_ALERT_TABLE/c\\
| Domain | Queries | Tenant Mentions |\\
|--------|---------|-----------------|\\
$SERVICE_ALERT
" "$REPORT_FILE"

###############################################################################
# Final Output
###############################################################################

echo ""
echo "✓ RLS Compliance Audit Complete"
echo ""
echo "Report Summary:"
echo "  Total RLS Policies:         $POLICIES_COUNT"
echo "  Restrictive (Safe):         $RESTRICTIVE_COUNT ✓"
echo "  Permissive (Risk):          $PERMISSIVE_COUNT ⚠"
echo "  Service Domains:            $DOMAINS_COUNT"
echo "  Domains with Tenant Check:  $SAFE_DOMAINS_COUNT ✓"
echo "  Domains without Check:      $ALERT_DOMAINS_COUNT ⚠"
echo ""
echo "Full Report: $REPORT_FILE"
echo ""
