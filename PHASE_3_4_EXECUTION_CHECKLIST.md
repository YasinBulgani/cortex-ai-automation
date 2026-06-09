# Phase 3.4 Execution Checklist
**Project:** Cortex AI (Neurex)  
**Phase:** 3.4 Optimization + Scaling  
**Timeline:** 3 weeks (2026-06-09 start)  
**Team:** 2 engineers + 1 DevOps

---

## Pre-Implementation (Today - 2026-06-09)

### Planning & Approval
- [ ] Review Phase 3.4 summary with team (30 min)
- [ ] Approve budget ($45K) and timeline (3 weeks)
- [ ] Assign leads:
  - Backend lead: ________________
  - Frontend lead: ________________
  - DevOps lead: ________________
  - QA lead: ________________
- [ ] Create Jira epics:
  - [ ] Epic: FLAKY-001 Flaky Test Detection
  - [ ] Epic: CICD-001 CI/CD Optimization
  - [ ] Epic: HARD-001 Production Hardening
  - [ ] Epic: TRAIN-001 Team Training
- [ ] Schedule daily standups (15 min, 9:30 AM)
- [ ] Schedule 3 workshops (Week 3, Tue/Wed/Thu)

### Environment Setup
- [ ] Create feature branches:
  - [ ] `feature/phase-3.4-flaky-detection`
  - [ ] `feature/phase-3.4-cicd-optimization`
  - [ ] `feature/phase-3.4-hardening`
- [ ] Set up local development environment:
  - [ ] `make docker-up` (start services)
  - [ ] `make migrate` (apply migrations)
  - [ ] `python scripts/detect_flaky.py --baseline` (record baseline)
- [ ] Verify test infrastructure:
  - [ ] `make test-backend` (runs successfully)
  - [ ] `npm run test` (frontend tests pass)
  - [ ] `make test-smoke` (smoke tests pass)

### Documentation Review
- [ ] Engineering team reads PHASE_3_4_IMPLEMENTATION_GUIDE.md
- [ ] QA team reads PHASE_3_4_OPTIMIZATION_SCALING.md
- [ ] Identify questions/blockers in Slack
- [ ] Schedule 30-min Q&A session if >5 questions

---

## Week 1: Flaky Test Detection (2026-06-10 to 2026-06-14)

### Code Implementation (Backend)

**Day 1-2: Flaky Service**
- [ ] Create `backend/app/domains/tspm/flaky_service.py`
  - [ ] Copy code from IMPLEMENTATION_GUIDE.md
  - [ ] Implement `FlakyTestService` class
  - [ ] Test locally: `pytest tests/unit/test_flaky_service_enhanced.py`
  - [ ] Code review (1h)
  - [ ] Commit: `feat(tspm): add flaky test detection service`

- [ ] Create `backend/app/domains/tspm/flaky_router.py`
  - [ ] Copy router code from guide
  - [ ] Add endpoints: GET /flaky-tests, POST /test-runs, POST /unquarantine
  - [ ] Test with curl/Postman
  - [ ] Code review (30 min)
  - [ ] Commit: `feat(tspm): add flaky test API endpoints`

**Day 2-3: Database**
- [ ] Create migration `backend/alembic/versions/20260609_0001_flaky_test_tracking.py`
  - [ ] Add `flaky_tests` table
  - [ ] Add `flaky_test_runs` table
  - [ ] Add indexes (project_id, test_id, recorded_at)
  - [ ] Test: `alembic upgrade head`
  - [ ] Verify schema: `psql neurex_postgres -c "\dt flaky_*"`
  - [ ] Commit: `migration(tspm): add flaky test tracking tables`

- [ ] Update `backend/app/infra/models.py`
  - [ ] Add `FlakyTest` model
  - [ ] Add `FlakyTestRun` model
  - [ ] Verify imports work: `python -c "from app.infra.models import FlakyTest"`
  - [ ] Code review (30 min)
  - [ ] Commit: `feat(infra): add flaky test models`

**Day 3-4: Testing**
- [ ] Create `backend/tests/unit/test_flaky_service_enhanced.py`
  - [ ] Test `record_test_run()`
  - [ ] Test quarantine logic (3-fail threshold)
  - [ ] Test `get_flaky_dashboard()`
  - [ ] Verify coverage >80%: `pytest --cov=app.domains.tspm.flaky_service`
  - [ ] Commit: `test(tspm): add flaky service unit tests`

- [ ] Create `backend/tests/integration/test_flaky_detection_e2e.py`
  - [ ] Test full flow: record runs → quarantine → dashboard
  - [ ] Test API endpoints (POST, GET)
  - [ ] Test 7-day trend calculation
  - [ ] Verify 10+ test cases pass
  - [ ] Commit: `test(tspm): add flaky detection E2E tests`

**Day 4-5: Integration**
- [ ] Update `backend/app/core/router_registry.py`
  - [ ] Register flaky_router: `include_router(flaky_router)`
  - [ ] Verify startup: `uvicorn app.main:app`
  - [ ] Test endpoint: `curl http://localhost:8000/api/v1/projects/test/flaky-tests`
  - [ ] Commit: `feat: register flaky detection router`

### Frontend Implementation (Day 3-5)

**Dashboard Component**
- [ ] Create `apps/web/components/FlakyTestDashboard.tsx`
  - [ ] Copy component code from guide
  - [ ] Implement useQuery hook for API data
  - [ ] Add LineChart for trends
  - [ ] Add Table for top 10 flakiest
  - [ ] Style with tailwind + design tokens
  - [ ] Test locally: `npm run dev` (port 3000)
  - [ ] Verify no TypeScript errors: `npx tsc --noEmit`
  - [ ] Code review (1h)
  - [ ] Commit: `feat(frontend): add flaky test dashboard`

**Page Integration**
- [ ] Create `apps/web/app/(dashboard)/p/[projectId]/quality/flaky/page.tsx`
  - [ ] Wrap FlakyTestDashboard component
  - [ ] Add breadcrumbs: Quality → Flaky Tests
  - [ ] Add loading state
  - [ ] Add error boundary
  - [ ] Test locally (navigate to /p/{projectId}/quality/flaky)
  - [ ] Code review (30 min)
  - [ ] Commit: `feat(frontend): add flaky test quality page`

### Week 1 Verification

**Run All Tests**
```bash
# Backend
cd backend && pytest tests/unit/test_flaky_service_enhanced.py -v
cd backend && pytest tests/integration/test_flaky_detection_e2e.py -v

# Frontend
cd apps/web && npm run test -- FlakyTestDashboard
cd apps/web && npx tsc --noEmit

# Full regression
make test-backend
```

**Baseline Metrics**
- [ ] Record current test flakiness: `python scripts/detect_flaky.py --baseline`
- [ ] Export baseline report: `reports/flaky-baseline-2026-06-14.json`
- [ ] Calculate flaky % (current state)

**Deployment Readiness**
- [ ] All tests passing (100% success rate)
- [ ] Code reviews complete (2+ approval)
- [ ] No linter violations: `make lint`
- [ ] TypeScript: 0 errors, 0 warnings
- [ ] Migration tested on staging
- [ ] Dashboard working end-to-end

**Commit to Feature Branch**
```bash
git add -A
git commit -m "feat(phase-3.4): Week 1 flaky test detection system

- Flaky service with quarantine logic (3-fail threshold)
- Detection API endpoints (record, dashboard, unquarantine)
- Database models + migration
- Frontend dashboard + quality page
- 40+ unit/integration tests
- Zero secrets in logs (audit passing)

Metrics:
- Baseline flakiness recorded
- Dashboard loads <500ms
- 100+ test runs tracked

Co-Authored-By: QA Team <noreply@neurex.ai>"
```

---

## Week 2: CI/CD Optimization (2026-06-17 to 2026-06-21)

### CI/CD Configuration (DevOps)

**Day 1-2: Parallelization**
- [ ] Update `backend/pyproject.toml`
  - [ ] Add pytest markers: regression, flaky, slow, etc.
  - [ ] Add testpaths: ["tests"]
  - [ ] Set asyncio_mode: "auto"
  - [ ] Verify: `cd backend && pytest --co -q | head -20`
  - [ ] Commit: `config(backend): add pytest markers and config`

- [ ] Update `Makefile`
  - [ ] Add `test-parallel` target (4 workers)
  - [ ] Add `test-parallel-unit` target
  - [ ] Add `test-fail-fast` target
  - [ ] Add `test-profile` target
  - [ ] Test locally: `make test-parallel PYTEST_WORKERS=4`
  - [ ] Verify execution time: should show <10s for unit tests
  - [ ] Commit: `feat(make): add parallel test targets`

- [ ] Install pytest-xdist locally:
  ```bash
  pip install pytest-xdist pytest-timeout
  ```

- [ ] Test parallelization:
  ```bash
  cd backend
  pytest -n 4 --dist=loadscope tests/unit/ --timeout=300
  # Should complete in <5 minutes (was ~10 min sequential)
  ```

**Day 2-3: CI/CD Workflow**
- [ ] Create `.github/workflows/test.yml`
  - [ ] Copy workflow from guide
  - [ ] Update job names, paths, versions
  - [ ] Add caching for pip (key: requirements.txt)
  - [ ] Add caching for npm (key: package-lock.json)
  - [ ] Add caching for Next.js (.next/)
  - [ ] Set PYTEST_WORKERS=4
  - [ ] Set PYTEST_TIMEOUT=300
  - [ ] Code review (1h)
  - [ ] Commit: `ci: add parallel test workflow`

- [ ] Test workflow locally with act:
  ```bash
  # Install: brew install act
  act -j unit-tests
  ```

**Day 3-4: Cache Optimization**
- [ ] Verify pip cache works:
  - [ ] First run: no cache, installs all deps
  - [ ] Second run: cache hit, <30s
  - [ ] Check: `du -sh ~/.cache/pip`

- [ ] Verify npm cache works:
  - [ ] First run: no cache, npm ci completes
  - [ ] Second run: cache hit, <20s
  - [ ] Check: `du -sh ~/.npm`

- [ ] Verify Next.js build cache:
  - [ ] First build: full build, ~60s
  - [ ] Second build (no changes): <5s (from .next/)
  - [ ] Check: `du -sh apps/web/.next`

**Day 4-5: Resource Optimization**
- [ ] Update `docker-compose.yml`
  - [ ] Add memory limits (backend: 512MB, postgres: 1GB)
  - [ ] Add CPU limits (backend: 1, postgres: 2)
  - [ ] Verify: `docker-compose up` (should not exceed limits)

- [ ] Optimize `engine/Dockerfile`
  - [ ] Use multi-stage build
  - [ ] Minimize layers
  - [ ] Remove dev dependencies from runtime
  - [ ] Verify: `docker build --no-cache` (< 2 min)

- [ ] Document CI/CD tuning:
  - [ ] Create `docs/CI_CD_TUNING_RUNBOOK.md`
  - [ ] Include: worker count, timeout, cache invalidation
  - [ ] Include: troubleshooting (cache poison, slow tests)

### Backend Hardening (Backend Engineer)

**Day 1-2: Secrets Filtering**
- [ ] Create `backend/app/infra/logging_config.py`
  - [ ] Copy SensitiveDataFilter class from guide
  - [ ] Add patterns for: password, token, api_key, auth
  - [ ] Test filtering: `pytest tests/unit/test_logging_filter.py`
  - [ ] Code review (30 min)
  - [ ] Commit: `feat(logging): add sensitive data filter`

- [ ] Integrate filter into app startup:
  - [ ] Update `backend/app/main.py`
  - [ ] Call `setup_logging()` in create_app
  - [ ] Verify logs don't contain secrets: test locally
  - [ ] Commit: `feat(app): enable sensitive data filtering`

- [ ] Create unit tests:
  - [ ] `backend/tests/unit/test_logging_filter.py`
  - [ ] Test password redaction
  - [ ] Test token redaction
  - [ ] Test authorization header redaction
  - [ ] Verify 100% pass rate
  - [ ] Commit: `test(logging): add filter unit tests`

**Day 2-3: Environment-Based Config**
- [ ] Update `backend/app/config.py`
  - [ ] Add ENVIRONMENT field (dev/staging/prod)
  - [ ] Add computed properties:
    - [ ] TEST_MODE (False in prod)
    - [ ] RUN_ALL_TESTS (True only in dev)
    - [ ] ALLOW_DATA_MUTATION (False in prod)
    - [ ] LOG_LEVEL (DEBUG/INFO/WARNING per env)
  - [ ] Test: `python -c "from app.config import settings; print(settings.LOG_LEVEL)"`
  - [ ] Code review (30 min)
  - [ ] Commit: `feat(config): add environment-based settings`

**Day 3-4: API Key Rotation**
- [ ] Update `backend/app/domains/auth/service.py`
  - [ ] Add `rotate_api_keys()` method
  - [ ] Implement: keep 2 active, revoke older ones
  - [ ] Test locally
  - [ ] Code review (30 min)
  - [ ] Commit: `feat(auth): add API key rotation workflow`

- [ ] Add endpoint to router:
  - [ ] POST /api/v1/auth/api-keys/rotate
  - [ ] Verify permission: require admin or self
  - [ ] Test with curl
  - [ ] Commit: `feat(auth): add API key rotation endpoint`

**Day 4-5: Audit Logging**
- [ ] Create migration `backend/alembic/versions/20260609_0002_audit_logging.py`
  - [ ] Add `audit_logs` table
  - [ ] Columns: id, action, actor_id, resource, changes, timestamp, ip, user_agent
  - [ ] Add index: (actor_id, timestamp)
  - [ ] Test: `alembic upgrade head`
  - [ ] Commit: `migration: add audit logging table`

- [ ] Add AuditLog model to `backend/app/infra/models.py`
  - [ ] Copy from guide
  - [ ] Verify import works
  - [ ] Code review (15 min)
  - [ ] Commit: `feat(infra): add audit log model`

- [ ] Create audit service `backend/app/domains/audit/service.py`
  - [ ] Implement: `log_sensitive_action()`
  - [ ] Capture: action, actor, resource, changes, IP, user agent
  - [ ] Test: 50 lines
  - [ ] Commit: `feat(audit): add audit logging service`

### Week 2 Verification

**Run All Tests**
```bash
# Backend with parallelization
make test-parallel PYTEST_WORKERS=4

# Measure time improvement
time make test-parallel PYTEST_WORKERS=1  # Sequential baseline
time make test-parallel PYTEST_WORKERS=4  # Parallel optimized
# Expected: 50% faster (90 min → 45 min)

# Frontend
npm run test

# Type checking
npx tsc --noEmit
```

**CI/CD Verification**
- [ ] Push to feature branch
- [ ] Verify GitHub Actions workflow runs
- [ ] Check execution times:
  - [ ] Unit tests: <5 min
  - [ ] API tests: <10 min
  - [ ] E2E tests: <15 min
  - [ ] Total: <45 min
- [ ] Verify cache hits in workflow
- [ ] Check fail-fast strategy (stop on unit failure)

**Performance Metrics**
- [ ] Record execution time improvement: `reports/ci-cd-metrics-2026-06-21.json`
- [ ] Cache hit rate: >85%
- [ ] P99 test duration: <5s per test

**Deployment Readiness**
- [ ] All tests passing
- [ ] Code reviews complete
- [ ] No linter violations
- [ ] Performance baseline established
- [ ] CI/CD tuning runbook complete

---

## Week 3: Hardening + Training (2026-06-24 to 2026-06-28)

### Production Hardening (Backend Engineer)

**Day 1-2: GDPR Compliance**
- [ ] Create migration `backend/alembic/versions/20260609_0003_gdpr_support.py`
  - [ ] Add columns to users table:
    - [ ] `gdpr_deleted_at` (timestamp, nullable)
    - [ ] `gdpr_export_requested_at` (timestamp, nullable)
  - [ ] Add `user_data_exports` table
  - [ ] Test: `alembic upgrade head`
  - [ ] Commit: `migration: add GDPR compliance tables`

- [ ] Create privacy service `backend/app/domains/privacy/service.py`
  - [ ] Implement: `delete_user_data()` (anonymize + audit)
  - [ ] Implement: `export_user_data()` (complete data dump)
  - [ ] Test locally: 50+ lines
  - [ ] Code review (1h)
  - [ ] Commit: `feat(privacy): add GDPR compliance service`

- [ ] Add privacy endpoints to router:
  - [ ] DELETE /api/v1/users/me (self-delete)
  - [ ] GET /api/v1/users/me/export (request export)
  - [ ] POST /api/v1/users/me/export/download (download zip)
  - [ ] Test with curl
  - [ ] Commit: `feat(privacy): add GDPR API endpoints`

**Day 2-3: Compliance Tests**
- [ ] Create `backend/tests/compliance/test_gdpr.py`
  - [ ] Copy tests from guide
  - [ ] Test: user deletion anonymizes identity
  - [ ] Test: deletion creates audit log
  - [ ] Test: PII not leaked in logs
  - [ ] Test: API key rotation works
  - [ ] Run: `pytest tests/compliance/test_gdpr.py -v`
  - [ ] Verify: 100% pass rate
  - [ ] Commit: `test(compliance): add GDPR test suite`

**Day 3-4: Sentry Integration**
- [ ] Update `backend/app/infra/sentry.py`
  - [ ] Add before_send() hook for PII redaction
  - [ ] Redact: Authorization header, cookies, email
  - [ ] Test: trigger error with PII, verify Sentry redacts
  - [ ] Code review (30 min)
  - [ ] Commit: `feat(sentry): add PII redaction`

**Day 4-5: Security Audit**
- [ ] Run security review:
  - [ ] Check: no hardcoded secrets in code
  - [ ] Check: all API endpoints require auth
  - [ ] Check: RBAC permissions enforced
  - [ ] Check: SQL injection prevention (use ORM)
  - [ ] Check: CSRF tokens on state-changing ops
  - [ ] Create `docs/SECURITY_AUDIT_2026-06-28.md`

- [ ] Document hardening checklist:
  - [ ] Create `docs/SECURITY_HARDENING_CHECKLIST.md`
  - [ ] Include: secrets management, GDPR, audit logging
  - [ ] Include: environment isolation, rate limiting
  - [ ] Include: testing, monitoring, incident response

### Team Training (QA Lead)

**Day 1: Workshop Prep**
- [ ] Prepare 3 workshop decks:
  - [ ] `workshops/01-pytest-advanced.md` (or .pptx)
  - [ ] `workshops/02-karate-api-testing.md`
  - [ ] `workshops/03-playwright-e2e.md`
  - [ ] Each: 40-50 slides, 5+ code examples

- [ ] Prepare workshop materials:
  - [ ] Sample code repo (5 exercises per workshop)
  - [ ] Exercise solutions (for instructor)
  - [ ] Quiz (10 questions per workshop)
  - [ ] Handouts (checklist, patterns, FAQ)

- [ ] Prepare knowledge base:
  - [ ] `docs/TEST_AUTOMATION_GUIDE.md` (best practices)
  - [ ] `docs/TEST_AUTOMATION_FAQ.md` (10+ Q&A)
  - [ ] `docs/CODE_REVIEW_CHECKLIST_TESTS.md` (test quality)
  - [ ] `docs/FLAKY_TEST_DIAGNOSIS.md` (root cause patterns)

**Day 2-3: Workshop 1 - pytest Advanced**
- [ ] Schedule: Tuesday 2 PM, 2 hours
- [ ] Agenda:
  - [ ] 0:00-0:20: Fixtures (scope, cleanup, parametrization)
  - [ ] 0:20-0:35: Markers and test organization
  - [ ] 0:35-0:50: Mocking and monkeypatching
  - [ ] 0:50-1:15: Async testing (pytest-asyncio)
  - [ ] 1:15-1:45: Hands-on lab (write 5 tests)
  - [ ] 1:45-2:00: Q&A and wrap-up

- [ ] Run workshop:
  - [ ] Record attendance: ________________
  - [ ] Collect feedback: survey/discussion
  - [ ] Assign homework: write 3 parametrized tests

**Day 3-4: Workshop 2 - Karate API Testing**
- [ ] Schedule: Wednesday 2 PM, 2 hours
- [ ] Agenda:
  - [ ] 0:00-0:20: Karate basics (feature, scenario)
  - [ ] 0:20-0:35: Assertions and validation
  - [ ] 0:35-0:50: Data-driven testing (Examples table)
  - [ ] 0:50-1:15: Custom functions and JavaScript
  - [ ] 1:15-1:45: Hands-on lab (write 5 API scenarios)
  - [ ] 1:45-2:00: Q&A and wrap-up

- [ ] Run workshop:
  - [ ] Record attendance: ________________
  - [ ] Collect feedback: survey
  - [ ] Assign homework: write 2 contract tests

**Day 4-5: Workshop 3 - Playwright E2E**
- [ ] Schedule: Thursday 2 PM, 2 hours
- [ ] Agenda:
  - [ ] 0:00-0:20: Page Object Model pattern
  - [ ] 0:20-0:35: Selectors, locators, actions
  - [ ] 0:35-0:50: Assertions and screenshots
  - [ ] 0:50-1:15: Visual regression and debugging
  - [ ] 1:15-1:45: Hands-on lab (write 3 workflows)
  - [ ] 1:45-2:00: Q&A and wrap-up

- [ ] Run workshop:
  - [ ] Record attendance: ________________
  - [ ] Collect feedback: survey
  - [ ] Assign homework: write 2 visual regression tests

### Week 3 Verification

**Compliance & Security**
- [ ] GDPR compliance tests: 100% pass
  ```bash
  pytest tests/compliance/test_gdpr.py -v
  ```
- [ ] Security audit: all items checked
- [ ] PII redaction: tested with Sentry
- [ ] Audit logging: events being recorded

**Team Knowledge**
- [ ] 3 workshops completed
- [ ] 100% team attendance (or >80%)
- [ ] Post-workshop quiz: >80% pass rate
- [ ] Feedback survey: >4/5 satisfaction

**Documentation**
- [ ] Knowledge base complete (5 files)
- [ ] Workshop decks published
- [ ] FAQ updated with real team questions
- [ ] Troubleshooting guide available

**Deployment Readiness**
- [ ] All tests passing (unit + integration + compliance)
- [ ] Code reviews complete
- [ ] Migrations tested on staging
- [ ] Security audit green
- [ ] Performance baselines established
- [ ] Team trained and confident

---

## Post-Implementation (2026-06-28 onwards)

### Week 4 & Beyond: Maintenance & Monitoring

**Daily Monitoring**
- [ ] Flaky test dashboard: check daily
  - [ ] Flakiness rate: should be <0.5%
  - [ ] Quarantine rate: <2% of tests
  - [ ] Trending tests: 0 new flaky tests/day
- [ ] CI/CD metrics: check daily
  - [ ] Execution time: should be <45 min
  - [ ] Pass rate: should be >99%
  - [ ] Cache hit rate: should be >85%

**Weekly Review**
- [ ] Team sync (30 min, Friday):
  - [ ] Review flaky tests from week
  - [ ] Review CI/CD failures
  - [ ] Q&A on new patterns
- [ ] Metrics dashboard:
  - [ ] Create report: `reports/weekly-metrics-*.json`
  - [ ] Share with team
  - [ ] Discuss trends

**Monthly Review**
- [ ] Deep dive on flaky tests:
  - [ ] Root cause analysis of top 10
  - [ ] Plan fixes for next sprint
  - [ ] Update FAQ with new patterns
- [ ] Knowledge base update:
  - [ ] Add new team learnings
  - [ ] Update workshop materials
  - [ ] Archive old issues (if resolved)
- [ ] Training needs assessment:
  - [ ] Do we need follow-up workshops?
  - [ ] Are new team members trained?
  - [ ] Should we schedule refresher sessions?

**Quarterly Review**
- [ ] Architecture review:
  - [ ] Is CI/CD still optimal (4 workers)?
  - [ ] Do we need more disk space for logs?
  - [ ] Should we scale up infrastructure?
- [ ] Security audit:
  - [ ] Any new vulnerabilities discovered?
  - [ ] Are secrets still properly redacted?
  - [ ] Is audit logging comprehensive?
- [ ] Team effectiveness:
  - [ ] Reduced production bugs (goal: -30%)?
  - [ ] Faster test cycle (goal: 45 min)?
  - [ ] Team satisfaction (goal: >4/5)?

---

## Success Metrics Dashboard

### Target Metrics (Post-Phase-3.4)

| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| **Flaky Test Rate** | Unknown | <0.5% | [ ] Monitor |
| **CI/CD Execution** | ~90 min | <45 min | [ ] Measure |
| **Cache Hit Rate** | N/A | >85% | [ ] Track |
| **Secrets in Logs** | Risk | 0 cases | [ ] Audit |
| **GDPR Compliance** | Partial | 100% | [ ] Test |
| **Team Knowledge** | Varies | >80% | [ ] Quiz |
| **Production Incidents** | Baseline | -30% | [ ] Track |
| **Test Review Time** | Baseline | -40% | [ ] Measure |

### Measurement Tools

**Flaky Test Dashboard**
- URL: `/api/v1/projects/{project_id}/flaky-tests`
- Metrics: flaky_rate_percent, top_flaky_tests[], trending_up[]
- Frequency: real-time

**CI/CD Metrics**
- Source: GitHub Actions logs
- Metrics: execution_time, cache_hit_rate, pass_rate
- Frequency: per commit

**Compliance Audit**
- Tool: pytest compliance suite
- Metrics: GDPR tests passed, PII redaction working
- Frequency: daily in CI/CD

**Team Knowledge**
- Tool: Post-workshop quiz + survey
- Metrics: pass rate, satisfaction score
- Frequency: after each workshop

---

## Troubleshooting Guide

### Issue: Tests still flaky after detection
**Root Cause:** Detection enabled, but tests not fixed  
**Solution:**
1. Check flaky dashboard for top offenders
2. Pick highest-impact test (>50% fail rate)
3. Debug using root cause patterns (timing, async, mocking)
4. Apply fix, run 10x locally to verify
5. Retest in CI/CD, unquarantine if stable

### Issue: CI/CD slower than before
**Root Cause:** Parallelization not working, or increased tests  
**Solution:**
1. Check if pytest-xdist is installed: `pip show pytest-xdist`
2. Verify workers: `make test-parallel PYTEST_WORKERS=4`
3. Check if tests added: `pytest --co -q | wc -l`
4. Increase workers if available: `PYTEST_WORKERS=8`
5. Profile slowest tests: `make test-profile`

### Issue: Secrets still appearing in logs
**Root Cause:** SensitiveDataFilter not active, or new pattern not covered  
**Solution:**
1. Check filter is loaded: `grep SensitiveDataFilter app/main.py`
2. Test filter: `pytest tests/unit/test_logging_filter.py -v`
3. Add new pattern to PATTERNS list if needed
4. Verify Sentry PII redaction is on
5. Audit logs: `grep -r "password\|token\|api_key" logs/`

### Issue: GDPR compliance tests failing
**Root Cause:** Missing migration or service not implemented  
**Solution:**
1. Check migration: `alembic current`
2. Run migration: `alembic upgrade head`
3. Verify tables: `psql neurex_postgres -c "\dt user_data_exports"`
4. Check privacy service: `python -c "from app.domains.privacy.service import PrivacyService"`
5. Run compliance tests: `pytest tests/compliance/test_gdpr.py -v`

### Issue: Workshop attendance low
**Root Cause:** Scheduling conflict, low perceived value, or fatigue  
**Solution:**
1. Survey team on preferred times
2. Offer optional recording for async watching
3. Show ROI: reduced production bugs
4. Make workshops interactive (pair programming)
5. Schedule follow-up refresher sessions

---

## Sign-Off Checklist

### Engineering Lead
- [ ] Code reviews complete (all 4 modules)
- [ ] Migrations tested on staging
- [ ] Performance baseline established
- [ ] Security audit passing
- [ ] Deployment plan documented

### DevOps Lead
- [ ] CI/CD workflow configured
- [ ] Caching strategy validated
- [ ] Infrastructure scaled appropriately
- [ ] Monitoring dashboards set up
- [ ] Runbook documented

### QA Lead
- [ ] Flaky detection operational
- [ ] Compliance tests passing
- [ ] Workshops completed
- [ ] Knowledge base published
- [ ] Team training documented

### Product/Management
- [ ] Phase 3.4 objectives met
- [ ] Budget within scope ($45K)
- [ ] Timeline achieved (3 weeks)
- [ ] ROI on track (40% flaky reduction)
- [ ] Approved for next phase (if applicable)

---

## Next Phase Planning

**Hypothetical Phase 3.5 (Future)**
- [ ] Native Appium/Selenium support
- [ ] Performance regression detection
- [ ] Visual regression testing
- [ ] Load testing integration
- [ ] Mobile device cloud integration

**Decision Point:** 2026-07-28 (end of Phase 3.4)
- [ ] Review success metrics
- [ ] Decide: continue to 3.5, or pivot to new priority?
- [ ] Plan next cycle

---

## Document Control

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2026-06-09 | QA Lead | Final |
| 1.1 | 2026-06-28 | Team | Post-Implementation |

---

**Phase 3.4 Owner:** QA Engineering Lead  
**Timeline:** 2026-06-09 to 2026-06-28 (3 weeks)  
**Status:** Ready for Implementation ✅

Print this checklist and post on team whiteboard. Update daily with progress.

---

**Good luck! 🚀**
