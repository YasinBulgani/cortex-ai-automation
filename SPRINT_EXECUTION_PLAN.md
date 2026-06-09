# SPRINT EXECUTION PLAN — 80 BULGU × 3 KIŞI (2 DEV + 1 QA)

**Başlangıç:** Hemen (2026-06-09)  
**Target:** Tüm 80 bulgu CLOSED  
**Ekip:** Dev-A, Dev-B, QA-Lead  
**Methodology:** Parallel sprints + dependency chain  

---

## 🎯 SPRINT STRUCTURE

### **WEEK 1: KRITIK FIXES (Days 1-5)**

#### **🔴 KRITIK (8 bulgu) — MUST FINISH WEEK 1**

Dev-A sorumluluk:
```
S-CRIT-1 (SSL verify=False)              0.5h
S-CRIT-2 (Tenant fallback exception)     1h
DB-CRIT-2 (ProjectMember FK)             2h
A-CRIT-3 (Cost Numeric overflow)         1h
────────────────────────────────
Toplam Dev-A: 4.5h ✅ DAY 1-2
```

Dev-B sorumluluk:
```
S-CRIT-3 (Webhook HMAC enforcement)      2h
DB-CRIT-1 (Multi-tenant RLS verify)      1h
A-CRIT-1 (Async/Sync mixing refactor)    6h
A-CRIT-2 (Circuit breaker fix)           2h
────────────────────────────────
Toplam Dev-B: 11h ✅ DAY 1-3
```

QA-Lead:
```
- Tüm CRITICAL test case'leri yazma
- Dev-A/B çıktısını test etme
- Smoke test suite çalıştırma
```

**Day 1-5 Beklenen Çıktı:**
- ✅ 3 SSL + tenant + webhook FIXED
- ✅ Database constraints enforce
- ✅ Async/sync separation
- ✅ Circuit breaker unit test pass

---

### **WEEK 2: YÜKSEK RİSK (Days 6-10)**

#### **🟠 HIGH (32 bulgu) — 2 Parallel Streams**

**Stream A — Dev-A (Backend Security & DB)**
```
SEC-HIGH-1  Admin permission wildcard           1h
SEC-HIGH-2  Engine internal key rotation        3h
SEC-HIGH-4  SSRF protection expand (IPv6)       2h
SEC-HIGH-5  Error message sanitization          2h

DB-HIGH-1   Migration merge resolve             2h
DB-HIGH-2   Cascade delete soft-delete pattern  4h
DB-HIGH-3   DateTime timezone audit             2h
DB-HIGH-4   Composite index add                 1h

────────────────────────────────
Toplam: 17h ✅ Days 6-8
```

**Stream B — Dev-B (Backend Performance & Test)**
```
PERF-HIGH-1  N+1 query fix (eager loading)      4h
PERF-HIGH-2  HTTPX connection pool singleton    1h
PERF-HIGH-3  Timeout boundary enforcement       2h

T-HIGH-1     E2E global setup retry mechanism   2h
T-HIGH-2     Test data seed factory             3h
AUTO-HIGH-1  Test parameterization pattern      3h
AUTO-HIGH-2  E2E fullParallel enable            1h
AUTO-HIGH-3  Admin domain RBAC test (20 test)   4h

────────────────────────────────
Toplam: 20h ✅ Days 6-9
```

**QA-Lead (Parallel)**
```
- Test matrix create (CRITICAL × 32 HIGH)
- Dev-A output test (security focus)
- Dev-B output test (performance + coverage)
- Regression test suite (baseline from WEEK 1)
```

**Week 2 Beklenen Çıktı:**
- ✅ 32 HIGH bulgu FIXED + TESTED
- ✅ 20+ admin RBAC test pass
- ✅ N+1 query 50-100x speedup verify
- ✅ Security audit pass (all HIGH findings resolved)
- ✅ E2E parallel run <15 min

---

### **WEEK 3-4: MEDIUM RISK (Days 11-20)**

#### **🟡 MEDIUM (38 bulgu) — 2 Parallel Streams**

**Stream A — Dev-A (Database + Architecture)**
```
DB-MED-1  Self-ref FK cascade semantics        1h
DB-MED-2  JSONB schema validation              2h
DB-MED-3  RefreshToken.id default UUID         0.5h
DB-MED-4  JSON → JSONB migration               1h

A-MED-1   Service layer async refactor         6h
A-MED-2   Correlation ID graceful handling     2h
A-MED-3   Rate limiter runtime error handling  1h

FUNC-MED-1  Review workflow state machine       3h
FUNC-MED-2  Defect retest lifecycle validation  2h
FUNC-MED-3  Products real telemetry pipeline    4h
FUNC-MED-4  API key rotation endpoint           4h

────────────────────────────────
Toplam: 26.5h ✅ Days 11-15
```

**Stream B — Dev-B (Frontend + Otomasyon)**
```
UI-MED-1   Pagination implementation            4h
UI-MED-2   Design token migration (dark mode)   3h
UI-MED-3   Form validation real-time            2h
UI-MED-4   Filter state URL persistence         2h
UI-MED-5   Modal responsive overflow            1h

AUTO-MED-1  Flaky test detection CI             3h
AUTO-MED-2  Pre-commit hook setup               1h
AUTO-MED-3  Performance baseline CI             4h
AUTO-MED-4  Async test isolation fixture        2h

DEVOPS-1   Fresh DB upgrade CI test             1h
DEVOPS-2   Migration fresh DB scenario test     1h

────────────────────────────────
Toplam: 24h ✅ Days 11-15
```

**QA-Lead**
```
- MEDIUM test matrix execute
- Performance regression test (N+1 baseline vs optimized)
- Frontend E2E test (pagination, filters, forms)
- Database migration test (fresh DB + upgrade)
- Async isolation test
```

**Week 3-4 Beklenen Çıktı:**
- ✅ 38 MEDIUM bulgu FIXED + TESTED
- ✅ Database constraints all verified
- ✅ Frontend UX improvements verified (pagination, validation)
- ✅ Otomasyon improvements (parallel, parameterized)
- ✅ Integration test coverage %70+

---

### **WEEK 5: LOW RISK (Days 21-25)**

#### **🟢 LOW (27 bulgu) + DOCUMENTATION**

**Stream A — Dev-A (Code Quality + Docs)**
```
CODE-LOW-1  AppShell component split            3h
CODE-LOW-2  Button styling consistency          2h
CODE-LOW-3  useEffect dependency cleanup        1h

DOC-1       State machine transition diagram    2h
DOC-2       Merge migration strategy SOP        2h
DOC-3       RBAC permission matrix              2h

────────────────────────────────
Toplam: 12h ✅ Days 21-23
```

**Stream B — Dev-B (UI/UX + Nice-to-have)**
```
UI-LOW-1    Modal escape key handler            0.5h
UI-LOW-2    Loading state aria-label            0.5h
UI-LOW-3    Empty state emoji aria-hidden       0.5h
UI-LOW-4    Responsive table scroll hint        1h
UI-LOW-5    Error retry button                  1h
UI-LOW-6    Modal double-click debounce         1h
UI-LOW-7    Breadcrumb current page             1h
UI-LOW-8    Responsive modal max-width          1h

DB-LOW-1    JSON vs JSONB type audit            1h

────────────────────────────────
Toplam: 8h ✅ Days 21-23
```

**QA-Lead**
```
- Final regression test suite (ALL 80 findings)
- Cross-browser test (Chrome, Safari, Firefox)
- Mobile responsive test (iPad, iPhone)
- Accessibility audit (axe-core)
- Performance benchmark vs baseline
- Security final check
```

**Week 5 Beklenen Çıktı:**
- ✅ 27 LOW bulgu FIXED
- ✅ Code cleanup + doc complete
- ✅ Full regression pass
- ✅ A11y audit clean
- ✅ Performance ~100% baseline

---

## 📊 TIMELINE & BURNDOWN

```
WEEK 1  Kritik (8)          ████████ 8 bugs     [0h → 15h → DONE]
WEEK 2  High (32)           ████████████████████████████████ 32 bugs [15h → 52h → DONE]
WEEK 3-4 Medium (38)        ██████████████████████████████████████ 38 bugs [52h → 100.5h → DONE]
WEEK 5  Low (27) + Doc      █████████████████████████ 27 bugs [100.5h → 120.5h → DONE]

CRITICAL PATH: Week 1 (blocking everything else)
DAG DEPENDENCIES: CRITICAL → HIGH → MEDIUM → LOW
```

### **Total Effort Estimate**

| Role | Week 1 | Week 2 | Week 3-4 | Week 5 | Total |
|------|--------|--------|----------|--------|-------|
| Dev-A | 4.5h | 17h | 26.5h | 12h | **60h** |
| Dev-B | 11h | 20h | 24h | 8h | **63h** |
| QA-Lead | 15h | 24h | 32h | 16h | **87h** |
| **Total** | **30.5h** | **61h** | **82.5h** | **36h** | **210h** |

**Per Kişi Per Hafta:**
- Dev-A: 8-13h/hafta (normal sprint) ✅
- Dev-B: 11-20h/hafta (busy weeks 1-2) ✅
- QA-Lead: 15-32h/hafta (heavy testing) ✅

---

## 🔄 DEPENDENCY ANALYSIS

### **KRITICAL BLOCKING CHAIN**
```
Day 1:  S-CRIT-1 (SSL)
        ↓
Day 1-2: S-CRIT-2 (Tenant) + DB-CRIT-1 (RLS)
        ↓
Day 2-3: A-CRIT-1 (Async) + A-CRIT-2 (Breaker)
        ↓
Day 3-5: Tüm HIGH'lar (depend on CRIT foundation)
        ↓
Week 2+: MEDIUM + LOW (depend on HIGH'lar passing test)
```

### **PARALLEL STREAMS (NO BLOCKING)**
- Dev-A (Database path) + Dev-B (Backend/Frontend path) = 90% parallelizable
- QA-Lead = all outputs üzerinde continuous testing

---

## ✅ TEST STRATEGY

### **QA-Lead Responsibility Matrix**

#### **Week 1: CRITICAL Tests**
```
Coverage: SSL, Tenant isolation, HMAC, Async safety
Method: Unit test + Integration test + Security test
Acceptance: 100% pass before Week 2 start
```

#### **Week 2: HIGH Tests**
```
Coverage: Security (8), Performance (4), Backend (3), Test (3), DB (3)
Method: Unit + Integration + Load test (performance)
Acceptance: >95% pass; known flaky <5%
```

#### **Week 3-4: MEDIUM Tests**
```
Coverage: Functionality (4), UI (5), Otomasyon (4), DevOps (2)
Method: E2E + Regression + Visual regression
Acceptance: >95% pass
```

#### **Week 5: LOW + Regression**
```
Coverage: All 80 bugs + baseline regression
Method: Full test suite + A11y + Cross-browser
Acceptance: 100% pass; zero known regressions
```

---

## 🚀 DAILY STANDUP FORMAT

### **9:00 AM — Daily Standup (15 min)**
```
Dev-A: "Yesterday: X bug fixed. Today: Y bug + Z bug. Blocker: [if any]"
Dev-B: "Yesterday: Y bug fixed. Today: Z bug + W bug. Blocker: [if any]"
QA-Lead: "Tested X + Y bugs. Blocking: [if regression found]. Ready for Z bug."
```

### **5:00 PM — Daily Checkin (10 min)**
```
Dev-A: "Done with X+Y. PR opened for review."
Dev-B: "Done with Z. Testing ready."
QA-Lead: "Verified X+Y. Signed off. 2 low-severity regressions found in [component]. Non-blocking."
```

---

## 📋 BRANCHING STRATEGY

### **Branch per Bug Group**
```
main
├── feature/crit-security (Week 1 — Dev-A + Dev-B)
├── feature/high-perf (Week 2 — Dev-B)
├── feature/high-security (Week 2 — Dev-A)
├── feature/medium-backend (Week 3-4 — Dev-A)
├── feature/medium-frontend (Week 3-4 — Dev-B)
└── feature/low-cleanup (Week 5 — both)
```

**Merge Strategy:**
1. Dev commits to feature branch
2. QA-Lead tests on feature branch
3. QA approval → merge to main
4. Main branch always production-ready

---

## 🔑 SUCCESS CRITERIA

### **Week 1 END**
- [ ] 8 CRITICAL bugs FIXED + QA PASSED
- [ ] SSL verify=True in prod code
- [ ] Tenant RLS verified on all tables
- [ ] Async/sync separation clear
- [ ] No regressions in baseline

### **Week 2 END**
- [ ] 32 HIGH bugs FIXED + QA PASSED
- [ ] Test coverage %70+ (integration enabled)
- [ ] Admin RBAC 20+ test pass
- [ ] Performance baseline established
- [ ] Security audit clean

### **Week 3-4 END**
- [ ] 38 MEDIUM bugs FIXED + QA PASSED
- [ ] Frontend pagination working
- [ ] All migrations tested (fresh DB)
- [ ] Async test isolation clean
- [ ] Full regression suite pass

### **Week 5 END**
- [ ] 27 LOW bugs FIXED + cleaned up
- [ ] Documentation complete
- [ ] A11y audit pass (WCAG 2.1 AA)
- [ ] Cross-browser test pass (Chrome, Safari, Firefox)
- [ ] Mobile responsive test pass

### **FINAL STATE**
- ✅ **80/80 bugs CLOSED**
- ✅ **Test coverage %70+**
- ✅ **0 CRITICAL + 0 HIGH remaining**
- ✅ **Canlıya çıkışa HAZIR**

---

## 📌 RISK MITIGATION

### **Risk 1: Async/Sync Refactor Delay (Week 1-2)**
**Mitigation:** Dev-B başlar Day 1 (parallel Dev-A SSL fix), async refactor critical path.  
**Fallback:** Partial async (router only) if deadline tight.

### **Risk 2: Migration Merge Conflict**
**Mitigation:** Dev-A starts with migration DAG cleanup Day 1.  
**Fallback:** Fresh migration chain if too tangled.

### **Risk 3: QA Bottleneck (Week 3-4)**
**Mitigation:** QA-Lead runs automated test suite in parallel (no manual delay).  
**Fallback:** Hire 2nd QA contractor for critical path weeks 3-4.

### **Risk 4: Database Migration Testing**
**Mitigation:** CI test on fresh DB (automated) + QA manual verify.  
**Fallback:** Database team review before main merge.

---

## 🎁 DELIVERABLES (End of Sprint)

1. **All 80 bugs CLOSED** — verified fixed
2. **Test suite expansion** — 200+ new test case
3. **Documentation** — state machines, SOP, permission matrix
4. **Performance baseline** — dashboard <500ms p95
5. **Security audit** — zero CRITICAL/HIGH
6. **Regression test suite** — automated CI/CD gate
7. **Production-ready code** — deployable to GA

---

**Sprint Start:** Monday 2026-06-09  
**Sprint End:** Friday 2026-07-04 (4 weeks)  
**Team:** Dev-A + Dev-B (full-time) + QA-Lead (full-time)  
**Status:** 🟢 READY TO START
