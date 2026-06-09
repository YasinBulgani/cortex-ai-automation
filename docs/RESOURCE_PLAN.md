# NEUREX FRONTEND HARDENING — RESOURCE PLAN & BUDGET

**Sprint Duration:** 6 weeks (2026-06-10 to 2026-07-21)  
**Budget Cycle:** Q2 2026  
**Approval Status:** PENDING CTO/VP SIGNATURE  

---

## EXECUTIVE SUMMARY

| Item | Cost | Duration | FTE |
|------|------|----------|-----|
| **Frontend Developers (3x)** | $60,000 | 6 weeks | 3.0 |
| **QA/Test Automation Lead** | $30,000 | 6 weeks | 1.0 |
| **Tech Lead/Architect (part-time)** | $20,000 | 6 weeks | 0.5 |
| **Infrastructure & Tools** | $5,000 | - | - |
| **Total Project Cost** | **$115,000** | **6 weeks** | **4.5 FTE** |

**Cost per week:** $19,167  
**Cost per day:** $3,833  
**ROI Payback:** 8-12 weeks (post-launch stabilization + avoided firefighting)

---

## DETAILED RESOURCE BREAKDOWN

### 1. FRONTEND DEVELOPERS (3 FTE)

#### Profile: Senior Frontend Engineer (Dev 1 — Lead)
- **Role:** Performance optimization, hook refactoring, architecture decisions
- **Experience:** 7+ years React, TypeScript, component design
- **Salary:** $180K/year → $20.8K/6-week sprint (40 hrs/week × 6 weeks)
- **Allocation:** 100% (critical path)
- **Key Responsibilities:**
  - Lead use-management hook split (6-8 days)
  - TanStack Virtual implementation (3-4 days)
  - TypeScript strict mode audit (2-3 days)
  - Load testing + performance baseline (2 days)
  - Code review + merge coordination (ongoing)

#### Profile: Mid-Level Frontend Engineer (Dev 2)
- **Role:** Component refactoring, query key standardization, testing
- **Experience:** 4-5 years React, TypeScript, testing
- **Salary:** $140K/year → $16.2K/6-week sprint
- **Allocation:** 100%
- **Key Responsibilities:**
  - new-project page decomposition (5-6 days)
  - Query key factory creation + ESLint setup (2-3 days)
  - Form validation standardization (3-4 days)
  - E2E test creation (5-6 days)
  - WebSocket notification implementation (2-3 days)

#### Profile: Junior/Mid-Level Frontend Engineer (Dev 3)
- **Role:** Component extraction, type safety, unit testing
- **Experience:** 2-4 years React, TypeScript, testing
- **Salary:** $110K/year → $12.8K/6-week sprint
- **Allocation:** 100%
- **Key Responsibilities:**
  - AppShell refactoring (4-5 days)
  - @neurex/contracts package creation (2-3 days)
  - Error boundary implementation (2-3 days)
  - Unit tests for refactored components (4-5 days)
  - Layout business logic extraction (2-3 days)

**Total Dev Cost:** $49,800 (43% of budget)

---

### 2. QA / TEST AUTOMATION LEAD (1 FTE)

#### Profile: QA Automation Engineer
- **Role:** E2E test automation, load testing, accessibility audit
- **Experience:** 5+ years test automation, Playwright/Cypress, k6/JMeter
- **Salary:** $120K/year → $13.9K/6-week sprint
- **Allocation:** 100%
- **Key Responsibilities:**
  - E2E test framework setup & configuration (Week 4, 1-2 days)
  - Critical path E2E test creation (Week 4-5, 5-6 days)
  - Load testing with k6 (Week 5, 2-3 days)
  - Accessibility audit (WCAG 2.1) (Week 5, 2-3 days)
  - Browser compatibility testing (Week 5, 2-3 days)
  - Cross-browser & mobile testing (Week 5, 2-3 days)
  - Final smoke testing & validation (Week 6, 1-2 days)

**QA Cost:** $30,200 (26% of budget)

---

### 3. TECH LEAD / ARCHITECT (0.5 FTE)

#### Profile: Senior Architect / Tech Lead
- **Role:** Architecture oversight, design decisions, code review
- **Experience:** 10+ years full-stack, system design, mentoring
- **Salary:** $200K/year → $11.5K/6-week sprint (20 hrs/week)
- **Allocation:** 50% (part-time, oversight mode)
- **Key Responsibilities:**
  - Sprint planning & kick-off (Week 1, 2-3 hours)
  - Design review meetings (Week 1, 1-2 hours/day)
  - Code review all critical refactors (ongoing, 5-8 hours/week)
  - Architecture decisions (async, queries, state mgmt, 2-4 hours/week)
  - Gate reviews (Week 2/4/6, 2-3 hours each)
  - Documentation review (Week 6, 2-3 hours)
  - GO/NO-GO decision meeting (Week 6, 1 hour)

**Tech Lead Cost:** $23,000 (20% of budget)

---

### 4. INFRASTRUCTURE & TOOLS

| Item | Cost | Purpose |
|------|------|---------|
| **Playwright/Cypress Enterprise** | $1,500 | E2E test automation (20 tests) |
| **k6 Cloud Plan** | $1,200 | Load testing (1-2K concurrent users) |
| **Axe DevTools License** | $800 | Accessibility testing automation |
| **Sentry Pro Plan** (3 months) | $900 | Error logging + monitoring (post-launch) |
| **GitKraken Enterprise** | $300 | Merge conflict management (optional) |
| **Misc (AWS, monitoring)** | $300 | Infrastructure costs |
| **Total** | **$5,000** | |

---

## TEAM STRUCTURE & ORG CHART

```
┌─────────────────────────────────────────────────────┐
│ CTO / VP Engineering (Sponsor & Decision Maker)     │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
    ┌───▼─────────┐  ┌───────▼──────────┐
    │ Tech Lead   │  │ Frontend Lead    │
    │ (0.5 FTE)   │  │ (Dev 1 - 1.0 FTE)│
    └───┬─────────┘  └───────┬──────────┘
        │                    │
        │          ┌─────────┼─────────┐
        │          │         │         │
        │      ┌───▼──┐  ┌───▼──┐  ┌──▼────┐
        │      │Dev 2 │  │Dev 3 │  │QA Lead│
        │      │1 FTE │  │1 FTE │  │1 FTE  │
        │      └──────┘  └──────┘  └───────┘
        │
        └─► Code Reviews, Design Decisions, Gate Reviews
```

---

## WORK BREAKDOWN STRUCTURE (WBS)

```
Frontend Hardening Sprint (6 weeks, $115K)
├─ Phase 1: Critical Fixes (Week 1-2, $18K)
│  ├─ use-management hook split (Dev 1, 6-8 days)
│  ├─ new-project decomposition (Dev 2, 5-6 days)
│  ├─ AppShell refactoring (Dev 3, 4-5 days)
│  ├─ Type safety contracts (Dev 3, 2-3 days)
│  └─ Code review & integration (Tech Lead, 10 hours)
│
├─ Phase 2: Refactoring & Testing (Week 2-3, $25K)
│  ├─ Hook & component testing (Dev 1/2/3, 8-10 days)
│  ├─ Query key standardization (Dev 2, 3-4 days)
│  ├─ Form validation audit (Dev 3, 3-4 days)
│  └─ Integration testing (QA Lead, 3-4 days)
│
├─ Phase 3: Performance & Type Safety (Week 3-4, $22K)
│  ├─ Virtual scrolling implementation (Dev 1, 3-4 days)
│  ├─ Page-level state optimization (Dev 2, 2-3 days)
│  ├─ TypeScript strict audit (Dev 1, 2-3 days)
│  ├─ Lighthouse optimization (Dev 1, 3-4 days)
│  └─ Performance baseline (QA Lead, 2 days)
│
├─ Phase 4: Secondary Fixes (Week 4, $18K)
│  ├─ WebSocket notifications (Dev 2, 2-3 days)
│  ├─ Error boundaries (Dev 3, 2-3 days)
│  ├─ Layout hooks extraction (Dev 1, 2-3 days)
│  └─ E2E framework setup (QA Lead, 2-3 days)
│
├─ Phase 5: Comprehensive Testing (Week 5, $28K)
│  ├─ E2E critical paths (QA Lead, 5-6 days)
│  ├─ Load testing (QA Lead, 2-3 days)
│  ├─ Accessibility audit (QA Lead, 2-3 days)
│  ├─ Browser/mobile testing (QA Lead, 2-3 days)
│  └─ Core Web Vitals validation (Dev 1 + QA, 2 days)
│
└─ Phase 6: Hardening & Deployment (Week 6, $24K)
   ├─ Final critical fixes (Dev 1/2, 2 days)
   ├─ Documentation & runbooks (Dev 3 + Tech Lead, 3 days)
   ├─ Staging deployment (QA Lead, 1-2 days)
   └─ GO/NO-GO decision (Tech Lead + All leads, 2 hours)
```

---

## BUDGET ALLOCATION BY WEEK

```
Week 1 (Jun 10-14):    $19,167  ████████████████████ (Critical refactors)
Week 2 (Jun 17-21):    $19,167  ████████████████████ (Refactoring + testing)
Week 3 (Jun 24-28):    $19,167  ████████████████████ (Performance)
Week 4 (Jul 1-5):      $19,167  ████████████████████ (Secondary fixes)
Week 5 (Jul 8-12):     $19,167  ████████████████████ (Comprehensive testing)
Week 6 (Jul 15-21):    $19,167  ████████████████████ (Hardening + deployment)
────────────────────────────────────────────────────────────────────
TOTAL:                $115,000
```

---

## SKILLS MATRIX & TRAINING NEEDS

| Skill | Dev 1 | Dev 2 | Dev 3 | QA | Tech Lead |
|-------|-------|-------|-------|-----|-----------|
| React/TypeScript | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Component Design | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Performance Optimization | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Test Automation | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| TanStack Query | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Accessibility (a11y) | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Load Testing (k6) | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

### Training Needs (If-Needed)
| Topic | Duration | For | Cost |
|-------|----------|-----|------|
| TanStack Virtual Workshop | 2 hours | Dev 1, Dev 2 | $0 (included in toolkit) |
| k6 Load Testing | 2 hours | QA Lead | $0 (k6 webinar) |
| WCAG 2.1 a11y | 1 hour | All team | $0 (internal workshop) |

---

## TEAM COMMUNICATION & CEREMONIES

### Daily Stand-up
- **Time:** 9:00 AM daily (15 mins)
- **Attendees:** Dev 1, Dev 2, Dev 3, QA Lead, Tech Lead
- **Format:** Slack thread + optional video call (if blockers)
- **Cadence:** Monday-Friday

### Code Review Protocol
- **Frequency:** Per PR (no wait >4 hours)
- **Reviewers:** Dev Lead + Tech Lead (minimum 2 approvals)
- **Turnaround:** <24 hours target
- **Tool:** GitHub PR comments + Slack notifications

### Phase Gate Reviews
- **Week 2 End (Friday 4pm):** Gate 1 review with Tech Lead + Dev Lead
- **Week 4 End (Friday 4pm):** Gate 2 review with CTO + Tech Lead
- **Week 6 Mid (Wednesday 2pm):** Final validation checkpoint
- **Week 6 End (Monday 2pm):** GO/NO-GO decision meeting

### Sprint Planning & Retrospectives
- **Kick-off:** Monday 6/10, 10:00 AM (2 hours)
  - Review deliverables
  - Assign tasks to devs
  - Set up development environment
  
- **Weekly Retro:** Friday 5:00 PM (1 hour)
  - What went well?
  - What blocked progress?
  - Adjustments for next week?

- **Final Retro:** Friday 7/21, 4:00 PM (1.5 hours)
  - Sprint retrospective
  - Lessons learned documentation

---

## RISK MITIGATION: RESOURCE LEVEL

### Risk: Key Developer Absence
- **Mitigation:** 
  - Cross-training: Dev 2 shadows Dev 1 on performance work
  - Dev 3 pairs with Dev 1 on type safety
  - Tech Lead can cover critical code review gaps
  - Contingency: Hire contract developer if >1 person out >2 consecutive days

### Risk: Scope Creep
- **Mitigation:**
  - Strict feature freeze (June 10-July 21)
  - No new feature requests during sprint
  - Bug fixes only (critical/blocking)
  - All scope changes require CTO approval

### Risk: Insufficient QA Resources
- **Mitigation:**
  - QA lead owns E2E automation, devs assist with manual testing
  - Automated tests reduce manual effort 70%
  - Hire contract QA if load testing bottleneck identified

### Risk: Team Burnout
- **Mitigation:**
  - No weekend work expected
  - Flexible hours allowed (core 10am-3pm mandatory)
  - Weekly retros to identify overload early
  - Acknowledge wins publicly (Slack #wins channel)

---

## BUDGET CONTINGENCY & BUFFER

```
Base Cost:              $115,000
Contingency (10%):      $11,500  ← for unexpected issues
─────────────────────────────────
Total Approved Budget:  $126,500
```

**Contingency Usage Scenarios:**
- Extended testing (2-3 extra days) if Gate 3 fails: $5,000-7,500
- Contract developer support (1 week): $4,000-6,000
- Additional tools/licenses: $1,500-2,000
- Remaining buffer: $2,000-5,000

---

## SUCCESS METRICS FOR RESOURCE ALLOCATION

| Metric | Target | Threshold |
|--------|--------|-----------|
| **Actual vs Planned Cost** | $115K | <$126.5K (10% buffer) |
| **Schedule Adherence** | 100% | ≥95% (no >1 week delay) |
| **Team Utilization** | 95% | ≥90% |
| **Code Review Turnaround** | <24 hours | <48 hours max |
| **Defect Escape Rate** | <0.1% | <1% |
| **Team Satisfaction** | ≥4/5 | ≥3.5/5 |

---

## POST-SPRINT RESOURCE PLAN

### After Week 6 (Post-Launch)
- **Production Support (2 weeks):** 1 dev on-call, QA lead monitoring
  - Budget: $8,000
  - Purpose: Patch critical bugs, monitor production metrics
  - Escalation: CTO/VP Engineering

- **Knowledge Transfer & Documentation (1 week):** All team
  - Budget: $6,000
  - Purpose: Archive learnings, update internal wiki, team retrospective

- **Vacation/Recovery:** Team members take 1-week vacation (staggered)
  - After July 21 (high stress sprint)

### Ongoing Maintenance (Post-Launch)
- **Quarterly Performance Audits:** 1 day/quarter (Dev 1 + Tech Lead)
  - Monitor Lighthouse, Core Web Vitals, bundle size trends
- **Feature Development:** Resume normal cadence (Aug 1)

---

## APPROVAL SIGN-OFF

**Budget Authorization:**
- [ ] CTO: $115K approved + 10% contingency
- [ ] VP Finance: Budget line item coded to Q2 frontend project
- [ ] VP Engineering: Resource allocation confirmed (3 devs + 1 QA)

**Team Allocation Confirmation:**
- [ ] Dev 1 (Senior): Available 100% (June 10-July 21)
- [ ] Dev 2 (Mid): Available 100% (June 10-July 21)
- [ ] Dev 3 (Junior): Available 100% (June 10-July 21)
- [ ] QA Lead: Available 100% (June 10-July 21)
- [ ] Tech Lead: Available 50% (June 10-July 21)

**Resource Conflicts Check:**
- [ ] No competing project deadlines?
- [ ] No planned vacations during sprint?
- [ ] All required software licenses available?

**Sign-off:**
- **Approved by (CTO):** _________________ Date: _________
- **Approved by (VP Eng):** ______________ Date: _________
- **Confirmed by (Dev Lead):** __________ Date: _________

---

**Resource Plan prepared by:** Frontend Audit Task Force  
**Date:** 2026-06-09  
**Status:** READY FOR EXECUTION
