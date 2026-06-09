# RLS Compliance Audit — Complete Index

**Date:** June 9, 2026  
**Status:** ✓ Complete

This index provides navigation to all RLS compliance audit artifacts generated during Risk #4 investigation.

---

## Quick Start

**For executives/decision-makers:**  
→ Start with: [Executive Summary](#executive-summary-1-page)

**For security leads:**  
→ Start with: [Critical Findings](#critical-findings-with-remediation-code)

**For backend engineers:**  
→ Start with: [Remediation Roadmap](#remediation-roadmap)

**To run the audit yourself:**  
→ Run: `backend/scripts/rls_compliance_audit.sh`

---

## Report Structure

### 1. Executive Summary (1 page)

**File:** Not separate (inline below)

**Key Numbers:**
- 4 RLS policies found
- 3 restrictive ✓, 1 permissive ❌
- 14 service domains audited
- 3 with explicit tenant checks, 11 without

**Key Decisions Needed:**
- Fix permissive policy (this sprint)
- Add explicit checks to 3 high-risk domains (next sprint)

---

### 2. Audit Results Report (7 KB)

**File:** `docs/AUDIT_RLS_COMPLIANCE_2026-06-09.md`

**Contains:**
- Summary statistics
- RLS policy audit (4 policies, status breakdown)
- Service layer audit (14 domains, query counts)
- Critical finding #1 (regression_set_cases)
- Architecture review
- Recommendations (5 phases)
- Appendices (syntax reference, patterns)

**Audience:** Security lead, backend architect

**Time to read:** 15 minutes

---

### 3. Critical Findings with Remediation Code (13 KB)

**File:** `docs/RLS_COMPLIANCE_FINDINGS_2026-06-09.md`

**Contains:**
- Detailed vulnerability analysis
- Issue #1: Permissive policy (CRITICAL) with fix code
- Issue #2: 11 domains without explicit checks
- Issue #3: Legacy tables without RLS
- Implementation roadmap (3 phases, effort estimates)
- Migration code templates
- Integration test examples
- Multi-tenancy reference guide

**Audience:** Backend engineers, security engineers

**Time to read:** 30 minutes  
**Time to implement Phase 1:** 2–3 hours

---

### 4. Quick Reference Summary (9 KB)

**File:** `backend/scripts/RLS_AUDIT_SUMMARY.txt`

**Contains:**
- One-page summary
- Vulnerability assessment
- Risk scenarios
- Remediation code snippets (copy-paste ready)
- Compliance checklist
- Escalation procedures

**Audience:** Developers, on-call engineers

**Time to read:** 5 minutes

---

### 5. Automated Audit Script (Executable)

**File:** `backend/scripts/rls_compliance_audit.sh`

**Usage:**
```bash
# Run the audit
./backend/scripts/rls_compliance_audit.sh

# Run with full report
./backend/scripts/rls_compliance_audit.sh --full
```

**What it does:**
1. Scans all service.py files for queries
2. Analyzes RLS policies in migrations
3. Generates compliance report
4. Outputs statistics

**Frequency:** Run on every schema change or weekly

---

## Key Findings Summary

### Critical Issue #1: Permissive RLS Policy

```
Table:    test_management_regression_set_cases
Policy:   rls_service_layer_owns
Problem:  USING (TRUE) → no RLS protection
Severity: 🔴 HIGH
Fix:      Change to restrictive subquery policy
Time:     2–3 hours
```

**Remediation Code:**
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

### Issue #2: 11 Domains Without Explicit Tenant Checks

```
High-Risk Domains:
  • kiwi_tcms (8 queries)
  • nexus_repo (16 queries)
  • organizations (9 queries)

Medium-Risk Domains:
  • api_testing (4 queries)
  • catalog (3 queries)
  • tspm (2 queries)
  • auth (1 query)

Low-Risk Domains:
  • artifacts, jobs, quality, rules (1 query each)

Fix: Add explicit WHERE tenant_id = ? to all queries
Time: 1 day per domain
```

### Issue #3: Legacy Tables Without RLS

```
Tables Created Before Migration 20260514:
  • tspm_projects
  • tspm_scenarios
  • api_test_specs
  • datasets
  • ... (35+ more)

Status: Have tenant_id column but RLS disabled
Fix: Create migration to enable RLS on legacy tables
Time: 1 day
```

---

## Implementation Timeline

### Phase 1: Critical (This Sprint)
- [ ] Fix permissive policy on regression_set_cases
- [ ] Add integration test
- [ ] Deploy migration
- **Effort:** 2–3 hours

### Phase 2: Short-term (Next Sprint)
- [ ] Add explicit tenant checks to kiwi_tcms, nexus_repo, organizations
- [ ] Enable RLS on legacy tables
- **Effort:** 2 days

### Phase 3: Long-term (Roadmap)
- [ ] Tenant-first schema design rule
- [ ] CI/CD gate for RLS compliance
- [ ] Tenant audit logging
- **Effort:** Ongoing

---

## Compliance Checklist

For each new table:
```
[ ] tenant_id UUID FK column added
[ ] RLS policy created (RESTRICTIVE, never USING TRUE)
[ ] Service layer has explicit WHERE tenant_id = ?
[ ] Cross-tenant access test added
[ ] ADR-0005 updated
[ ] Code review passed
```

For service layer:
```
[ ] Queries include WHERE tenant_id
[ ] OR: documented as RLS-protected
[ ] OR: documented as global (not tenant-scoped)
```

---

## Related Documentation

- **ADR-0005:** Multi-tenancy via RLS — `docs/adr/0005-multi-tenant-rls.md`
- **Multi-tenancy Architecture:** `backend/alembic/versions/20260514_multi_tenant_rls.py`
- **RLS Function:** `backend/app/deps.py` (search: current_tenant_id)

---

## Files Generated by This Audit

```
docs/
  ├── AUDIT_RLS_COMPLIANCE_2026-06-09.md          [7.1 KB]
  ├── RLS_COMPLIANCE_FINDINGS_2026-06-09.md       [13 KB]
  ├── RLS_COMPLIANCE_INDEX.md                     [This file]
  └── adr/
      └── 0005-multi-tenant-rls.md                [Reference]

backend/scripts/
  ├── rls_compliance_audit.sh                     [13 KB, executable]
  └── RLS_AUDIT_SUMMARY.txt                       [9.0 KB]
```

---

## How to Review This Audit

**Step 1: Read Summary (5 min)**
```
Read: backend/scripts/RLS_AUDIT_SUMMARY.txt
Focus: Key findings, severity, timeline
```

**Step 2: Review Findings (30 min)**
```
Read: docs/RLS_COMPLIANCE_FINDINGS_2026-06-09.md
Focus: Vulnerability details, remediation code
Action: Approve/revise Phase 1 migration code
```

**Step 3: Plan Implementation (60 min)**
```
Read: docs/AUDIT_RLS_COMPLIANCE_2026-06-09.md
Focus: Implementation roadmap, 3 phases
Action: Schedule sprints, assign engineers
```

**Step 4: Execute Phase 1**
```
Assign: Senior backend engineer (2–3 hours)
Deliver: Migration 20260610_0001 + integration test
Timeline: This sprint
```

---

## Questions & Escalation

**Question:** Why is test_management_regression_set_cases using USING (TRUE)?

**Answer:** Developer prioritized flexibility for service layer to handle tenant isolation. However, this removes database-level protection and is fragile. Recommend fixing to restrictive policy (subquery).

---

**Question:** How critical is this really?

**Answer:** MEDIUM-HIGH but manageable. Current architecture has 3 layers:
1. RLS on parent tables (indirect protection)
2. Tenant context set per-request
3. Service layer knows about tenants

If ANY layer fails, cross-tenant data is exposed. Fix makes the system more resilient.

---

**Question:** Can this wait until next quarter?

**Answer:** No. The permissive policy is a known vulnerability. Fix it this sprint (2–3 hours). Phase 2 (next sprint) and Phase 3 (roadmap) can be deferred.

---

**Question:** What happens if we don't fix this?

**Answer:** 
- No immediate production impact (RLS on parent table protects)
- Refactoring risk: next developer might query directly
- Audit/compliance risk: auditors will flag USING (TRUE)
- Regression: any schema change could break isolation

**Recommendation:** Fix now (low cost, high confidence).

---

## Sign-off

- **Generated by:** RLS Compliance Scanner (automated)
- **Reviewed by:** [Pending]
- **Approved by:** [Pending]
- **Next review:** 2026-06-16 (after Phase 1 completion)

---

**Last updated:** 2026-06-09 11:16:14 UTC
