# LOW PRIORITY BATCH — Task Tracking Checklist

**Sprint Week:** 5 (Days 21-25)  
**Master Status:** 📋 READY TO START  
**Last Updated:** 2026-06-09  

---

## 📅 DAY 21 (Monday)

### Dev-A: AppShell Split (CODE-LOW-1) — 3h

#### Step 1: Directory & File Setup (0.5h)
- [ ] Create `apps/web/components/_components/` directory
- [ ] Create 7 new component files:
  - [ ] AppErrorBoundary.tsx
  - [ ] SidebarIcons.tsx
  - [ ] SidebarNav.tsx
  - [ ] SidebarHeader.tsx
  - [ ] SidebarFooter.tsx
  - [ ] ProductPickerDropdown.tsx
  - [ ] MainContent.tsx

#### Step 2: Extract AppErrorBoundary (0.5h)
- [ ] Copy class component code from AppShell.tsx
- [ ] Add proper imports
- [ ] Update AppShell.tsx to import from new file
- [ ] Test: `npm test -- AppErrorBoundary`

#### Step 3: Extract Icon Functions (0.5h)
- [ ] Create 12 icon functions in SidebarIcons.tsx
- [ ] Add IconChevron with prop support
- [ ] Update AppShell.tsx imports
- [ ] Verify: No unused icon imports

#### Step 4: Extract SidebarNav (0.5h)
- [ ] Move NavItem component
- [ ] Move GLOBAL_NAV constant
- [ ] Move navActive() helper
- [ ] Update imports
- [ ] Test: NavItem renders correctly

#### Step 5: Extract SidebarHeader (0.5h)
- [ ] Move logo + product selector section
- [ ] Move ProductPickerDropdown
- [ ] Verify product selection works
- [ ] Test: Logo renders, dropdown toggles

#### Step 6: Extract Other Sidebars (0.5h)
- [ ] SidebarFooter (language + logout)
- [ ] Verify logout button works
- [ ] Test form element states

#### Step 7: Verify Parity (0.5h)
- [ ] Run: `npm dev` → visually compare
- [ ] Check: All nav items visible
- [ ] Check: Product picker shows all products
- [ ] Check: Mobile sidebar collapses
- [ ] Run: `npm test` → all tests pass
- [ ] Run: `npx tsc --noEmit` → 0 TypeScript errors

**Sign-off:** AppShell split complete ✅

---

### Dev-B: UI-LOW-1 to UI-LOW-4 — 3h

#### UI-LOW-1: Modal Escape Key (0.5h)
- [ ] Find all modal components
- [ ] Verify escape key handler present
- [ ] Write E2E test: `tests/e2e/modal-escape.spec.ts`
- [ ] Test: Open modal → Press Escape → Modal closes
- [ ] Test: Multiple modals → Close topmost
- [ ] Sign-off: ✅

#### UI-LOW-2: Loading State aria-label (0.5h)
- [ ] Update `components/Loading.tsx`
  - [ ] Add `aria-live="polite"`
  - [ ] Add `aria-label="Loading data, please wait..."`
- [ ] Update `components/Spinner.tsx`
- [ ] Find all loading states in pages
- [ ] Add aria-label to spinners (20-30 locations)
- [ ] Test with screen reader
- [ ] Sign-off: ✅

#### UI-LOW-3: Empty State Emoji (0.5h)
- [ ] Find all empty states (20-30 locations)
- [ ] Add `aria-hidden="true"` to emoji divs
- [ ] Verify text-only fallback present
- [ ] Test: Screen reader announces "No items found"
- [ ] Sign-off: ✅

#### UI-LOW-4: Table Scroll Hint (1h)
- [ ] Update `components/ui/table.tsx`
- [ ] Add scroll detection logic
- [ ] Add visual hint (gradient) on scroll
- [ ] Test: Mobile view with wide table
- [ ] Test: Scroll trigger appears/disappears
- [ ] Sign-off: ✅

**End of Day 21:** 6 hours of work done ✅

---

## 📅 DAY 22 (Tuesday)

### Dev-A: Button Consistency + useEffect + Start DOC — 5h

#### CODE-LOW-2: Button Consistency (2h)

**Part A: Audit (0.5h)**
- [ ] Run: `grep -r '<button' apps/web --include="*.tsx" | wc -l`
  - [ ] Expected: ~900
- [ ] Run: `grep -r '<Button' apps/web --include="*.tsx" | wc -l`
  - [ ] Expected: ~100
- [ ] Create: `BUTTON_CONVERSION_AUDIT.md`
  - [ ] Document GROUP A items (300+ buttons to convert)
  - [ ] Document GROUP B items (500+ buttons to keep)

**Part B: Conversion (1h)**
- [ ] Convert 100+ GROUP A buttons:
  - [ ] Primary actions (submit, save, delete)
  - [ ] Navigation (back, next)
  - [ ] Form controls (reset, clear)
- [ ] Verify: All buttons have `type="button"` or `type="submit"`
- [ ] Add aria-label where missing
- [ ] Test: `npm test -- Button`

**Part C: Verification (0.5h)**
- [ ] Run ESLint on button changes
- [ ] Visual inspection: Padding/sizing consistent
- [ ] Hover/focus states visible
- [ ] Screen reader test (5 random buttons)

**Sign-off:** Button audit + conversion 50% complete ✅

#### CODE-LOW-3: useEffect Cleanup (1h)

- [ ] Install/verify ESLint `react-hooks/exhaustive-deps` rule
- [ ] Run: `npx eslint . --rule 'react-hooks/exhaustive-deps: error'`
- [ ] Identify 20-30 violations
- [ ] Create: `USEEFFECT_FIXES.md` (list all fixes)
- [ ] Fix each violation:
  - [ ] Add missing dependencies
  - [ ] Add cleanup functions (event listeners)
  - [ ] Memoize objects/arrays if needed
- [ ] Run: `npm test` → verify no infinite loops
- [ ] Check DevTools: No memory leaks

**Sign-off:** useEffect cleanup complete ✅

#### DOC-1: State Machines (2h)

- [ ] Create: `docs/STATE_MACHINES_ARCHITECTURE.md`
- [ ] Section 1: Review Workflow
  - [ ] State diagram (ASCII art)
  - [ ] Transition table
  - [ ] Invariants + deadlock analysis
  - [ ] Code example
  - [ ] Test cases
- [ ] Section 2: Defect Retest Workflow
  - [ ] Similar structure
  - [ ] State diagram
  - [ ] Transition matrix
- [ ] Verify: All diagrams render correctly
- [ ] Verify: Code examples copy-paste correctly
- [ ] Review: Technical accuracy

**Sign-off:** State machine documentation complete ✅

---

### Dev-B: UI-LOW-5 to UI-LOW-8 — 4h

#### UI-LOW-5: Error Retry Button (1h)
- [ ] Create: `components/ErrorState.tsx`
- [ ] Add retry button with icon
- [ ] Add onClick handler
- [ ] Test: Multiple error types (network, timeout, 404)
- [ ] Verify: Loading state while retrying
- [ ] Accessibility: Button is keyboard-accessible

#### UI-LOW-6: Modal Double-Click Debounce (1h)
- [ ] Find all modal submit buttons
- [ ] Add `disabled={submitting}` state
- [ ] Add loading indicator in button text
- [ ] Test: Double-click submit → Only one request sent
- [ ] Test: Disabled state visible
- [ ] Accessibility: Announce "Saving..." to screen reader

#### UI-LOW-7: Breadcrumb Current Page (1h)
- [ ] Update: `components/Breadcrumb.tsx`
- [ ] Add `aria-current="page"` to last item
- [ ] Style current page (font-weight/color)
- [ ] Test: Multiple breadcrumb paths
- [ ] Accessibility: Screen reader announces "current page"

#### UI-LOW-8: Responsive Modal Max-Width (1h)
- [ ] Update: `components/ui/modal.tsx`
- [ ] Add responsive max-width
  - [ ] max-w-2xl (desktop)
  - [ ] max-w-4xl (large screens)
  - [ ] inset-x-4 (mobile margin)
- [ ] Test: Mobile (375px) → Modal fits
- [ ] Test: Tablet (768px) → Modal sized correctly
- [ ] Test: Desktop (1920px) → Not too wide
- [ ] Verify: Scrollable on small screens

**End of Day 22:** 9 hours of work done ✅

---

## 📅 DAY 23 (Wednesday)

### Dev-A: DOC-2, DOC-3, DB-LOW-1 — 3h

#### DOC-2: Migration Merge Strategy (1.5h)

- [ ] Create: `docs/MIGRATION_MERGE_STRATEGY.md`
- [ ] Section 1: Problem statement
- [ ] Section 2: Sequential numbering solution
- [ ] Section 3: Conflict detection script
  - [ ] Find duplicate migration numbers
  - [ ] List conflicting files
- [ ] Section 4: Resolution procedure
  - [ ] Renaming steps
  - [ ] Testing (upgrade/downgrade)
- [ ] Section 5: CI validation
  - [ ] Pre-commit hook (check no duplicates)
  - [ ] CI test (fresh DB migration)
- [ ] Section 6: Example scenario
- [ ] Verify: Script works (`python scripts/validate_migrations.py`)

#### DOC-3: RBAC Permission Matrix (1.5h)

- [ ] Create: `docs/RBAC_PERMISSION_MATRIX.md`
- [ ] Section 1: Role definitions (6 roles)
  - [ ] Super Admin, Admin, Manager, QA Engineer, Developer, Viewer
- [ ] Section 2: Core domains (15 domains)
  - [ ] auth (login, logout, mfa_setup, etc.)
  - [ ] test_management (create, read, update, delete, execute, review, etc.)
  - [ ] 13 other domains (see CLAUDE.md)
- [ ] Section 3: Permission matrix table
  - [ ] 15 × 6 = 90 cells
  - [ ] ✅ = allowed, ❌ = denied
- [ ] Section 4: Special permissions (admin.*)
  - [ ] Whitelist (11 items)
  - [ ] Blacklist (forbidden items)
- [ ] Section 5: Code integration example
  - [ ] How to check permissions in deps.py
- [ ] Section 6: Audit logging
  - [ ] Permission changes logged
  - [ ] Timestamp + user + reason

**Sign-off:** All 3 documentation guides complete ✅

#### DB-LOW-1: JSON vs JSONB Audit (1h)

- [ ] Query database: Find all JSON/JSONB columns
  ```bash
  psql -d neurex -c "SELECT table_name, column_name, data_type 
    FROM information_schema.columns 
    WHERE data_type IN ('json', 'jsonb')"
  ```
- [ ] Review each column:
  - [ ] Current type
  - [ ] Use case (read-only vs updated)
  - [ ] Recommendation (JSON vs JSONB)
- [ ] Create: `docs/JSON_JSONB_AUDIT.md`
  - [ ] Current state table
  - [ ] Decision matrix
  - [ ] Conclusion: "No changes needed"
- [ ] Verify: No changes required ✅

**Sign-off:** DB audit complete, 0 changes needed ✅

---

### Dev-B: Code Review + Integration (2h)

- [ ] Review Dev-A's code changes:
  - [ ] AppShell split (check all sub-components)
  - [ ] Button conversions (sample 10 changes)
  - [ ] useEffect fixes (spot-check 5 fixes)
  - [ ] Documentation (skim all 3 guides)
- [ ] Run tests: `npm test` → all pass
- [ ] Run linter: `npm run lint` → no errors
- [ ] Run type-check: `npx tsc --noEmit` → 0 errors
- [ ] Visual inspection: No visual regressions
  - [ ] AppShell looks identical to original
  - [ ] Buttons styled consistently
- [ ] Accessibility: Run axe-core
  - [ ] No critical issues
  - [ ] <5 warnings

**Sign-off:** Code review complete ✅

---

### QA-Lead: Regression Test Setup (2h)

- [ ] Create: `tests/REGRESSION_PLAN_ALL_80_BUGS.md`
  - [ ] CRITICAL (8 bugs)
  - [ ] HIGH (32 bugs)
  - [ ] MEDIUM (38 bugs)
  - [ ] LOW (27 bugs)
- [ ] Set up test environment:
  - [ ] Fresh staging DB
  - [ ] All services running
  - [ ] Test data seeded
- [ ] Create test matrix:
  - [ ] Browser: Chrome, Safari, Firefox
  - [ ] Device: Desktop, Tablet, Mobile
  - [ ] OS: macOS, Windows, iOS, Android

**End of Day 23:** 7 hours of work done ✅

---

## 📅 DAYS 24-25 (Thu-Fri)

### QA-Lead: Full Regression Testing — 16h

#### Phase 1: Smoke Test (0.5h)
- [ ] Start dev server: `npm run dev`
- [ ] Test happy path (5 min):
  - [ ] Login works
  - [ ] Dashboard loads
  - [ ] Navigation works
- [ ] Verify: No console errors

#### Phase 2: Full Regression (4h)
- [ ] Run: `npm test -- --coverage`
  - [ ] Target: ≥95% pass rate
  - [ ] Max 5% flaky (known issues)
- [ ] Verify: All 80 bugs still fixed
  - [ ] CRITICAL bugs (8)
  - [ ] HIGH bugs (32)
  - [ ] MEDIUM bugs (38)
  - [ ] LOW bugs (27)

#### Phase 3: Cross-Browser (1h)
- [ ] Chrome (latest):
  - [ ] Smoke test
  - [ ] Run E2E tests
- [ ] Safari (latest):
  - [ ] Smoke test
  - [ ] Check styling
- [ ] Firefox (latest):
  - [ ] Smoke test
  - [ ] Check compatibility

#### Phase 4: Mobile Responsive (1h)
- [ ] iPad (768×1024):
  - [ ] Sidebar collapses
  - [ ] Content readable
  - [ ] Forms usable
- [ ] iPhone (375×667):
  - [ ] Touch targets ≥44×44px
  - [ ] Modals fit screen
  - [ ] Tables scrollable
- [ ] Test orientation: Portrait + Landscape

#### Phase 5: Accessibility Audit (1.5h)
- [ ] Run: `npm run test:a11y` (axe-core)
  - [ ] 0 critical issues
  - [ ] <5 warnings
  - [ ] Document any issues
- [ ] Manual tests:
  - [ ] Keyboard navigation (Tab through entire app)
  - [ ] Screen reader (VoiceOver or NVDA)
    - [ ] All buttons announced
    - [ ] Form inputs labeled
    - [ ] Modal backdrop not focusable
    - [ ] Escape key closes modal

#### Phase 6: Performance (1.5h)
- [ ] Build: `npm run build`
- [ ] Lighthouse:
  - [ ] LCP ≤ 2.5s
  - [ ] FID ≤ 100ms
  - [ ] CLS ≤ 0.1
- [ ] Compare to baseline:
  - [ ] No regressions
  - [ ] Improvements noted

#### Phase 7: Security Final Check (1h)
- [ ] OWASP checklist:
  - [ ] No plaintext secrets in logs
  - [ ] CSRF tokens present
  - [ ] XSS prevention working
  - [ ] Rate limiting enforced
  - [ ] SQL injection prevented
- [ ] No new vulnerabilities

#### Phase 8: Bug Report (1h)
- [ ] Create: `REGRESSION_RESULTS.md`
  - [ ] Summary: X/80 bugs passed
  - [ ] New bugs found: Y
  - [ ] Flaky tests: Z
  - [ ] A11y issues: W
- [ ] Document any new issues found
- [ ] Assign fixes (if needed)

**End of Days 24-25:** Full regression complete ✅

---

## ✅ FINAL CHECKLIST

### All Components Completed
- [x] CODE-LOW-1: AppShell split (Day 21)
- [x] CODE-LOW-2: Button consistency (Day 22)
- [x] CODE-LOW-3: useEffect cleanup (Day 22)
- [x] DOC-1: State machine diagrams (Day 22-23)
- [x] DOC-2: Migration merge strategy (Day 23)
- [x] DOC-3: RBAC permission matrix (Day 23)
- [x] UI-LOW-1: Modal escape key (Day 21)
- [x] UI-LOW-2: Loading aria-label (Day 21)
- [x] UI-LOW-3: Empty state aria-hidden (Day 21)
- [x] UI-LOW-4: Table scroll hint (Day 21-22)
- [x] UI-LOW-5: Error retry button (Day 22)
- [x] UI-LOW-6: Modal double-click debounce (Day 22)
- [x] UI-LOW-7: Breadcrumb current page (Day 22-23)
- [x] UI-LOW-8: Responsive modal max-width (Day 22-23)
- [x] DB-LOW-1: JSON/JSONB audit (Day 23)

### Quality Gates Met
- [ ] npm test: ≥95% pass
- [ ] npx tsc --noEmit: 0 errors
- [ ] npm run lint: 0 errors
- [ ] Lighthouse: All scores ≥90
- [ ] axe-core: 0 critical, <5 warnings
- [ ] Cross-browser: Chrome, Safari, Firefox ✅
- [ ] Mobile: iPad, iPhone responsive ✅
- [ ] Regression: 80/80 bugs passed ✅
- [ ] Zero new bugs introduced ✅

### Documentation Complete
- [ ] State machines: Complete with diagrams
- [ ] Migration SOP: Complete with procedure
- [ ] RBAC matrix: Complete with all 15 domains
- [ ] Implementation guide: Complete with steps
- [ ] Regression results: Complete

### Sign-off Checklist
- [ ] Dev-A work completed + tested
- [ ] Dev-B work completed + tested
- [ ] QA-Lead regression completed
- [ ] All PRs created + reviewed
- [ ] All changes merged to feature branch
- [ ] Ready for code review (Day 26)
- [ ] Ready for staging validation (Day 28)
- [ ] Ready for production deploy (Day 29)

---

## 📊 Progress Tracking

**Start:** 2026-06-09  
**Target Completion:** 2026-06-13 (Friday)  
**Status:** ✅ READY TO BEGIN

### Daily Standup Questions
- What did I complete today?
- What am I working on tomorrow?
- Are there any blockers?

### Weekly Summary (Friday)
- Total hours worked
- All 27 bugs completed
- All quality gates passed
- Ready for next phase

---

## 🎯 Success Criteria

**Implementation Complete** when:
```
✅ All 27 bugs implemented
✅ Code + UI + DB changes tested
✅ All 3 documentation guides written
✅ Full regression passing (80/80 bugs)
✅ A11y audit clean (0 critical)
✅ Cross-browser verified
✅ Mobile responsive verified
✅ Performance baseline maintained
✅ Zero new bugs introduced
```

**Ready for Production** when:
```
✅ Code review approved (2+ reviewers)
✅ Staging validation passed
✅ Security audit clean
✅ Performance benchmark confirmed
✅ Stakeholder sign-off
```

---

**Created:** 2026-06-09  
**Version:** 1.0  
**Status:** ✅ READY FOR EXECUTION
