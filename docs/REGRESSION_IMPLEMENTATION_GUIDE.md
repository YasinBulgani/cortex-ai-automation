# Regression Suite Implementation Guide
**Date:** 2026-06-09  
**Status:** Bootstrap Phase (Phase 2.3)  
**Target:** 180+ test collection with CI/CD integration  
**Timeline:** 2 weeks (4 engineers)

---

## Quick Start

### 1. Load Test Data
```bash
make regression-seed
# Creates: 2 orgs, 4 users, 100 projects, 500 test cases, 100 runs, 50 defects
```

### 2. Run Full Suite (45 min)
```bash
make regression-full
# Executes: 100 unit + 50 API + 20 E2E + 10 integration tests
```

### 3. Run Parallel (Fastest)
```bash
make regression-parallel
# 4-worker parallel execution (~30 min)
```

### 4. View Help
```bash
make regression-help
```

---

## Architecture

### Test Organization
```
backend/tests/
├── unit/
│   ├── test_regression_core_auth.py         [8 tests]
│   ├── test_regression_*_service.py         [35 tests per service]
│   ├── test_regression_*_schemas.py         [10 tests]
│   └── test_regression_*_helpers.py         [25 tests per domain]
│
├── integration/
│   ├── test_regression_api_auth.py          [16 tests]
│   ├── test_regression_api_projects.py      [8 tests]
│   ├── test_regression_api_testcases.py     [8 tests]
│   ├── test_regression_api_execution.py     [8 tests]
│   ├── test_regression_db_integrity.py      [5 tests]
│   ├── test_regression_async_operations.py  [5 tests]
│   ├── test_regression_cross_service.py     [3 tests]
│   └── test_regression_notifications.py     [3 tests]
│
└── factories.py                              [Test data builders]

e2e/
├── regression/
│   ├── critical-flows.spec.ts               [5 tests]
│   ├── feature-workflows.spec.ts            [10 tests]
│   └── cross-browser.spec.ts                [5 tests]
└── ...

backend/tests/
└── regression_seed.sh                       [Fixture loader]
```

### Test Pyramid
```
        E2E Tests (20)
       /            \
      /  API Tests   \
     /  (50 tests)    \
    /________________\
   Unit Tests (100+)

Quality: Contract ← Integration ← Service ← Unit
Speed:   Slow     ← Medium      ← Fast     ← Fastest
```

---

## Implementation Checklist

### Phase 1: Foundation (Days 1-3)

**Engineer A: Unit Tests (100+)**
- [ ] Core authentication (8 tests)
  - `test_hash_password_*` (4 tests)
  - `test_jwt_token_*` (3 tests)
  - `test_session_revocation` (1 test)

- [ ] Data models & schemas (12 tests)
  - `test_*_schema_validation` (8 tests)
  - `test_model_relationships` (4 tests)

- [ ] Utilities & helpers (10 tests)
  - `test_datetime_helpers` (5 tests)
  - `test_string_helpers` (5 tests)

- [ ] Service layer (35 tests)
  - Test management service (12 tests)
  - Automation service (10 tests)
  - Defect management service (8 tests)
  - AI domain services (5 tests)

- [ ] Domain utilities (25 tests)
  - Locator strategies (8 tests)
  - Gherkin parser (10 tests)
  - Test data generation (7 tests)

**Checklist:**
- [ ] All 100+ unit tests written
- [ ] `test_regression_core_auth.py` complete
- [ ] All tests passing with 70%+ coverage
- [ ] Test markers (@pytest.mark.regression) applied
- [ ] Docstrings with traceability IDs

**Definition of Done:**
```bash
cd backend
pytest tests/unit/test_regression_*.py -m regression -q
# 100+ tests passed, 0 failed
```

### Phase 2: API Integration (Days 4-5)

**Engineer B: API Tests (50+)**
- [ ] Authentication endpoints (16 tests)
  - Login/logout (5 tests)
  - Token refresh (2 tests)
  - MFA operations (6 tests)
  - Password reset (2 tests)
  - Get current user (1 test)

- [ ] Project endpoints (8 tests)
  - CRUD operations (5 tests)
  - Member management (3 tests)

- [ ] Test case endpoints (8 tests)
  - CRUD operations (5 tests)
  - Bulk operations (3 tests)

- [ ] Execution endpoints (8 tests)
  - Run lifecycle (4 tests)
  - Result submission (4 tests)

- [ ] Additional categories (10 tests)
  - Defects (4 tests)
  - Automation (4 tests)
  - Integrations (2 tests)

**Implementation Pattern:**
```python
# tests/integration/test_regression_api_auth.py

@pytest.mark.regression
@pytest.mark.integration
class TestAuthLoginEndpoint:
    def test_login_valid_credentials(self, client: TestClient, db_ready):
        """POST /api/v1/auth/login with valid credentials.
        
        Traceability: TC-AUTH-001, REQ-AUTH-001
        Given: User with email admin@example.com
        When: POST /api/v1/auth/login
        Then: Returns 200 with access_token
        """
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
```

**Checklist:**
- [ ] All 50+ API tests written in `test_regression_api_*.py`
- [ ] Request/response validation included
- [ ] Error cases tested (400, 401, 403, 404, 422)
- [ ] Pagination tested where applicable
- [ ] Data isolation ensured (no cross-test dependencies)
- [ ] Traceability tags (TC-*, REQ-*) in docstrings

**Definition of Done:**
```bash
cd backend
pytest tests/integration/test_regression_api_*.py -m "regression and integration" -q
# 50+ tests passed, 0 failed
```

### Phase 3: Integration Tests (Days 6-7)

**Engineer C: Integration Patterns (10+)**
- [ ] Database integrity (5 tests)
  - Cascade delete
  - Foreign key constraints
  - Unique constraints
  - RLS policy enforcement
  - Transaction rollback

- [ ] Async operations (3 tests)
  - Test run execution lifecycle
  - Background job completion
  - Webhook delivery

- [ ] Cross-service (2 tests)
  - Auth → project → test case → execution
  - Engine integration

**Pattern:**
```python
@pytest.mark.integration
@pytest.mark.requires_db
def test_project_cascade_delete(self, db_session):
    """Verify cascade delete removes all related data."""
    # Setup
    project = create_test_project(db_session)
    test_cases = [create_test_case(db_session, project.id) for _ in range(3)]
    
    # Execute
    db_session.delete(project)
    db_session.commit()
    
    # Verify
    assert db_session.query(TestCase).filter_by(project_id=project.id).count() == 0
```

**Checklist:**
- [ ] Database setup/teardown isolation working
- [ ] Async tests with timeout handling
- [ ] Cross-service mocking where needed
- [ ] Transaction rollback cleanup verified
- [ ] No test interdependencies

**Definition of Done:**
```bash
cd backend
pytest tests/integration/test_regression_*_db_*.py -m "integration" -q
# 10+ tests passed, 0 failed
```

### Phase 4: UI/E2E Tests (Days 8-10)

**Engineer D: E2E Scenarios (20)**
- [ ] Critical flows (5 tests)
  - Login → Create project → Add TC → Execute
  - Create defect → Assign → Update status
  - Create plan → Add cases → Schedule run
  - Generate report → Share
  - Configure automation → Schedule

- [ ] Feature workflows (10 tests)
  - Test management flow
  - Execution flow
  - Defect flow
  - Reporting flow
  - Automation flow

- [ ] Cross-browser (5 tests)
  - Chrome, Firefox, WebKit
  - Mobile Chrome
  - Responsive layout

**Pattern:**
```typescript
// e2e/regression/critical-flows.spec.ts

test.describe('Critical User Workflows', () => {
  
  test('Complete Login → Create Project → Add Test Case → Execute Flow', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'admin@example.com');
    await page.fill('[data-testid="password"]', 'admin123');
    await page.click('[data-testid="submit"]');
    await page.waitForURL('/dashboard');
    
    // 2. Create project
    await page.click('[data-testid="create-project"]');
    await page.fill('[data-testid="project-name"]', 'E2E Test Project');
    await page.fill('[data-testid="project-key"]', 'ETP');
    await page.click('[data-testid="save-project"]');
    
    // 3. Add test case
    await page.click('[data-testid="add-test-case"]');
    await page.fill('[data-testid="tc-title"]', 'Login Test');
    await page.fill('[data-testid="tc-step-1"]', 'Open login page');
    await page.click('[data-testid="save-tc"]');
    
    // 4. Execute
    await page.click('[data-testid="run-tests"]');
    await page.waitForSelector('[data-testid="run-complete"]');
    
    // Verify
    const status = await page.textContent('[data-testid="run-status"]');
    expect(status).toContain('Passed');
  });
  
});
```

**Checklist:**
- [ ] All 20 E2E tests written
- [ ] Page objects/fixtures created
- [ ] Data setup via API before tests
- [ ] Screenshot/video on failure
- [ ] Timeout handling
- [ ] Cross-browser matrix configured

**Definition of Done:**
```bash
npm run test:e2e:regression -- --reporter=list
# 20 tests passed, 0 failed (across all browsers)
```

### Phase 5: CI/CD Integration (Days 11-14)

**All Engineers: Pipeline Setup**
- [ ] GitHub Actions workflow (`.github/workflows/regression.yml`)
  - Scheduled daily at 8 AM
  - Manual trigger support
  - Parallel execution (4 workers)
  - Coverage reporting
  - Slack notifications on failure

- [ ] Makefile targets
  - `make regression-full`
  - `make regression-parallel`
  - `make regression-coverage`
  - `make regression-seed`

- [ ] Test reports
  - JUnit XML export
  - HTML coverage report
  - Trend charts

- [ ] Documentation
  - Runbook (this file)
  - Troubleshooting guide
  - Data schema documentation

**Checklist:**
- [ ] GitHub Actions workflow created
- [ ] Daily schedule configured
- [ ] Makefile targets working
- [ ] Coverage report generated
- [ ] Slack integration tested
- [ ] Documentation complete

**Definition of Done:**
```bash
# Runs successfully:
make regression-full
# Produces artifacts:
#   - reports/regression-junit.xml
#   - reports/regression-coverage/
# Slack notification sent on completion
```

---

## Test Data Management

### Seed Script
Location: `backend/tests/regression_seed.sh`

**Creates:**
- 2 test organizations
- 4 test users (admin, operator, viewer, tester)
- 100 test projects
- 500 test cases
- 100 test runs (varied statuses)
- 50 defects

**Usage:**
```bash
bash backend/tests/regression_seed.sh
# Or:
make regression-seed
```

**Data Reset (between test runs):**
```python
# Automatic via pytest fixture in conftest.py
@pytest.fixture(autouse=True)
def cleanup_test_data(db_session):
    """Auto-cleanup test-created data after each test."""
    yield
    db_session.query(TestRun).filter(TestRun.id.like("test-%")).delete()
    db_session.query(TestCase).filter(TestCase.id.like("test-%")).delete()
    db_session.commit()
```

### Fixture Isolation
```python
# Backend: Use fixtures for auto-cleanup
@pytest.fixture(scope="function")
def db_transaction_rollback(db_session):
    """Wrap test in transaction that rolls back after test."""
    savepoint = db_session.begin_nested()
    yield db_session
    savepoint.rollback()

# Usage in test:
def test_something(db_session, db_transaction_rollback):
    # Create test data (auto-rolled back)
    project = create_test_project(db_session)
    ...
    # Data cleanup happens automatically
```

### E2E Data Setup via API
```typescript
// e2e/fixtures/test-data.ts

export async function setupTestData(page: Page) {
  const token = await login(page, 'admin@example.com', 'admin123');
  
  const project = await createProject(token, {
    name: 'E2E Test Project',
    key: 'ETP'
  });
  
  const testCases = await Promise.all([
    createTestCase(token, project.id, { title: 'TC 1' }),
    createTestCase(token, project.id, { title: 'TC 2' }),
  ]);
  
  return { project, testCases };
}

// Usage:
test('my flow', async ({ page }) => {
  const { project } = await setupTestData(page);
  // Use project in test
});
```

---

## Execution Patterns

### Daily Regression (45 min)
```bash
# Morning routine
make docker-up          # Start postgres + redis
make regression-seed    # Load fixtures
make regression-full    # Run all 180+ tests
make regression-report  # Generate report
```

### CI/CD Pipeline
```yaml
# .github/workflows/regression.yml
schedule:
  - cron: '0 8 * * *'  # Daily 8 AM

jobs:
  regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
      - name: Install deps
      - name: Start services
        run: docker-compose up -d postgres redis
      - name: Run migrations
        run: cd backend && alembic upgrade head
      - name: Load test data
        run: bash backend/tests/regression_seed.sh
      - name: Run regression suite
        run: make regression-parallel
      - name: Upload coverage
        uses: codecov/codecov-action@v3
      - name: Slack notify
        if: failure()
        uses: slackapi/slack-github-action@v1
```

### Developer Workflow
```bash
# During development
make docker-up                              # Start deps
make regression-unit                        # Quick unit test (~5 min)
# Make code changes
make regression-unit                        # Verify unit tests pass
make regression-api                         # Test API endpoints (~10 min)
make regression-full                        # Full validation (~45 min)
git push                                    # CI/CD runs full suite again
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Fails
```bash
# Check postgres is running
docker compose ps postgres

# If not running:
make docker-up

# Verify connection:
psql -h localhost -U postgres -d neurex -c "SELECT 1;"
```

#### 2. Seed Script Fails
```bash
# Check DB exists:
psql -h localhost -U postgres -l | grep neurex

# If missing, create:
psql -h localhost -U postgres -c "CREATE DATABASE neurex;"

# Run migrations:
cd backend
alembic upgrade head

# Then seed:
make regression-seed
```

#### 3. Tests Hang on Async Operations
```bash
# Increase timeout:
pytest --timeout=30

# Or for specific test:
@pytest.mark.timeout(60)
def test_async_operation(self):
    ...
```

#### 4. Flaky E2E Tests
```bash
# Increase timeouts in playwright.config.ts:
timeout: 30000,  // 30s per test
navigationTimeout: 30000,

# Or retry mechanism:
test.describe.configure({ retries: 2 });

# Or use --headed mode for debugging:
npm run test:e2e:regression -- --headed
```

#### 5. Coverage Below 70%
```bash
# Identify uncovered lines:
pytest --cov=app --cov-report=html
open reports/coverage/index.html

# Add tests for gaps:
# - Look for red (uncovered) lines
# - Create test_regression_*_coverage.py
# - Aim for line coverage above 80%
```

---

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Unit Tests | 100+ | 0 | ⏳ |
| API Tests | 50+ | 0 | ⏳ |
| E2E Tests | 20+ | 0 | ⏳ |
| Integration Tests | 10+ | 0 | ⏳ |
| **Total Tests** | **180+** | **0** | ⏳ |
| Code Coverage | 70%+ | TBD | ⏳ |
| Daily Execution | <45 min | TBD | ⏳ |
| Pass Rate | 100% | TBD | ⏳ |
| Flakiness | <1% | TBD | ⏳ |

---

## Resources

### Files Created
- `docs/REGRESSION_SUITE_2026-06-09.md` — Comprehensive test blueprint
- `backend/tests/regression_seed.sh` — Data fixture loader
- `backend/tests/unit/test_regression_core_auth.py` — 8 auth unit tests
- `backend/tests/integration/test_regression_api_auth.py` — 16 auth API tests
- `Makefile` — Regression targets (regression-help, regression-full, etc.)

### Key Commands
```bash
# Setup & execution
make regression-help              # View all regression targets
make regression-seed              # Load 756 test data fixtures
make regression-full              # Run complete suite (180+ tests, 45 min)
make regression-parallel          # 4-worker parallel execution (30 min)
make regression-unit              # Unit tests only (5 min)
make regression-api               # API tests only (10 min)
make regression-e2e               # E2E tests only (15 min)
make regression-integration       # Integration tests only (5 min)
make regression-coverage          # Generate coverage report
make regression-report            # Generate JUnit report
```

### Documentation References
- **Blueprint:** `docs/REGRESSION_SUITE_2026-06-09.md`
- **Guide:** This file
- **CLAUDE.md:** Project conventions & test guidelines
- **Test Infrastructure:** `docs/test_infrastructure.md`

---

## Next Steps (Post-Bootstrap)

1. **Week 2:** Run first full suite, iterate on flaky tests
2. **Week 3:** Integrate into CI/CD, schedule daily runs
3. **Week 4:** Collect baseline metrics, optimize performance
4. **Week 5+:** Continuous improvement, add new tests as features ship

---

## Sign-off

**Status:** ✅ Ready for Phase 2.3 implementation  
**Created:** 2026-06-09  
**Lead:** QA Automation Team  
**Next Review:** After Day 5 (API tests complete)
