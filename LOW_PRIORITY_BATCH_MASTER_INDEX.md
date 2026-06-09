# LOW PRIORITY BATCH — Master Index

**Sprint Phase:** Week 5 (Days 21-25)  
**Target Release:** GA (General Availability)  
**Status:** ✅ READY FOR EXECUTION  
**Created:** 2026-06-09  

---

## 📚 Documentation Index

### 1. 📋 Executive Summary
**File:** `LOW_PRIORITY_EXECUTIVE_SUMMARY.md`  
**Purpose:** High-level overview for stakeholders  
**Contents:**
- What gets fixed (27 items overview)
- Impact on users/team/business
- Timeline (Days 21-25)
- Quality gates
- Success criteria
- Risks & mitigations

**Read this if:** You want a 5-minute understanding of the project

---

### 2. 📊 Status Report (Detailed)
**File:** `FIX_BATCH_LOW_PRIORITY_STATUS.md`  
**Purpose:** Comprehensive project documentation  
**Contents:**
- Complete batch breakdown
- 27 items detailed descriptions
- CODE-LOW: 3 items (code quality)
- DOC: 3 items (documentation)
- UI-LOW: 8 items (UX polish)
- DB-LOW: 1 item (database audit)
- QA regression testing plan
- Timeline & burndown
- Success criteria
- Deliverables manifest

**Read this if:** You need detailed understanding of what's being built

---

### 3. 🛠️ Implementation Guide
**File:** `LOW_PRIORITY_IMPLEMENTATION_GUIDE.md`  
**Purpose:** Step-by-step developer guide  
**Contents:**
- **STREAM A (Dev-A):** Code + Docs + DB work
  - Day 21: AppShell split (3h) — 9 detailed steps
  - Day 22: Button consistency (2h) + useEffect cleanup (1h) + Start DOC (2h)
  - Day 22-23: Documentation (6h)
    - DOC-1: State machine diagrams
    - DOC-2: Migration merge strategy
    - DOC-3: RBAC permission matrix
  - Day 23: DB-LOW-1 JSON/JSONB audit (1h)

- **STREAM B (Dev-B):** UI/UX Polish
  - Day 21: UI-LOW-1 to UI-LOW-4 (3h)
  - Day 22-23: UI-LOW-5 to UI-LOW-8 (5h)
  - Day 23: Code review + integration (2h)

- **QA-Lead:** Regression testing
  - Days 24-25: Full regression suite (16h)
  - 8 phases: smoke → regression → cross-browser → mobile → a11y → perf → security → report

**Read this if:** You're implementing the batch (detailed step-by-step instructions)

---

### 4. ✅ Task Checklist
**File:** `LOW_PRIORITY_TASK_CHECKLIST.md`  
**Purpose:** Day-by-day tracking checklist  
**Contents:**
- Day 21 checklist (Dev-A AppShell 3h + Dev-B UI-LOW 3h)
- Day 22 checklist (Dev-A button/useEffect/DOC 5h + Dev-B UI-LOW 4h)
- Day 23 checklist (Dev-A DOC/DB 3h + Dev-B review 2h + QA setup 2h)
- Days 24-25 checklist (QA full regression 16h)
- Final checklist (all components, quality gates, sign-off)
- Progress tracking
- Success criteria

**Read this if:** You want to track daily progress

---

## 🎯 Quick Reference

### Files to Create/Modify

#### Code Changes
```
apps/web/components/
├── AppShell.tsx [REFACTORED]
├── _components/
│   ├── AppErrorBoundary.tsx [NEW]
│   ├── SidebarIcons.tsx [NEW]
│   ├── SidebarNav.tsx [NEW]
│   ├── SidebarHeader.tsx [NEW]
│   ├── SidebarFooter.tsx [NEW]
│   ├── ProductPickerDropdown.tsx [NEW]
│   └── MainContent.tsx [NEW]
├── ui/button.tsx [AUDIT + CONVERSIONS]
├── ErrorState.tsx [NEW] (UI-LOW-5)
├── Breadcrumb.tsx [UPDATED] (UI-LOW-7)
└── ... (300+ button conversions)
```

#### Documentation
```
docs/
├── STATE_MACHINES_ARCHITECTURE.md [NEW]
├── MIGRATION_MERGE_STRATEGY.md [NEW]
├── RBAC_PERMISSION_MATRIX.md [NEW]
└── JSON_JSONB_AUDIT.md [NEW]
```

#### Test Artifacts
```
tests/
├── REGRESSION_PLAN_ALL_80_BUGS.md [NEW]
├── REGRESSION_RESULTS.md [NEW (after testing)]
├── a11y_audit_results.md [NEW (after testing)]
├── cross_browser_results.md [NEW (after testing)]
└── performance_benchmark.md [NEW (after testing)]
```

---

## 📅 Timeline at a Glance

| Day | Dev-A | Dev-B | QA-Lead | Status |
|-----|-------|-------|---------|--------|
| **21** | AppShell split (3h) | UI-LOW-1-4 (3h) | — | ⏳ In Progress |
| **22** | Button + useEffect + DOC-1 (5h) | UI-LOW-5-8 (4h) | — | ⏳ In Progress |
| **23** | DOC-2 + DOC-3 + DB-LOW (3h) | Code review (2h) | Setup (2h) | ⏳ In Progress |
| **24-25** | — | — | Full regression (16h) | ⏳ In Progress |
| **Total** | **11h** | **9h** | **18h** | **✅ 38h** |

---

## 🔍 What Each Document Covers

### For Product Managers
📖 **Read:** Executive Summary  
💡 **Key Takeaway:** 27 low-priority bugs being fixed before GA release. Zero functional changes, pure polish. 37 hours of work, 🟢 LOW risk.

### For Developers
🛠️ **Read:** Implementation Guide + Task Checklist  
💡 **Key Takeaway:** Detailed step-by-step instructions for Days 21-25. 9 components to create, 300+ buttons to convert, 3 documentation guides to write.

### For QA
🧪 **Read:** Status Report (QA section) + Task Checklist (Days 24-25)  
💡 **Key Takeaway:** Full regression testing across 80 bugs, 8 phases, A11y audit, cross-browser, mobile responsive.

### For Architecture
🏗️ **Read:** Status Report (all sections) + Implementation Guide (sub-components)  
💡 **Key Takeaway:** AppShell refactor maintains visual parity but improves maintainability. No architectural changes.

### For DevOps
🚀 **Read:** Executive Summary (post-deploy monitoring)  
💡 **Key Takeaway:** No database migrations, no API changes, pure UI/docs. Simple rollback if needed.

---

## ⚡ Critical Path

**Blocking sequence:**
1. **Day 21:** AppShell split must complete (blocks Day 23 code review)
2. **Days 22-23:** All code + docs work
3. **Days 24-25:** Regression testing (blocks GA release decision)

**Parallel work:**
- Dev-A + Dev-B can work independently (no dependencies)
- QA setup can start Day 23 (doesn't block development)

---

## 🚨 Key Success Factors

### Must Complete by End of Day 21
- [ ] AppShell split complete + tested
- [ ] UI-LOW-1 to UI-LOW-4 complete + tested

### Must Complete by End of Day 23
- [ ] All 27 bugs implemented
- [ ] All 3 documentation guides written
- [ ] Code review setup started
- [ ] QA regression plan ready

### Must Complete by End of Day 25
- [ ] Full regression passing (80/80 bugs)
- [ ] Zero new bugs introduced
- [ ] A11y audit clean
- [ ] Cross-browser verified
- [ ] Ready for production approval

---

## 📞 Communication Plan

### Daily Standup (9 AM)
**Duration:** 15 min  
**Attendees:** Dev-A, Dev-B, QA-Lead  
**Format:**
- What did I complete?
- What am I working on?
- Are there blockers?

### End-of-Day Status (4 PM)
**Owner:** Team lead  
**Format:** Slack message
```
Day 21 Status:
- Dev-A: ✅ AppShell split 70% (IconChevron remaining)
- Dev-B: ✅ UI-LOW-1-2 complete, starting UI-LOW-3
- QA-Lead: ✅ Regression plan ready
- Blockers: None
```

### Weekly Sync (Friday 3 PM)
**Duration:** 30 min  
**Review:**
- All 27 bugs completed
- Quality gates status
- Any regressions found
- Ready for next phase (code review)

---

## 🎯 Decision Matrix: When to Read What

| Situation | Read This | Why |
|-----------|-----------|-----|
| "What is this project?" | Executive Summary | Quick context |
| "I need to implement this" | Implementation Guide | Step-by-step instructions |
| "How do I track progress?" | Task Checklist | Daily checklist |
| "What are the details?" | Status Report | Complete documentation |
| "I want API reference for state machines" | Status Report (DOC-1 section) | Full design |
| "How do migrations work?" | Implementation Guide (DOC-2 section) | SOP reference |
| "What permissions exist?" | Implementation Guide (DOC-3 section) | RBAC matrix |
| "Is it safe to deploy?" | Executive Summary (risk section) | Risk assessment |

---

## ✨ Deliverables Summary

### Code (7 new components + conversions)
- AppShell split: 7 sub-components (450 LOC total)
- Button conversions: 300+ buttons → <Button> component
- useEffect cleanup: 20-30 fixes for dependencies
- UI improvements: 8 items (modals, tables, breadcrumbs, etc.)

### Documentation (3 guides)
- State Machines Architecture: Review workflow + Defect retest workflow
- Migration Merge Strategy: Conflict detection + resolution procedure
- RBAC Permission Matrix: 15 domains × 6 roles = 90 permission cells

### Testing
- Full regression: 80/80 bugs tested
- Cross-browser: Chrome, Safari, Firefox
- Mobile: iPad, iPhone responsive
- A11y: axe-core audit (0 critical)
- Performance: Lighthouse benchmark

---

## 🔐 Quality Assurance

### Before Shipping
```
✅ npm test: ≥95% pass
✅ npx tsc --noEmit: 0 errors
✅ npm run lint: 0 errors
✅ npm run build: Succeeds
✅ Lighthouse: All ≥90
✅ axe-core: 0 critical, <5 warnings
✅ Visual parity: Identical to original
✅ Regression: 80/80 bugs passed
```

### Monitoring (Post-Deploy)
```
Day 1: Hourly checks
Day 2-7: Daily checks
Week 2+: Regular monitoring
Rollback: Ready if needed
```

---

## 📊 Metrics

### Effort Distribution
```
Dev-A: 13 hours (35%)
Dev-B: 9 hours (24%)
QA-Lead: 16 hours (43%)
Total: 38 hours
```

### Risk Distribution
```
AppShell refactor: MEDIUM risk (visual parity)
Button consistency: LOW risk (isolated)
useEffect cleanup: LOW risk (internal)
Documentation: ZERO risk (no code impact)
UX polish: LOW risk (enhancements)
DB audit: ZERO risk (read-only)
```

---

## 🚀 Next Steps (After Week 5)

**Week 6 (Day 26):** Code Review
- Architecture team reviews changes
- 2+ approvals required
- Address feedback if any

**Week 6 (Day 27):** Staging Validation
- Run full regression on staging
- Verify all changes work end-to-end
- Load testing if applicable

**Week 6 (Day 28):** Production Deploy
- Blue-green deployment
- Monitor error logs
- Monitor performance metrics

**Week 6-7:** Monitoring
- Daily checks (1st week)
- Regular monitoring (ongoing)
- Rollback ready if needed

---

## 📖 Document Relationships

```
LOW_PRIORITY_BATCH_MASTER_INDEX (this file)
├── Executive Summary (5-min overview)
│   └── [Stakeholders, PM, CTO]
│
├── Status Report (detailed reference)
│   ├── [Architects, Tech Leads]
│   └── [References Implementation Guide]
│
├── Implementation Guide (step-by-step)
│   ├── [Developers (Dev-A, Dev-B)]
│   └── [QA Lead (regression section)]
│
└── Task Checklist (daily tracking)
    ├── [Dev-A (Days 21-23)]
    ├── [Dev-B (Days 21-23)]
    └── [QA-Lead (Days 24-25)]
```

---

## ✅ Final Checklist Before Starting

- [ ] All 4 documents reviewed by team
- [ ] Dev-A setup for AppShell split work
- [ ] Dev-B setup for UI-LOW work
- [ ] QA-Lead regression test plan ready
- [ ] Staging environment available
- [ ] Slack channels ready for updates
- [ ] Estimated timeline communicated to stakeholders
- [ ] Risk mitigation plan understood by team

---

## 🎉 Success Looks Like

**Day 25 (Friday 5 PM):**
- ✅ All 27 bugs implemented + tested
- ✅ All 3 documentation guides written
- ✅ Full regression: 80/80 bugs passing
- ✅ Zero new bugs introduced
- ✅ Ready for code review (Day 26)
- ✅ Ready for staging validation (Day 27)
- ✅ Ready for production deploy (Day 28)

---

## 📞 Questions?

- **Technical questions:** Ask in #backend-code-review or #frontend-development
- **Process questions:** Ask team lead
- **Escalation:** Contact sprint lead

---

**Report Generated:** 2026-06-09  
**Status:** ✅ ALL DOCUMENTS READY  
**Next Action:** START IMPLEMENTATION (Day 21)
