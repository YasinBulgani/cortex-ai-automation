# QA Governance — Master Index
**Cortex AI Automation (Neurex) — 10-Expert Synthesis**

**Date:** 2026-06-09  
**Branch:** feature/qa-system-bootstrap

---

## Document Hierarchy

```
📋 QA_GOVERNANCE_INDEX_2026-06-09.md ← YOU ARE HERE
│
├─ 🏢 QA_GOVERNANCE_EXECUTIVE_BRIEF_2026-06-09.md (1-page summary for decision-makers)
│  ├─ Current state baseline (55.6/100 maturity)
│  ├─ 10-expert audit findings (competitive, design, architecture)
│  ├─ Critical path blockers (P0 bugs)
│  ├─ Go/No-Go decisions needed
│  └─ Timeline (2-week critical, 90-day comprehensive)
│
├─ 🎯 QA_GOVERNANCE_STRATEGY_2026-06-09.md (36KB, comprehensive strategy document)
│  ├─ Executive summary
│  ├─ Current state assessment (backend, frontend, E2E, API testing)
│  ├─ Expert audit findings summary (7 expert workflows)
│  ├─ Test pyramid recommendation (50/25/15/10)
│  ├─ Test strategy (coverage-driven + risk-driven hybrid)
│  ├─ Tool recommendations (pytest, Factory Boy, k6, Playwright, etc.)
│  ├─ CI/CD integration strategy (fail-fast PR → comprehensive main)
│  ├─ Automation backlog & prioritization (P0-P3 items)
│  ├─ 90-day timeline (Weeks 1-2 → 9-12)
│  ├─ Production readiness checklist
│  ├─ Success metrics & KPIs
│  ├─ Risk mitigation
│  └─ Framework comparison matrices (pytest vs unittest, Karate vs httpx, etc.)
│
├─ 🛣️ AUTOMATION_ROADMAP_2026-06-09.md (25KB, implementation roadmap)
│  ├─ Executive summary
│  ├─ Phase 1: Weeks 1-2 (P0 critical fixes, CI optimization)
│  │  ├─ 7 tasks: RBAC, Jira, Factory Boy, pytest-xdist, ESLint, flaky enforcement, jest coverage
│  │  └─ Deliverable: 6-7 bugs fixed, CI 33m→20m, 0 regressions
│  ├─ Phase 2: Weeks 3-4 (foundation, coverage reporting)
│  │  ├─ Coverage: 70% backend, 60% frontend (enforced)
│  │  ├─ API test audit, webhook tests, RLS validation
│  │  ├─ Design-token migration 50%, visual baseline, k6 smoke
│  │  └─ Deliverable: Foundation solid, visual baseline, performance baseline
│  ├─ Phase 3: Weeks 5-8 (comprehensive coverage, performance)
│  │  ├─ Design-token 100%, k6 full suite, Storybook 50 components
│  │  ├─ OTel Jaeger, E2E 35 specs, sharding (22m→5m/worker)
│  │  └─ Deliverable: Maturity 80/100, visual regression CI-gated
│  ├─ Phase 4: Weeks 9-12 (optimization, production readiness)
│  │  ├─ Mobile (Appium iOS/Android), chaos engineering, documentation
│  │  └─ Deliverable: Maturity 85+/100, production-ready
│  ├─ Resource allocation (team composition, staffing)
│  ├─ Dependencies & blockers
│  ├─ Success metrics (week-by-week, monthly KPIs)
│  ├─ Risk register & mitigation
│  ├─ Deliverables & sign-offs (per phase)
│  ├─ Budget & cost estimation (~$65k engineering, optional tools ~$1k/month)
│  └─ Tool & technology reference (locked versions, config checklists)
│
└─ 📚 Related Memory Documents (10-expert audit findings)
   ├─ mgmt_competitive_audit_2026_06_09.md (55.6/100 maturity, 7 bugs)
   ├─ design_audit_2026_06_09.md (58/100, token bypass root cause)
   ├─ architecture_panel_faz0_2026_06_09.md (modular monolit, async-ready, Faz 0-3)
   ├─ async_faz_2_3_complete.md (circuit breaker, async SQLAlchemy, OTel, read-replica, MinIO)
   ├─ automation_completeness_audit_2026_06_08.md (80% feature-complete)
   ├─ automation_gaps_completed_2026_06_08.md (LLM adapter, scheduler, frontend wiring)
   ├─ automation_persistence_2026_06_08.md (in-memory→SQL: automation_suite_runs, mobile_sessions)
   ├─ frontend_test_suite_state.md (Jest suite previously broken, 370 fixture drift failures)
   └─ ... 15+ other audit documents
```

---

## Quick Navigation

### For Decision-Makers (5 min read)
→ **QA_GOVERNANCE_EXECUTIVE_BRIEF_2026-06-09.md**
- 1-page summary of findings, recommendations, timeline, budget
- Go/No-Go gates
- Decisions needed

### For QA/Test Leaders (30 min read)
→ **QA_GOVERNANCE_STRATEGY_2026-06-09.md**
- Comprehensive test strategy (pyramid, framework selection, CI/CD)
- Current state assessment (all layers)
- 90-day timeline with success metrics

### For Implementation (ongoing reference)
→ **AUTOMATION_ROADMAP_2026-06-09.md**
- Week-by-week tasks, owners, effort estimates
- Acceptance criteria per phase
- Risk register & blockers
- Budget breakdown

### For Audit Context (research)
→ **Memory documents** (see hierarchy above)
- Expert findings from 10-agent workflows
- Architecture decisions (Faz 0-3 complete)
- Code state & test status

---

## Key Metrics at a Glance

### Current State (2026-06-09)
| Metric | Value | Status |
|--------|-------|--------|
| Overall Maturity | 55.6/100 | ⚠️ Competitive but needs work |
| Backend Coverage | 70% | ✅ Enforced (cov-fail-under) |
| Frontend Tests | 813 specs | ✅ High volume |
| E2E Tests | 28 specs | ✅ Solid baseline |
| Type Errors | 0 | ✅ Strict mode |
| Test Pass Rate | 100% (10,386/10,386) | ✅ Green |
| CI Time (unit+api+smoke) | 33m | ⚠️ Needs optimization |
| Critical Bugs (Audit) | 7 found | 🔴 6 fixed, 1 pending RBAC |
| Design-Token Coverage | 798 violations | 🔴 Needs enforcement |
| Flaky Tests Quarantined | ~5 | ⚠️ Enforcement loose |

### Target State (2026-09-09, End of Phase 4)
| Metric | Target | Impact |
|--------|--------|--------|
| Overall Maturity | 85+/100 | Production-ready |
| Backend Coverage | 70%+ | Enforced + maintainable |
| Frontend Coverage | 60%+ | Reported + gated |
| E2E Tests | 35+ specs | Critical path complete |
| CI Time | <15m (sharded) | 33m → 15m (+40% velocity) |
| Design-Token Coverage | 0 violations | Token-first, 0 hardcoded |
| Flaky Tests | <3 in main | Quarantine enforced |
| Security Test Pass | 100% | All audit bugs verified |
| Performance SLA | p75 <500ms | Baseline + k6 enforcement |

---

## Critical Path (Must Complete Week 1-2)

**Blockers for Phase 1 completion:**

1. **RBAC project-permission wiring** (2d, Backend) — **SECURITY BLOCKER**
   - Fix: Import `require_project_permission` in 5 routers
   - Validation: E2E test per role (admin/member/viewer)
   - No merge without: 3 role tests + code review 2 approvers

2. **Jira sync push endpoint** (2d, Backend) — **INTEGRATION BLOCKER**
   - Fix: POST /defects/{id}/sync-jira returns 200
   - Validation: creates external_key + external_source='jira'
   - No merge without: endpoint test + HMAC validation

3. **Flaky test quarantine enforcement** (1d, QA) — **STABILITY BLOCKER**
   - Fix: quarantine.json integrated in Playwright config
   - Validation: <10 flaky tests in main, CI reports violations
   - No merge without: enforcement active + reporter shows status

---

## Phase 1 Deliverables (Week 2)

**Code:**
- [ ] RBAC wiring (5 router imports + E2E tests)
- [ ] Jira sync endpoint (POST logic + HMAC)
- [ ] Factory Boy (auth domain: 3 factories + conftest)
- [ ] pytest-xdist (pytest.ini config, CI job update)
- [ ] ESLint rule (no-restricted-syntax + 407 violations baseline)
- [ ] Jest coverage (jest.config.js + CI reporting)
- [ ] Flaky quarantine (Playwright config + CI report)

**Test Results:**
- [ ] Backend tests: 10,386/10,386 PASS (0 regression)
- [ ] Frontend tests: 0 type errors
- [ ] RBAC E2E: 3/3 (admin, member, viewer)
- [ ] Jira E2E: 1/1 (POST endpoint)

**Performance:**
- [ ] CI time: 33m → <25m (target 20m)

**Maturity:**
- [ ] 55.6/100 → 60/100 (7 bugs fixed + tooling improvements)

---

## Document Versions & Dates

| Document | Version | Updated | Pages | Status |
|----------|---------|---------|-------|--------|
| QA_GOVERNANCE_INDEX | 1.0 | 2026-06-09 | This page | Active |
| QA_GOVERNANCE_EXECUTIVE_BRIEF | 1.0 | 2026-06-09 | 5 | Active |
| QA_GOVERNANCE_STRATEGY | 1.0 | 2026-06-09 | 36 | Active |
| AUTOMATION_ROADMAP | 1.0 | 2026-06-09 | 25 | Active |

---

## How to Use These Documents

### Week 1-2 (Stabilization)
1. **Kickoff meeting:** Review EXECUTIVE_BRIEF + identify owners for 7 P0 tasks
2. **Daily standup:** Track progress in AUTOMATION_ROADMAP (Phase 1 checklist)
3. **Code review:** Verify acceptance criteria (3 role tests, endpoint test, etc.)
4. **Blockers:** Escalate to QA Lead if any P0 item stuck >4 hours

### Week 3-4 (Foundation)
1. **Sprint planning:** Allocate Phase 2 work (API audit, coverage reporting, design-tokens 50%)
2. **Coverage gates:** Monitor pytest + jest thresholds in CI
3. **Visual baseline:** Create Playwright snapshots (50 components)
4. **Performance:** Run k6 smoke scripts, record baseline

### Week 5-8 (Comprehensive)
1. **Design completion:** Finish token migration (100%), delete rescue layer
2. **Performance gates:** Set p75 <500ms SLA in CI
3. **Storybook:** Expand to 50 components, visual regression pipeline
4. **E2E expansion:** Add 7 new critical paths (multi-org, RBAC, Jira, webhook, perf, mobile, a11y)

### Week 9-12 (Optimization)
1. **Production readiness:** Run checklist (all P0 ✓, security 100%, SLA met)
2. **Mobile automation:** Set up Appium (BrowserStack or local farm)
3. **Chaos engineering:** Run 5 resilience experiments
4. **Documentation:** Finalize strategy guide, framework guide, CI runbook
5. **Team training:** Workshop + pair sessions; handoff to team

---

## Success Criteria Summary

### Phase 1 Go/No-Go (Week 2)
✅ **GO if:**
- 6/7 P0 bugs fixed (RBAC, Jira, Factory Boy, xdist, ESLint, flaky, jest)
- CI time <25m (33m → target 20m)
- 0 test regression (10,386/10,386)
- RBAC E2E per role (3/3)

❌ **NO-GO if:**
- >1 P0 item blocked
- Test regression (any failures)
- RBAC E2E <3 tests

### Phase 2 Go/No-Go (Week 4)
✅ **GO if:**
- Backend coverage 70%+ enforced
- Frontend coverage 60%+ reported
- API test audit (100+ documented)
- Webhook tests passing (4/4)
- RLS validation (8+ tests)
- Design-token 50% (400 remaining)
- Visual baseline + k6 smoke baseline

### Phase 3 Go/No-Go (Week 8)
✅ **GO if:**
- Design-token 100% (0 violations)
- k6 suite 8 scripts (p75 baseline)
- Storybook 50 components
- OTel Jaeger traces visible
- E2E 35 specs + sharding
- Flaky <3 tests

### Phase 4 Go/No-Go (Week 12, PRODUCTION READINESS)
✅ **GO/PRODUCTION-READY if:**
- All P0 tests passing (10,386 backend, 813 frontend)
- Coverage >70% backend, >60% frontend
- Security tests 100%
- Performance p75 <500ms
- Flaky <3 in main
- Appium 5+ specs
- Chaos experiments 5/5
- Documentation + training complete

❌ **NO-GO/DELAY if:**
- Any security test fails
- Coverage <70% backend
- >3 flaky tests in main
- Performance SLA breach

---

## Frequently Asked Questions

**Q: Why 90 days? Can we do it faster?**  
A: 2 weeks for P0 critical fixes (security + blockers), then 6 weeks for foundation + coverage, then 4 weeks for comprehensive + optimization. Each phase gates on acceptance criteria. Could compress to 6 weeks with >50% staffing increase.

**Q: What if RBAC wiring is too risky?**  
A: Mitigated with E2E test per role (3 tests); code review 2 approvers; revert plan if main breaks. Can pilot in one router first (e.g., management only), validate, then expand.

**Q: Is Factory Boy adoption worth the effort?**  
A: Yes. 50+ ad-hoc fixtures → 3 factory classes; decouple test data from migrations (intelligence_service.py fixture mess proves this). 2-3 day migration pays off in 1 month of reduced maintenance.

**Q: Why not just use pytest coverage reporting?**  
A: We do. Frontend (Jest) also needs coverage reporting; currently missing. CI badge shows status; threshold enforces quality gate.

**Q: Can we skip k6 in Phase 3?**  
A: Not recommended. We have no performance baseline; production SLA unknown. k6 smoke (3 scripts) is <2 days. Phase 2 defers to Phase 3 if time-pressed.

**Q: What about mobile automation (Appium)?**  
A: Deferred to Phase 4 (Week 9-12) because mobile persistence (SQL migration) completed; native automation is nice-to-have. If critical for demo, move to Phase 3.

**Q: How do we prevent regression after fixes?**  
A: Regression test suite (20+ tests) for all 7 P0 bugs; run in CI; never remove. `@pytest.mark.security + @pytest.mark.regression` tags.

---

## Appendix: Expert Audit Summary

### 10-Expert Workflows (2026-06-09)

| Expert Role | Audit | Findings | Impact |
|-------------|-------|----------|--------|
| **Competitive Analyst** | Management module vs TestRail/Zephyr/Qase | 55.6/100 maturity; 72/100 test design (best); 42/100 integration (worst) | 7 critical bugs identified; 6 fixed |
| **Design Auditor** | Token system + component compliance | 58/100 maturity; 798 kontrast violations; single root cause (token bypass) | Design-token migration strategy clear |
| **Architecture Panel (7 architects)** | Monolit vs microservices; async strategy | Consensus: modular monolit sound; Faz 0-3 complete; resilience layers in place | Production-ready checklist ✓ |
| **Professional QA** | Security + integration + UX | 6 critical bugs (auth, SSRF, MFA, RLS, webhook, Jira); RBAC wiring missing | Path forward clear; P0 fixes identified |
| **Performance Analyst** | k6 baseline + SLA | No baseline; architecture sound; read-replica + MinIO ready | Performance testing Phase 2+ |
| **Mobile Specialist** | Mobile testing strategy | SQL persistence done; native Appium deferred; responsive Playwright sufficient | Phase 4 adds native automation |
| **AI/ML QA** | AI model validation, LLM testing | Adapter wiring complete; LLM executor ready; AI gateway fallback chain working | Not critical path; Phase 2+ |
| **DevOps/Reliability** | Resilience, observability, deployment | Circuit breaker working; OTel prod-enforced; outbox relay atomic; flaky test quarantine loose | OTel Jaeger Phase 3; enforcement Phase 1 |
| **Security Lead** | Auth bypass, SSRF, injection, RLS | 6 critical fixes; 7 domain auth gaps; tenant isolation solid | Security regression test suite required |
| **Team Velocity Lead** | Test infrastructure, CI optimization | 33m CI → 20m target (xdist); coverage reporting missing; Factory Boy needed | Infrastructure fixes Phase 1 immediate |

**Overall Verdict:** ✅ Mature platform, clear gaps identified, achievable roadmap, 2-week critical path, 90-day comprehensive plan, 85+/100 maturity goal realistic.

---

## Document Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-06-09 | 1.0 | Initial creation (QA Governance synthesis) | QA Governance Lead |

---

## Contact & Escalation

| Role | Contact | Availability | Escalation Level |
|------|---------|--------------|------------------|
| **QA Governance Lead** | qalead@neurex.ai | Daily 9am-5pm | Roadmap, strategy, Phase gates |
| **Backend Lead** | backend@neurex.ai | Daily 9am-5pm | RBAC, Jira, Factory Boy, API tests |
| **Frontend Lead** | frontend@neurex.ai | Daily 9am-5pm | Design-tokens, Jest coverage, Storybook |
| **DevOps Lead** | devops@neurex.ai | Daily 9am-5pm | CI/CD, k6 setup, OTel Jaeger |
| **Product Manager** | product@neurex.ai | Tues/Thurs 10am | Scope, timeline, resource decisions |

---

## License & Attribution

This QA Governance Strategy and Automation Roadmap are derived from **10-expert audits** conducted by autonomous agents on 2026-06-09 across competitive analysis, design systems, architecture, security, performance, mobile, AI/ML, DevOps, reliability, and team velocity dimensions.

**Synthesis:** Aggregated findings, common themes, consensus recommendations, prioritized action items.

**Caveats:** Recommendations are advisory. Final decisions rest with engineering leadership and product team. All timelines assume 1 QA + 1.5 engineering FTE per sprint (80 hours). Phase gates and go/no-go criteria are gating points for management review.

---

**Last Updated:** 2026-06-09  
**Next Review:** 2026-06-16 (Week 1 check-in)  
**Status:** ACTIVE — Ready for implementation  
**Owner:** QA Governance Lead
