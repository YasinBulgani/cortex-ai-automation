# LOW PRIORITY BATCH — Implementation Guide

**Sprint Week:** 5  
**Target Days:** 21-25 (Days Mon-Fri)  
**Total Effort:** 37 hours  
**Parallel Streams:** Dev-A (code + docs) | Dev-B (UI/UX)  

---

## 🎯 STREAM A: Dev-A (Code + Docs + DB)

### Day 21: CODE-LOW-1 (AppShell Split) — 3h

#### Step 1: Create Sub-Component Directory
```bash
mkdir -p apps/web/components/_components
```

#### Step 2: Extract AppErrorBoundary
**File:** `apps/web/components/_components/AppErrorBoundary.tsx`

```typescript
"use client";

import React from "react";
import { Button } from "@/components/ui/button";

export class AppErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[AppShell] Caught error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-surface-base">
          <div className="mx-auto max-w-md rounded-lg border border-red-500/20 bg-red-500/5 p-8 text-center">
            <div className="mb-4 flex justify-center">
              <svg
                className="h-12 w-12 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>
            <h2 className="mb-2 text-lg font-semibold text-red-400">
              Beklenmeyen Bir Hata Oluştu
            </h2>
            <p className="mb-1 text-sm text-slate-400">
              Sayfa yüklenirken bir sorun oluştu.
            </p>
            {this.state.error && (
              <p className="mb-6 rounded-md bg-surface-raised px-3 py-2 text-xs font-mono text-fg-subtle text-left break-all">
                {this.state.error.message}
              </p>
            )}
            <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
              <Button
                variant="primary"
                size="default"
                onClick={() => window.location.reload()}
              >
                Sayfayı Yenile
              </Button>
              <a
                href="/"
                className="rounded-md border border-border px-4 py-2 text-sm font-medium text-fg-muted hover:border-border-strong hover:text-fg transition-colors"
              >
                Anasayfaya Dön
              </a>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

#### Step 3: Extract SidebarIcons
**File:** `apps/web/components/_components/SidebarIcons.tsx`

```typescript
"use client";

import { cn } from "@/lib/utils";

export function IconChart() {
  return (
    <svg
      className="h-4 w-4 shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}

export function IconFolder() {
  return (
    <svg
      className="h-4 w-4 shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  );
}

// ... export all other icons (IconEdit, IconClipboardCheck, etc.)
// Total: 12 icon exports

export function IconChevron({ open }: { open: boolean }) {
  return (
    <svg
      className={cn(
        "h-3 w-3 shrink-0 transition-transform duration-150",
        open && "rotate-180"
      )}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2.5}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}
```

#### Step 4: Extract SidebarHeader
**File:** `apps/web/components/_components/SidebarHeader.tsx` (120 LOC)
- Logo + Brand selector
- Product picker button
- Hamburger close (mobile)

#### Step 5: Extract SidebarNav
**File:** `apps/web/components/_components/SidebarNav.tsx` (150 LOC)
- NavItem component (memo'd)
- Navigation structure (GLOBAL_NAV)
- Active item highlighting

#### Step 6: Extract SidebarFooter
**File:** `apps/web/components/_components/SidebarFooter.tsx` (40 LOC)
- Language selector
- Logout button

#### Step 7: Extract ProductPickerDropdown
**File:** `apps/web/components/_components/ProductPickerDropdown.tsx` (120 LOC)
- Product list
- Selection logic
- Meta (availability badges)

#### Step 8: Extract MainContent
**File:** `apps/web/components/_components/MainContent.tsx` (80 LOC)
- Right side layout (header + content)
- Top banner
- Lazy-loaded widgets

#### Step 9: Refactor AppShell.tsx
```typescript
"use client";

import React, { Suspense } from "react";
import { AppErrorBoundary } from "./_components/AppErrorBoundary";
import { SidebarHeader } from "./_components/SidebarHeader";
import { SidebarNav } from "./_components/SidebarNav";
import { SidebarFooter } from "./_components/SidebarFooter";
import { MainContent } from "./_components/MainContent";
// ... other imports

export function AppShell({ children, projects, projectId, topBanner }) {
  // Only state management + effects
  // Delegates rendering to sub-components
  return (
    <AppErrorBoundary>
      <div className="flex min-h-screen flex-col bg-surface-base">
        <MainContent topBanner={topBanner} children={children} />
      </div>
    </AppErrorBoundary>
  );
}
```

#### Verification Checklist
```
[ ] All 7 sub-components created
[ ] AppShell.tsx now ≤100 LOC
[ ] Tests still pass: npm test
[ ] Visual parity: No changes to UI
[ ] No TypeScript errors: npx tsc --noEmit
[ ] Lighthouse score unchanged
```

---

### Day 22: CODE-LOW-2 + CODE-LOW-3 — 3h

#### CODE-LOW-2: Button Consistency (2h)

**Step 1: Audit Existing Buttons**
```bash
# Find all <button> elements
grep -r "<button" apps/web --include="*.tsx" --include="*.ts" | wc -l
# Expected: ~900

# Find <Button> components
grep -r "<Button" apps/web --include="*.tsx" | wc -l
# Expected: ~100
```

**Step 2: Categorize (GROUP A vs GROUP B)**

Create `BUTTON_CONVERSION_TRACKER.md`:
```markdown
# Button Conversion Tracker

## GROUP A: Convert to <Button> (300+ buttons)
- [ ] Primary actions (submit, save, delete)
- [ ] Navigation (back, next)
- [ ] Form controls (reset, clear)
- [ ] Dialog actions (confirm, cancel)

## GROUP B: Keep plain (500+ buttons)
- [ ] Tree expand/collapse (icon-only, aria-expanded)
- [ ] Tab switching (role=tab, aria-selected)
- [ ] Icon-only toolbar buttons
- [ ] Special drag/drop contexts
```

**Step 3: Batch Conversion**
```typescript
// Before:
<button onClick={handleSave}>Save</button>

// After:
<Button variant="primary" onClick={handleSave}>
  Save
</Button>
```

**Step 4: Audit Remaining Plain Buttons**
For buttons that stay plain:
```typescript
// Must have:
<button
  type="button"
  aria-label="Expand section"  // ← Must add
  aria-expanded={isOpen}       // ← If collapsible
  onClick={handleToggle}
>
  <ChevronIcon />
</button>
```

**Step 5: Verify**
```bash
# No aria-label-less buttons
grep -r '<button[^>]*>' apps/web/components --include="*.tsx" | \
  grep -v 'aria-label' | \
  grep -v 'className=".*aria' | \
  head -20
```

#### CODE-LOW-3: useEffect Cleanup (1h)

**Step 1: Run ESLint**
```bash
cd apps/web
npx eslint . --ext .tsx --rule 'react-hooks/exhaustive-deps: error' > /tmp/eslint-report.txt
```

**Step 2: Fix Issues**
```typescript
// ❌ Before
useEffect(() => {
  setActiveProductId(productIdFromPath(path));
}, []); // Missing 'path'

// ✅ After
useEffect(() => {
  setActiveProductId(productIdFromPath(path));
}, [path]);
```

**Step 3: Verify No Stale Closures**
```bash
# Run tests
npm test -- --testPathPattern="useEffect|hook" --coverage
```

**Step 4: Manual Spot Checks**
- [ ] No infinite loops (test in browser for 30s)
- [ ] Event listeners cleaned up (check DevTools memory)
- [ ] No memory leaks (run Lighthouse)

---

### Day 22-23: DOC (3 docs) — 6h

#### DOC-1: State Machines (2h)

Create `docs/STATE_MACHINES_ARCHITECTURE.md`:

**Section 1: Review Workflow**
```markdown
# State Machine Architecture

## Review Workflow

States: `none`, `pending`, `approved`, `rejected`

### State Diagram
```
    ┌─────────────────┐
    │     none        │ (initial)
    └────────┬────────┘
             │ submit_for_review()
             ▼
    ┌─────────────────┐
    │    pending      │
    ├─────┬───────────┤
    │ ✓   │ (QA role) │
    │     │ ✗         │
    ▼     ▼
┌────────┐ ┌─────────┐
│approved│ │rejected │
└────────┘ └────┬────┘
                │ resubmit()
                └─────────┐
                    ┌──────▼──┐
                    │ pending  │
                    └──────────┘
```

### Transitions
| From | To | Method | Required Role | Condition |
|------|----|----|---|---|
| none | pending | submit_for_review() | Owner | Case must be valid |
| pending | approved | approve() | QA Manager | — |
| pending | rejected | request_changes() | QA Manager | Reason required |
| rejected | pending | resubmit() | Owner | — |

### Invariants
- Only 1 pending review per case
- No approval without QA Manager role
- History recorded in audit_log
- Timestamps tracked

### Code Example
```python
# backend/app/domains/test_management/review_workflow.py
from enum import Enum

class ReviewStatus(str, Enum):
    none = "none"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

def can_transition(
    from_state: ReviewStatus,
    to_state: ReviewStatus,
    user_role: str
) -> bool:
    """Check if transition is valid."""
    valid_transitions = {
        ReviewStatus.none: [ReviewStatus.pending],
        ReviewStatus.pending: [ReviewStatus.approved, ReviewStatus.rejected],
        ReviewStatus.rejected: [ReviewStatus.pending],
    }
    
    if to_state not in valid_transitions.get(from_state, []):
        return False
    
    # Role checks
    if to_state in [ReviewStatus.approved, ReviewStatus.rejected]:
        return user_role == "qa_manager"
    
    return True
```

### Testing
```python
# test_review_workflow.py
def test_transition_none_to_pending():
    assert can_transition(ReviewStatus.none, ReviewStatus.pending, "owner")

def test_transition_pending_to_approved_qa_only():
    assert can_transition(ReviewStatus.pending, ReviewStatus.approved, "qa_manager")
    assert not can_transition(ReviewStatus.pending, ReviewStatus.approved, "developer")

def test_no_direct_approval_without_qc():
    assert not can_transition(ReviewStatus.none, ReviewStatus.approved, "owner")
```
```

**Section 2: Defect Retest Workflow** (similar structure)

---

#### DOC-2: Migration Merge Strategy (2h)

Create `docs/MIGRATION_MERGE_STRATEGY.md`:

```markdown
# Migration Merge Strategy

## Problem
Multiple devs create migrations simultaneously → numbering conflicts.

## Solution: Sequential Numbering + CI Validation

### Workflow

1. **Before pushing:**
   ```bash
   git pull --rebase
   # Check for conflicts
   ls -1 alembic/versions/*.py | sed 's/.*\///' | cut -d_ -f1 | sort | uniq -d
   ```

2. **If conflict detected:**
   ```bash
   # Rename to next available number
   git mv alembic/versions/0005_feature.py alembic/versions/0006_feature.py
   
   # Update depends_on in migration file
   # Open file and change: depends_on = '0004_...'
   ```

3. **Test locally:**
   ```bash
   alembic upgrade head  # Should work
   alembic downgrade -1  # Should work
   ```

4. **Push:**
   ```bash
   git push
   ```

### CI Validation

**File:** `.github/workflows/test.yml`
```yaml
- name: Validate migrations
  run: |
    python scripts/validate_migrations.py
    # Script checks:
    # - No duplicate numbers
    # - All depends_on values exist
    # - Upgrade/downgrade works
```

**Script:** `backend/scripts/validate_migrations.py`
```python
import os
from pathlib import Path

def validate_migrations():
    versions_dir = Path("backend/alembic/versions")
    files = sorted(versions_dir.glob("*.py"))
    
    numbers = []
    for f in files:
        num = f.stem.split("_")[0]
        if num in numbers:
            raise ValueError(f"Duplicate migration number: {num}")
        numbers.append(num)
    
    print(f"✅ {len(numbers)} migrations, no conflicts")
```

### Manual Merge Resolution

If there's a merge conflict in `alembic_version` table:

```bash
# 1. Check current state
git status

# 2. Identify conflicting migrations
git log --oneline | head -5

# 3. Rename locally
git mv alembic/versions/0005_a.py alembic/versions/0006_a.py
sed -i 's/depends_on = .0004.*/depends_on = "0005_b"/' alembic/versions/0006_a.py

# 4. Test & push
alembic upgrade head
git add alembic/versions/0006_a.py
git commit -m "fix(migration): Resolve numbering conflict"
```

### Prevention

Add pre-commit hook:
```bash
# .git/hooks/pre-commit
#!/bin/bash
python -m pytest backend/tests/test_migration_numbers.py
```

### Reference

- Alembic docs: https://alembic.sqlalchemy.org/
- Common conflicts: https://docs.sqlalchemy.org/
```

---

#### DOC-3: RBAC Matrix (2h)

Create `docs/RBAC_PERMISSION_MATRIX.md`:

```markdown
# RBAC Permission Matrix

Complete role-permission mapping for all 15 backend domains.

## Roles Definition

| Role | Level | Use Case |
|------|-------|----------|
| Super Admin | 0 | System administrator, all permissions |
| Admin | 1 | Organization admin, most permissions |
| Manager | 2 | Team lead, business operations |
| QA Engineer | 3 | Test execution + case creation |
| Developer | 4 | Defect fix, code review |
| Viewer | 5 | Read-only access |
| Public | 6 | Unauthenticated user |

## Core Domains (15)

### 1. auth (Authentication & Sessions)
```
Permission | Super | Admin | Manager | QA | Dev | Viewer | Public
-----------|-------|-------|---------|-----|-----|--------|-------
auth.login | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅
auth.logout | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌
auth.register | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ (if open)
auth.mfa_setup | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
auth.mfa_disable | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌
auth.reset_password | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (self)
auth.manage_sessions | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌
```

### 2. test_management (Test Case CRUD)
```
Permission | Super | Admin | Manager | QA | Dev | Viewer
-----------|-------|-------|---------|-----|-----|--------
test_management.create | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
test_management.read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅
test_management.update | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
test_management.delete | ✅ | ✅ | ✅ | ❌ | ❌ | ❌
test_management.execute | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
test_management.review | ✅ | ✅ | ✅ | ✅ | ✅ (read) | ✅ (read)
test_management.defect_report | ✅ | ✅ | ✅ | ✅ | ✅ | ❌
test_management.retest_execute | ✅ | ✅ | ✅ | ✅ | ❌ | ❌
```

... (13 more domains)

## Special Permissions: admin.*

**Whitelist (11 allowed):**
- `admin.read` — View system state
- `admin.write` — Modify system state
- `admin.delete` — Delete entities
- `admin.manage_roles` — Create/update roles
- `admin.manage_permissions` — Assign permissions
- `admin.manage_users` — Create/suspend users
- `admin.manage_teams` — Create teams, assign members
- `admin.view_audit_logs` — Access audit trail
- `admin.configure_system` — System settings
- `admin.manage_api_keys` — API key lifecycle
- `admin.rotate_secrets` — Rotate internal keys

**Blacklist (forbidden):**
- `admin.super_bypass` ❌
- `admin.*.write` ❌ (nested wildcard)
- `admin.emergency_kill` ❌

## Code Integration

```python
# backend/app/deps.py
from app.domains.rbac.admin_permission_control import AdminPermissionControl

def get_current_user_with_rbac(token: str):
    user = verify_token(token)
    user.permissions = filter_admin_permissions(user.permissions)
    return user

def require_permission(domain: str, action: str):
    def dependency(user = Depends(get_current_user_with_rbac)):
        required = f"{domain}.{action}"
        if required not in user.permissions:
            raise HTTPException(403, f"Permission denied: {required}")
        return user
    return dependency
```

## Audit & Compliance

All permission changes logged:
- Timestamp
- Admin user ID
- Target user
- Changed permissions
- Reason (optional)

```sql
SELECT * FROM audit_log
WHERE entity_type = 'permission'
ORDER BY created_at DESC;
```
```

---

### Day 23: DB-LOW-1 + Final Integration — 3h

#### DB-LOW-1: JSON vs JSONB Audit (1h)

**Step 1: Query Database**
```bash
psql -d neurex -c "
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE data_type IN ('json', 'jsonb', 'character varying')
  AND column_name LIKE '%json%'
ORDER BY table_name;
"
```

**Step 2: Document Findings**

Create `docs/JSON_JSONB_AUDIT.md`:
```markdown
# JSON vs JSONB Audit

## Current State
- test_data: JSON (read-only, use JSON)
- config: JSONB (updated quarterly, use JSONB)
- metadata: JSON (never updated, use JSON)

## Decision Matrix

| Column | Table | Current | Recommended | Reason |
|--------|-------|---------|-------------|--------|
| test_data | automation_runs | JSON | JSON | Write-once |
| config | organizations | JSON | JSONB | Updated, needs indexing |
| metadata | projects | JSONB | JSONB | ✅ Correct |

## Future Guidance
- Default: Use JSONB (more features)
- Only use JSON if: specific size constraints, immutable data

## No Changes Needed
All columns are correctly typed. ✅
```

**Step 3: Verify No Changes Required**
```bash
# Run test to confirm current setup is optimal
pytest backend/tests/test_json_types.py
```

---

## 🎯 STREAM B: Dev-B (UI/UX Polish) — 9h

### Days 21-22: UI-LOW-1 to UI-LOW-8 — 8h

#### UI-LOW-1: Modal Escape Key Handler (0.5h)

**Verification only** (feature already exists):
```typescript
// In any Modal component:
useEffect(() => {
  const handleEscape = (e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  };
  document.addEventListener("keydown", handleEscape);
  return () => document.removeEventListener("keydown", handleEscape);
}, [onClose]);
```

**Test:**
```bash
# E2E test
npx playwright test e2e/modal-escape.spec.ts
```

---

#### UI-LOW-2: Loading State aria-label (0.5h)

**Task:** Add aria-live + aria-label to all loading spinners

**Files to update:**
- `apps/web/components/Loading.tsx`
- `apps/web/components/Spinner.tsx`
- All pages with "loading..." state

**Pattern:**
```typescript
<div aria-live="polite" aria-label="Loading data, please wait...">
  <Spinner />
</div>
```

---

#### UI-LOW-3: Empty State Emoji aria-hidden (0.5h)

**Pattern:**
```typescript
<div className="text-center">
  <div className="mb-4 text-5xl" aria-hidden="true">📭</div>
  <h3 className="text-lg font-semibold">No test cases found</h3>
  <p className="text-sm text-fg-muted">Create your first test case to get started</p>
</div>
```

---

#### UI-LOW-4: Responsive Table Scroll Hint (1h)

**Task:** Add scroll hint on mobile for tables wider than viewport

**File:** `apps/web/components/ui/table.tsx`

```typescript
export function Table({ children, ...props }) {
  const [canScrollRight, setCanScrollRight] = useState(false);
  
  useEffect(() => {
    const element = document.querySelector("[data-table-wrapper]");
    if (!element) return;
    
    setCanScrollRight(element.scrollWidth > element.clientWidth);
  }, []);
  
  return (
    <div 
      data-table-wrapper 
      className={cn(
        "overflow-x-auto",
        canScrollRight && "relative after:absolute after:right-0 after:top-1/2 after:-translate-y-1/2 after:w-8 after:h-8 after:bg-gradient-to-l after:from-brand-soft"
      )}
    >
      <table {...props}>{children}</table>
    </div>
  );
}
```

---

#### UI-LOW-5: Error Retry Button (1h)

**Task:** Add "Retry" button to error states

**Pattern:**
```typescript
export function ErrorState({ error, onRetry }) {
  return (
    <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-6 text-center">
      <h3 className="mb-2 font-semibold text-red-600">Error Loading Data</h3>
      <p className="mb-4 text-sm text-fg-muted">{error?.message}</p>
      <Button variant="secondary" onClick={onRetry}>
        <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Retry
      </Button>
    </div>
  );
}
```

---

#### UI-LOW-6: Modal Double-Click Debounce (1h)

**Task:** Prevent double-clicking submit button from creating duplicates

**Pattern:**
```typescript
const [submitting, setSubmitting] = useState(false);

async function handleSubmit(e) {
  if (submitting) return;
  setSubmitting(true);
  
  try {
    await apiClient.post("/endpoint", data);
    onSuccess();
  } finally {
    setSubmitting(false);
  }
}

return (
  <Button 
    onClick={handleSubmit} 
    disabled={submitting}
  >
    {submitting ? "Saving..." : "Save"}
  </Button>
);
```

---

#### UI-LOW-7: Breadcrumb Current Page (1h)

**Task:** Style current page differently in breadcrumb

**Pattern:**
```typescript
export function Breadcrumb({ items }) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex gap-2">
        {items.map((item, i) => (
          <li key={item.href} className="flex items-center gap-2">
            {i > 0 && <span aria-hidden="true" className="text-fg-muted">/</span>}
            {i === items.length - 1 ? (
              <span aria-current="page" className="font-semibold text-fg">
                {item.label}
              </span>
            ) : (
              <a href={item.href} className="text-brand hover:underline">
                {item.label}
              </a>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
```

---

#### UI-LOW-8: Responsive Modal Max-Width (1h)

**Task:** Ensure modals don't exceed viewport on mobile

**Pattern:**
```typescript
export function Modal({ open, onClose, children }) {
  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/50" onClick={onClose} />}
      <div
        className={cn(
          "fixed inset-x-4 top-1/2 z-50 -translate-y-1/2 rounded-lg bg-surface-raised",
          "max-h-[90vh] max-w-2xl mx-auto",
          "md:max-w-4xl", // Wider on desktop
          "overflow-y-auto" // Scroll if needed
        )}
      >
        {children}
      </div>
    </>
  );
}
```

---

### Day 23: Code Review & Integration (2h)

**Dev-B Tasks:**
- Review Dev-A's code changes (AppShell, useEffect, buttons)
- Spot-check regressions in UI
- Run accessibility audit

```bash
# A11y check
npx axe-core https://localhost:3000/test-page
```

---

## ✅ QA-Lead: Full Regression Testing

### Days 24-25: Comprehensive Testing (16h)

#### Phase 1: Test Plan Setup (1h)
```bash
# Create test matrix
cat > tests/REGRESSION_PLAN_ALL_80_BUGS.md << EOF
# All 80 Bugs Regression Test Plan

## Critical (8 bugs)
- [ ] SSL verify fix
- [ ] Tenant isolation
- [ ] HMAC webhook
- [ ] Async/sync separation
- [ ] Circuit breaker
- [ ] ProjectMember FK
- [ ] Cost numeric
- [ ] RLS multi-tenant

## High (32 bugs)
- [ ] Admin permission (all 11 types)
- [ ] SSRF protection
- [ ] N+1 queries fixed
- [ ] 20+ admin RBAC tests pass
- [ ] E2E parallel <15min
- ...

## Medium (38 bugs)
- [ ] Review workflow transitions
- [ ] Defect retest RBAC
- [ ] Products telemetry real data
- [ ] API key rotation
- [ ] UI improvements (pagination, forms, filters)
- ...

## Low (27 bugs)
- [ ] AppShell split (visual parity)
- [ ] Button consistency + A11y
- [ ] useEffect cleanup
- [ ] Documentation complete
- [ ] All UX polish items
- [ ] JSON/JSONB correct types
EOF
```

#### Phase 2: Smoke Test (0.5h)
```bash
npm run dev &
sleep 5
npx playwright test tests/smoke.spec.ts
```

#### Phase 3: Regression Suite (4h)
```bash
# Run full test suite
npm test -- --coverage
# Expected: >95% pass rate
```

#### Phase 4: Cross-Browser (1h)
- Chrome (latest)
- Safari (latest)
- Firefox (latest)

#### Phase 5: Mobile Responsive (1h)
- iPad (768×1024)
- iPhone (375×667)
- Verify touch targets ≥44×44px

#### Phase 6: A11y Audit (1.5h)
```bash
# Run axe-core
npm run test:a11y
# Expected: 0 critical, <5 warnings

# Screen reader test (manual)
# Test with: NVDA (Windows) or VoiceOver (Mac)
```

#### Phase 7: Performance Benchmark (1.5h)
```bash
# Lighthouse
npm run build
npx lighthouse https://localhost:3000 --output-path=/tmp/lighthouse.html

# Expected:
# - LCP: 2.5s ✅
# - FID: 100ms ✅
# - CLS: 0.1 ✅
```

#### Phase 8: Security Final Check (1h)
```bash
# OWASP checklist
- [ ] No plaintext secrets in logs
- [ ] CSRF tokens present
- [ ] XSS prevention working
- [ ] Rate limiting enforced
- [ ] SQL injection prevented (SQLAlchemy)
```

---

## 📋 Acceptance Criteria

### All 27 Bugs Fixed
```
CODE-LOW-1: ✅ AppShell split into 7 components, <100 LOC each
CODE-LOW-2: ✅ 300+ buttons converted, all have aria-labels
CODE-LOW-3: ✅ ESLint clean, no infinite loops
DOC-1: ✅ State machine diagrams complete + code examples
DOC-2: ✅ Migration merge SOP documented + CI validation
DOC-3: ✅ RBAC matrix 15 domains + role-permission table
UI-LOW-1 to UI-LOW-8: ✅ All 8 UX items implemented
DB-LOW-1: ✅ JSON/JSONB audit complete, no changes needed
```

### Regression Testing
```
✅ All 80 bugs regression tested
✅ Zero new bugs introduced
✅ Cross-browser verified (Chrome, Safari, Firefox)
✅ Mobile responsive tested
✅ A11y audit clean (0 critical, <5 warnings)
✅ Performance unchanged or improved
```

### Quality Gates
```
✅ npm test: 100% pass (or >95% known flaky)
✅ npx tsc --noEmit: 0 TypeScript errors
✅ npm run lint: 0 ESLint errors
✅ Lighthouse: All scores ≥90
```

---

## 🚀 Rollout

### Post-Implementation (Day 26)
1. **Code Review** → Architecture team (1 day)
2. **Staging Test** → QA team (1 day)
3. **Production Deploy** → DevOps (30 min)

### Monitoring (Week +1)
- [ ] No new error spikes
- [ ] User adoption metrics normal
- [ ] Performance metrics stable
- [ ] Security incident log clear

---

**End of Implementation Guide**  
Status: ✅ READY FOR EXECUTION
