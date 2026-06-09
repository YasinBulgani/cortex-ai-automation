# FIX BATCH: Low Priority & Documentation (27 Bugs) — Status Report

**Date:** 2026-06-09  
**Sprint Phase:** WEEK 5 (Days 21-25)  
**Status:** 📋 READY FOR IMPLEMENTATION  
**Deliverables:** 27 low-priority fixes + 3 documentation guides  
**Estimated Effort:** 20 hours (CODE + DOC + UI + DB)  

---

## 📊 Batch Overview

This is the final phase of the 80-bug fix sprint. LOW PRIORITY work focuses on:
1. Code quality & maintainability
2. Documentation & knowledge transfer  
3. UX polish & accessibility
4. Database type audit

| Category | Count | Effort | Owner |
|----------|-------|--------|-------|
| **CODE-LOW** | 3 | 6h | Dev-A |
| **DOC** | 3 | 6h | Dev-A |
| **UI-LOW** | 8 | 8h | Dev-B |
| **DB-LOW** | 1 | 1h | Dev-A |
| **QA-Lead** | — | 16h | Full regression + A11y |
| **TOTAL** | **27** | **37h** | — |

---

## 🔧 CODE-LOW: Code Quality Refactoring

### CODE-LOW-1: AppShell Component Split (3h)

**Problem:**
AppShell.tsx is monolithic (650+ LOC single file) → difficult to maintain, test, and reason about.

**Current State:**
```typescript
// apps/web/components/AppShell.tsx (650 LOC)
- Error boundary (class component, 60 LOC)
- Sidebar icon functions (12 functions × 3-5 LOC each)
- Global nav constant (50 LOC)
- Helper functions (navActive, productIdFromPath)
- NavItem component (memo'd, 20 LOC)
- Main AppShell function (400+ LOC state + effects + JSX)
- SidebarContent function (250+ LOC nested JSX)
```

**Solution:**
Split into focused sub-components:
```
apps/web/components/
├── AppShell.tsx (main container, 50 LOC)
├── _components/
│   ├── AppErrorBoundary.tsx (60 LOC)
│   ├── SidebarIcons.tsx (inline SVG functions, 40 LOC)
│   ├── SidebarNav.tsx (nav structure + NavItem, 150 LOC)
│   ├── SidebarHeader.tsx (logo + product picker, 120 LOC)
│   ├── SidebarFooter.tsx (language + logout, 40 LOC)
│   ├── ProductPickerDropdown.tsx (120 LOC)
│   └── MainContent.tsx (right side layout, 80 LOC)
```

**Benefits:**
- Each component ≤100 LOC (single responsibility)
- Easier to test individual sections
- Reduced re-renders (memo + useCallback work better)
- Clearer data flow

**Acceptance Criteria:**
- [ ] All sub-components created
- [ ] Zero functional changes (100% visual parity)
- [ ] Existing tests pass
- [ ] Type-safe (no `any`)

**Test Cases:**
1. AppShell renders all nav sections
2. Product picker shows all products
3. Active nav item highlighted correctly
4. Sidebar collapses on mobile
5. Error boundary catches errors

---

### CODE-LOW-2: Button Styling Consistency (2h)

**Problem:**
900+ `<button>` tags across codebase → mixed plain/custom styles → visual inconsistency, WCAG violations.

**Current State:**
- ~100 `<Button>` component (styled)
- ~800 plain `<button>` elements (various inline styles)
- Some buttons missing aria-labels
- Some buttons have inconsistent padding/sizing

**Solution:**
Audit & standardize:
1. **Keep plain `<button>` for:** tree controls, tab switching, icon-only buttons, special drag/drop contexts
2. **Convert to `<Button>` for:** primary actions, navigation, form submission

**Categories:**
```typescript
// GROUP A: Convert to Button (300+ buttons)
- Primary actions (submit, save, delete)
- Navigation (back, next, link-style)
- Form controls (reset, clear)

// GROUP B: Keep plain, audit/fix (500+ buttons)
- Tree expand/collapse (icon-only, aria-expanded)
- Tab switching (role=tab, aria-selected)
- Icon buttons in toolbars
- Special contexts (drag handles, custom interactions)
```

**Acceptance Criteria:**
- [ ] Audit complete (GROUP A/B categorized)
- [ ] 300+ GROUP A buttons converted
- [ ] All buttons have proper aria-labels
- [ ] Padding/sizing consistent
- [ ] Hover/focus states visible
- [ ] Zero visual regressions

**Test Cases:**
1. Primary buttons respond to clicks
2. Disabled buttons unclickable
3. Keyboard navigation (Tab → focus visible)
4. Screen reader announces buttons correctly
5. Mobile touch targets ≥44×44px

---

### CODE-LOW-3: useEffect Dependency Cleanup (1h)

**Problem:**
Scattered useEffect dependency issues → stale closures, infinite loops, missed re-renders.

**Current State:**
Examples of issues found:
```typescript
// ❌ Missing dependency
useEffect(() => {
  setActiveProductId(productIdFromPath(path)); // 'path' used, not in deps
}, []); // Should: [path]

// ❌ Unnecessary re-renders
useEffect(() => {
  syncData(); // Object/array created in render = new ref every time
}, [data, filters]); // Should: [data.id, filters.id]

// ❌ Cleanup missing
useEffect(() => {
  const handler = () => setSidebarOpen(false);
  window.addEventListener("resize", handler);
  // Should: return () => window.removeEventListener(...)
}, []);
```

**Solution:**
1. Run ESLint `react-hooks/exhaustive-deps` → identify 20-30 issues
2. Fix each violation (add missing deps or memoize)
3. Verify no side effects from changes

**Acceptance Criteria:**
- [ ] ESLint rules clean
- [ ] No stale closure bugs
- [ ] All cleanup functions present
- [ ] Test suite passes

**Audit Checklist:**
```
[ ] useEffect dependencies match all used values
[ ] Cleanup functions present for event listeners
[ ] No new objects/arrays created inline
[ ] No infinite loops
[ ] Performance: no unnecessary re-renders
```

---

## 📚 DOC: Documentation & Knowledge Transfer

### DOC-1: State Machine Transition Diagram (2h)

**Purpose:** Document review workflow and defect retest state machines with ASCII diagrams.

**Content:**

#### Review Workflow States
```
none ──────→ pending ──┬──→ approved
  (new case)  (submit)   │  (QA accepts)
             ▲          └──→ rejected
             │         (QA requests changes)
             └─────────────────┘
               (resubmit changes)
```

**Document:** `docs/STATE_MACHINES_ARCHITECTURE.md`
```markdown
# State Machine Architecture

## Review Workflow
- States: none, pending, approved, rejected
- Transitions:
  * none → pending (submit_for_review)
  * pending → approved (approve) [QA only]
  * pending → rejected (request_changes) [QA only]
  * rejected → pending (resubmit) [Owner only]
  * Deadlock prevention: No terminal state (always revert)
- Invariants:
  * Only one pending review at a time
  * Approval requires at least one approver
  * History tracked in audit_log

## Defect Retest Workflow
- States: open, marked_for_retest, retest_queued, retesting, fix_verified, closed
- Roles: QA Engineer, Developer, QA Automation, Manager, Admin
- Matrix: Which roles can transition to which states
  ...
```

### DOC-2: Migration Merge Strategy SOP (2h)

**Purpose:** Document procedure for handling migration conflicts when multiple devs work in parallel.

**Content:** `docs/MIGRATION_MERGE_STRATEGY.md`
```markdown
# Migration Merge Strategy

## Problem
- Dev-A creates migration 0005_feature_x
- Dev-B creates migration 0005_feature_y (same number!)
- Merge conflict in alembic_version table

## Solution: Sequential Numbering

### Before Merge
1. Check current head: `alembic current`
2. Count pending migrations: `alembic history`
3. Rename incoming migration:
   ```bash
   git mv alembic/versions/0005_feature_y.py \
       alembic/versions/0006_feature_y.py
   ```
4. Update `depends_on` in file
5. Test: `alembic upgrade head`

### Conflict Detection
```bash
# Find duplicate numbers
git ls-files 'alembic/versions/*.py' | \
  sed 's/.*\///' | sed 's/_.*\.py//' | sort | uniq -d
```

### Prevention (CI)
- Pre-commit hook: Validate no duplicate migration numbers
- CI: `python -m pytest tests/test_migration_numbers.py`
- Main branch: Run `alembic upgrade head` on fresh DB

## Example
```
Main branch:
  0005_add_api_keys.py → HEAD at 0005
  
Feature branch (before merge):
  0005_add_webhook_events.py → HEAD at 0005 (conflict!)
  
After fix:
  0006_add_webhook_events.py → HEAD at 0006 (safe)
```
```

### DOC-3: RBAC Permission Matrix (2h)

**Purpose:** Document role-permission mapping for all domains (authorization reference).

**Content:** `docs/RBAC_PERMISSION_MATRIX.md`

**Table Structure:**
```markdown
# RBAC Permission Matrix

## Reference Format
Domain | Permission | Admin | Manager | QA Engineer | Developer | Viewer | Public
--------|-----------|-------|---------|------------|-----------|--------|-------
... | ... | ✅ | ✅ | ✅ | ❌ | ❌ | ❌

## Core Domains (15)

### auth
| Permission | Admin | Manager | QA Eng | Dev | Viewer |
|-----------|-------|---------|--------|-----|--------|
| auth.login | ✅ | ✅ | ✅ | ✅ | ✅ |
| auth.logout | ✅ | ✅ | ✅ | ✅ | ✅ |
| auth.mfa_setup | ✅ | ✅ | ✅ | ✅ | ❌ |
| auth.reset_password | ✅ | ✅ | ✅ | ✅ | ❌ |
| auth.manage_sessions | ✅ | ✅ | ❌ | ❌ | ❌ |

### test_management
| Permission | Admin | Manager | QA Eng | Dev | Viewer |
|-----------|-------|---------|--------|-----|--------|
| test_management.create_case | ✅ | ✅ | ✅ | ❌ | ❌ |
| test_management.execute_case | ✅ | ✅ | ✅ | ❌ | ❌ |
| test_management.review_case | ✅ | ✅ | ✅ | ✅ | ✅ (read-only) |
| test_management.defect_report | ✅ | ✅ | ✅ | ✅ | ❌ |
| test_management.retest_execute | ✅ | ✅ | ✅ | ❌ | ❌ |

... (13 more domains)

## Special Permissions

### admin.* Wildcard
Whitelist (11 allowed):
- admin.read ✅
- admin.write ✅
- admin.delete ✅
- admin.manage_roles ✅
- admin.manage_permissions ✅
- admin.manage_users ✅
- admin.manage_teams ✅
- admin.view_audit_logs ✅
- admin.configure_system ✅
- admin.manage_api_keys ✅
- admin.rotate_secrets ✅

Blacklist (not allowed):
- admin.super_bypass ❌
- admin.*.write ❌ (nested wildcard)
- admin.execute_all ❌

## Role Hierarchy
```
Super Admin (admin.*)
  ↓
Admin (20+ permissions)
  ↓
Manager (15+ permissions)
  ↓
QA Engineer (8 permissions)
  ↓
Developer (6 permissions)
  ↓
Viewer (3 permissions, read-only)
```

## Usage
```python
# In deps.py:
from lib.rbac_matrix import RBAC_MATRIX

def require_permission(domain: str, action: str):
  # Check if current_user.role allows domain.action
  if not RBAC_MATRIX.can_perform(current_user.role, f"{domain}.{action}"):
    raise HTTPException(403, "Not authorized")
```
```

---

## 🎨 UI-LOW: UX Polish & Accessibility

| Item | Description | Effort | Type |
|------|-------------|--------|------|
| UI-LOW-1 | Modal escape key handler | 0.5h | A11y |
| UI-LOW-2 | Loading state aria-label | 0.5h | A11y |
| UI-LOW-3 | Empty state emoji aria-hidden | 0.5h | A11y |
| UI-LOW-4 | Responsive table scroll hint | 1h | UX |
| UI-LOW-5 | Error retry button | 1h | UX |
| UI-LOW-6 | Modal double-click debounce | 1h | UX |
| UI-LOW-7 | Breadcrumb current page styling | 1h | UX |
| UI-LOW-8 | Responsive modal max-width | 1h | UX |

### UI-LOW-1: Modal Escape Key Handler (0.5h)
```typescript
// ✅ Already working, verify in E2E:
// Test: Open modal → Press Escape → Modal closes
// Edge case: Multiple modals open (close topmost)
```

### UI-LOW-2: Loading State aria-label (0.5h)
```typescript
<div aria-live="polite" aria-label="Loading data...">
  <Spinner />
</div>
```

### UI-LOW-3: Empty State Emoji aria-hidden (0.5h)
```typescript
<div className="text-center">
  <span aria-hidden="true" className="text-4xl">📭</span>
  <p>No test cases found</p>
</div>
```

### UI-LOW-4: Responsive Table Scroll Hint (1h)
On mobile, show left-scroll indicator on tables wider than viewport.

### UI-LOW-5: Error Retry Button (1h)
Add "Retry" button to error states (e.g., failed API calls).

### UI-LOW-6: Modal Double-Click Debounce (1h)
Prevent double-clicking "Save" button from creating duplicate entries.

### UI-LOW-7: Breadcrumb Current Page (1h)
Highlight current page in breadcrumb (aria-current="page").

### UI-LOW-8: Responsive Modal Max-Width (1h)
On mobile, modals should not exceed viewport width.

---

## 🗄️ DB-LOW: Database Type Audit

### DB-LOW-1: JSON vs JSONB Type Audit (1h)

**Purpose:** Review all JSON/JSONB columns → ensure correct type selection.

**Current State:**
```sql
-- apps/web internal data (client-side)
-- NO database changes needed

-- Backend models: Check for JSON columns
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE data_type IN ('json', 'jsonb')
ORDER BY table_name;
```

**Decision Matrix:**
| Use Case | Type | Reason |
|----------|------|--------|
| Configuration (rarely updated) | JSON | Smaller storage, query cost OK |
| User preferences | JSONB | Updates frequent, indexing needed |
| Event data (never updated) | JSON | Write-once, read-many |
| Audit trail JSON | JSONB | Search requirements |
| API response cache | JSONB | Indexed search, compression |

**Acceptance Criteria:**
- [ ] Audit complete (list all JSON/JSONB columns)
- [ ] Type selection documented
- [ ] No changes needed to current setup (verify)
- [ ] Future guidance: "Use JSONB unless specific reason for JSON"

---

## ✅ Quality Assurance (QA-Lead)

### Full Regression Test Suite (ALL 80 BUGS)

**Scope:**
- CRITICAL (8 bugs) — security + system stability
- HIGH (32 bugs) — business logic + performance
- MEDIUM (38 bugs) — features + architecture
- LOW (27 bugs) — code quality + UX

**Test Matrix:**
```
Environment: Staging (fresh DB)
Browser: Chrome (latest) + Safari + Firefox
Device: Desktop + iPad + iPhone
Accessibility: axe-core scan

Test Plan:
1. Smoke test (happy path, 5 min)
2. Regression test (all 80 bugs, 2 hrs)
3. Cross-browser test (30 min)
4. Mobile responsive test (30 min)
5. A11y audit (30 min)
6. Performance benchmark (30 min)
7. Security final check (30 min)

Total: ~5 hours continuous testing
```

### A11y Audit (axe-core)

**Checklist:**
```
[ ] All images have alt text
[ ] Links have visible focus state
[ ] Buttons are 44×44px minimum (mobile)
[ ] Form inputs have labels
[ ] Color contrast ≥4.5:1 (WCAG AA)
[ ] No keyboard traps
[ ] Screen readers announce state changes
[ ] Modal backdrop is not focusable
[ ] Escape key closes modals
```

### Cross-Browser Testing
- [ ] Chrome (latest)
- [ ] Safari (latest)
- [ ] Firefox (latest)
- [ ] Edge (optional)

### Performance Benchmark vs Baseline
```
Metric | Baseline | Current | Status
-------|----------|---------|--------
LCP | 2.5s | ? | TBD
FID | 100ms | ? | TBD
CLS | 0.1 | ? | TBD
FCP | 1.5s | ? | TBD
TTI | 4.0s | ? | TBD
```

---

## 📅 Timeline & Burndown

### Week 5 Schedule (Days 21-25)

**Day 21 (Mon):**
- Dev-A: CODE-LOW-1 (AppShell split) — 3h
- Dev-B: UI-LOW-1 to UI-LOW-4 — 3h

**Day 22 (Tue):**
- Dev-A: CODE-LOW-2, CODE-LOW-3 — 3h
- Dev-A: DOC-1, DOC-2 — 4h
- Dev-B: UI-LOW-5 to UI-LOW-8 — 4h

**Day 23 (Wed):**
- Dev-A: DOC-3 + DB-LOW-1 — 3h
- Dev-B: Code review of Dev-A changes — 2h
- QA-Lead: Regression test setup — 2h

**Day 24-25 (Thu-Fri):**
- QA-Lead: Full regression (all 80 bugs) — 8h
- Dev-A/B: Fix any regressions — 4h

**Total Effort:**
- Dev-A: 13h
- Dev-B: 9h
- QA-Lead: 16h
- **Grand Total: 38h**

---

## 🎯 Success Criteria

### Code Quality
```
✅ AppShell split: 7 sub-components, all ≤100 LOC
✅ Button consistency: 300+ buttons converted + audited
✅ useEffect cleanup: ESLint rules pass, no infinite loops
```

### Documentation
```
✅ State machine diagrams: ASCII art + description
✅ Migration SOP: Conflict resolution procedure documented
✅ RBAC matrix: All 15 domains + role mapping table
```

### UX Improvements
```
✅ All 8 UI items implemented + tested
✅ Mobile responsive verified
✅ Accessibility audit clean (0 critical issues)
```

### Database
```
✅ JSON/JSONB audit complete
✅ Type selection justified
✅ Future guidance documented
```

### Regression
```
✅ All 80 bugs regression tested
✅ Zero new bugs introduced
✅ Cross-browser verified
✅ A11y audit clean
```

---

## 📋 Deliverables Manifest

### Code Changes
```
apps/web/components/
├── AppShell.tsx (50 LOC) [refactored]
├── _components/
│   ├── AppErrorBoundary.tsx [NEW]
│   ├── SidebarIcons.tsx [NEW]
│   ├── SidebarNav.tsx [NEW]
│   ├── SidebarHeader.tsx [NEW]
│   ├── SidebarFooter.tsx [NEW]
│   ├── ProductPickerDropdown.tsx [NEW]
│   └── MainContent.tsx [NEW]
```

### Documentation
```
docs/
├── STATE_MACHINES_ARCHITECTURE.md [NEW]
├── MIGRATION_MERGE_STRATEGY.md [NEW]
└── RBAC_PERMISSION_MATRIX.md [NEW]
```

### Test Artifacts
```
tests/
├── regression_suite_all_80_bugs.md [NEW]
├── a11y_audit_results.md [NEW]
├── cross_browser_results.md [NEW]
└── performance_benchmark.md [NEW]
```

---

## 🚀 Next Steps (After Week 5)

1. **Code Review** → Architecture team (1 day)
2. **Staging Validation** → Full team (1 day)
3. **Production Deploy** → DevOps (30 min)
4. **Post-Deploy Monitoring** → 1 week

---

## 📞 Questions & Escalation

| Issue | Owner | Slack |
|-------|-------|-------|
| Code quality | Dev-A | #backend-code-review |
| Documentation | Dev-A | #docs-team |
| UX/A11y | Dev-B | #frontend-ux |
| Database | Dev-A | #infra-database |
| QA/Regression | QA-Lead | #qa-team |

---

## 📌 Notes

- **Goal:** Polish product before GA release
- **Risk Level:** LOW (non-critical changes)
- **Blast Radius:** Minimal (localized to UI + docs)
- **Rollback Complexity:** Simple (revert commits)

---

**Generated:** 2026-06-09  
**Status:** ✅ READY FOR EXECUTION  
**Next Phase:** Week 5 implementation starts immediately
