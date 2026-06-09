# Karate Test Suite — Setup & Integration Checklist

Complete setup and integration checklist for deploying Karate API tests in your project.

## Phase 1: Backend Configuration (1-2 hours)

### 1.1 Maven Dependencies

- [ ] Copy content from `pom-karate-config.xml` → `backend/pom.xml`
  - Add Karate, JUnit5, HttpClient, JSON processing dependencies
  - Add Maven Surefire plugin with parallel execution config
  - Add properties section with karate.threads and base.url

```bash
# Verify dependencies
cd backend
mvn dependency:tree | grep -i karate
```

### 1.2 Test Database Seeding

- [ ] Create `backend/scripts/seed_test_users.py`:
  ```python
  # Script to seed test users matching karate-config.js
  # Users:
  #   admin@example.com / admin123 (role: admin)
  #   manager@example.com / manager123 (role: manager)
  #   tester@example.com / tester123 (role: tester)
  #   viewer@example.com / viewer123 (role: viewer)
  ```

- [ ] Create `backend/scripts/seed_organizations.py`:
  ```python
  # Seed multi-tenant test organizations for RLS testing
  ```

- [ ] Execute seeding:
  ```bash
  cd backend
  alembic upgrade head
  python scripts/seed_test_users.py
  python scripts/seed_organizations.py
  ```

- [ ] Verify users exist:
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@example.com", "password": "admin123"}'
  ```

### 1.3 Environment Configuration

- [ ] Copy TestRunner.java to correct location:
  ```bash
  mkdir -p backend/src/test/java/karate
  cp backend/tests/karate/TestRunner.java backend/src/test/java/karate/
  ```

- [ ] Update `backend/pom.xml` test source directory if needed:
  ```xml
  <testSourceDirectory>src/test/java</testSourceDirectory>
  ```

- [ ] Configure local environment variables:
  ```bash
  # backend/.env or export before running tests
  export BASE_URL=http://localhost:8000
  export DATABASE_URL=postgresql://user:pass@localhost:5432/neurex
  export REDIS_URL=redis://localhost:6379/0
  export JWT_SECRET=test-secret-key-123
  ```

## Phase 2: Karate Files Setup (30 minutes)

### 2.1 Feature Files

- [ ] All 10 feature files present in `backend/tests/karate/features/`:
  ```bash
  ls backend/tests/karate/features/
  # 01_auth_login.feature
  # 02_auth_me.feature
  # 03_projects_create.feature
  # 04_projects_get_by_id.feature
  # 05_test_cases_create.feature
  # 06_test_cases_get.feature
  # 07_test_runs_trigger.feature
  # 08_test_runs_status.feature
  # 09_permissions_rbac.feature
  # 10_cascade_delete.feature
  ```

- [ ] Configuration files present:
  ```bash
  ls backend/tests/karate/
  # karate-config.js
  # TestRunner.java
  # README.md
  # QUICKSTART.md
  # CI_INTEGRATION.md
  # pom-karate-config.xml
  # utils/helpers.js
  ```

### 2.2 Update karate-config.js

- [ ] Verify test users match database seeded users:
  ```javascript
  testUsers: {
    admin: { email: 'admin@example.com', password: 'admin123' },
    manager: { email: 'manager@example.com', password: 'manager123' },
    tester: { email: 'tester@example.com', password: 'tester123' },
    viewer: { email: 'viewer@example.com', password: 'viewer123' }
  }
  ```

- [ ] Verify base URL matches local environment:
  ```javascript
  var baseUrl = karate.properties['base.url'] || 'http://localhost:8000';
  ```

## Phase 3: Local Testing (1-2 hours)

### 3.1 Backend Startup

- [ ] Start PostgreSQL (if not running):
  ```bash
  docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:14
  ```

- [ ] Start Redis (if needed):
  ```bash
  docker run -d -p 6379:6379 redis:7
  ```

- [ ] Run database migrations:
  ```bash
  cd backend
  alembic upgrade head
  ```

- [ ] Seed test data:
  ```bash
  python scripts/seed_test_users.py
  ```

- [ ] Start FastAPI backend:
  ```bash
  cd backend
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  # Or: python -m uvicorn app.main:app --port 8000
  ```

- [ ] Verify health endpoint:
  ```bash
  curl http://localhost:8000/api/v1/health
  ```

### 3.2 Test Execution

- [ ] Run smoke tests (quick validation):
  ```bash
  cd backend
  mvn test -Dtest=karate.TestRunner -Dkarate.options="--tags @smoke"
  ```

- [ ] Verify output:
  ```
  Tests run: 9
  Failures: 0
  Errors: 0
  ```

- [ ] Run critical tests:
  ```bash
  mvn test -Dtest=karate.TestRunner -Dkarate.options="--tags @critical"
  ```

- [ ] Run RBAC tests:
  ```bash
  mvn test -Dtest=karate.TestRunner -Dkarate.options="--tags @rbac"
  ```

- [ ] Run all tests:
  ```bash
  mvn test -Dtest=karate.TestRunner -Dkarate.threads=5
  ```

### 3.3 Report Review

- [ ] View HTML report:
  ```bash
  open backend/target/karate-reports/karate-summary.html
  ```

- [ ] Check JUnit XML:
  ```bash
  cat backend/target/surefire-reports/karate.TestRunner.txt
  ```

- [ ] Verify all 90 scenarios executed
- [ ] Verify pass rate >= 95%

### 3.4 Troubleshooting

- [ ] Verify auth works:
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@example.com", "password": "admin123"}'
  ```

- [ ] Check database connection:
  ```bash
  psql -U neurex -d neurex_test -c "SELECT COUNT(*) FROM users;"
  ```

- [ ] Debug failed test:
  ```bash
  mvn test -Dtest=karate.TestRunner \
    -Dkarate.options="--tags @smoke" -X
  ```

## Phase 4: CI/CD Integration (2-4 hours)

### 4.1 GitHub Actions

- [ ] Create `.github/workflows/api-tests.yml` using template from `CI_INTEGRATION.md`

- [ ] Commit workflow file:
  ```bash
  git add .github/workflows/api-tests.yml
  git commit -m "ci: add karate api test workflow"
  ```

- [ ] Push to trigger workflow:
  ```bash
  git push origin feature/qa-system-bootstrap
  ```

- [ ] Monitor workflow execution in GitHub Actions tab

- [ ] Configure branch protection rule to require API tests pass:
  - Repo Settings → Branches → Require status checks to pass

### 4.2 Jenkins

- [ ] Copy Jenkinsfile template from `CI_INTEGRATION.md`

- [ ] Create pipeline job in Jenkins UI or as code

- [ ] Configure parameters:
  - Base URL
  - Karate threads
  - Report output path

- [ ] Trigger test run and verify

### 4.3 Docker Integration

- [ ] Create `docker-compose.test.yml` from `CI_INTEGRATION.md` template

- [ ] Test locally:
  ```bash
  docker-compose -f docker-compose.test.yml up --build
  # In another terminal:
  cd backend
  mvn test -Dtest=karate.TestRunner -Dbase.url=http://localhost:8000
  docker-compose -f docker-compose.test.yml down
  ```

- [ ] Push Docker Compose file to repo

## Phase 5: Documentation & Handoff (1 hour)

### 5.1 Team Documentation

- [ ] Review `QUICKSTART.md` — share with team
- [ ] Review `README.md` — detailed coverage
- [ ] Review `CI_INTEGRATION.md` — CI/CD setup

### 5.2 Create Internal Wiki/Docs

- [ ] Document test users and test accounts
- [ ] Document how to add new test scenarios
- [ ] Document common troubleshooting steps
- [ ] Document test environment URLs (dev/stage/prod)

### 5.3 Onboarding

- [ ] Walk through QUICKSTART.md with team member
- [ ] Have them run tests locally
- [ ] Have them understand feature file structure
- [ ] Have them add one new test scenario

## Phase 6: Monitoring & Maintenance (Ongoing)

### 6.1 Test Stability

- [ ] Monitor CI test pass rate over time
- [ ] Investigate any flaky tests (mark with @flaky tag)
- [ ] Address timeout issues in slow environments

### 6.2 Test Coverage Expansion

- [ ] Add new endpoint tests as features are released
- [ ] Add regression tests for bugs found in production
- [ ] Increase RBAC coverage for new roles

### 6.3 Performance Optimization

- [ ] Track test execution time trends
- [ ] Optimize slow tests (reduce unnecessary waits)
- [ ] Profile and reduce database queries

### 6.4 Dependency Updates

- [ ] Update Karate framework monthly:
  ```bash
  mvn versions:display-dependency-updates | grep karate
  ```

- [ ] Test with new JUnit version
- [ ] Update HTTP client libraries

## Validation Checklist

After completing all phases, verify:

### Functional Tests
- [ ] All 10 feature files run successfully
- [ ] ~90 total scenarios execute
- [ ] Pass rate >= 98% on stable environment
- [ ] Smoke tests complete in < 1 minute
- [ ] Full suite completes in < 2 minutes (5 threads)

### RBAC & Security
- [ ] Admin, Manager, Tester, Viewer roles tested
- [ ] Permission matrix verified
- [ ] Tenant isolation confirmed (RLS)
- [ ] Rate limiting verified (429 on 10+ failed attempts)

### Error Handling
- [ ] 401 Unauthorized for missing auth
- [ ] 403 Forbidden for insufficient permissions
- [ ] 404 Not Found for missing resources
- [ ] 422 Unprocessable Entity for invalid input
- [ ] 409 Conflict for duplicate resources

### CI/CD Integration
- [ ] GitHub Actions workflow runs on every push
- [ ] Tests block merge if they fail
- [ ] HTML reports generated and archived
- [ ] Email/Slack notifications on failure

### Documentation
- [ ] QUICKSTART.md covers getting started
- [ ] README.md documents all 10 endpoints
- [ ] CI_INTEGRATION.md covers setup for all platforms
- [ ] Code comments explain complex test logic

## File Inventory

Total files created:

```
backend/tests/karate/
├── karate-config.js                      (42 lines)
├── TestRunner.java                       (45 lines)
├── helpers.js                            (100 lines)
├── README.md                             (450 lines)
├── QUICKSTART.md                         (250 lines)
├── CI_INTEGRATION.md                     (400 lines)
├── pom-karate-config.xml                 (150 lines)
├── SETUP_CHECKLIST.md                    (this file)
├── features/
│   ├── 01_auth_login.feature             (114 lines)
│   ├── 02_auth_me.feature                (94 lines)
│   ├── 03_projects_create.feature        (159 lines)
│   ├── 04_projects_get_by_id.feature     (122 lines)
│   ├── 05_test_cases_create.feature      (152 lines)
│   ├── 06_test_cases_get.feature         (131 lines)
│   ├── 07_test_runs_trigger.feature      (179 lines)
│   ├── 08_test_runs_status.feature       (150 lines)
│   ├── 09_permissions_rbac.feature       (172 lines)
│   └── 10_cascade_delete.feature         (203 lines)
└── utils/
    └── helpers.js                        (87 lines)

Total: ~2,800 lines of code
Total scenarios: ~90
Total endpoints tested: 10
```

## Support & Resources

### Documentation Files
- `QUICKSTART.md` — Get running in 5 minutes
- `README.md` — Complete feature & endpoint documentation
- `CI_INTEGRATION.md` — GitHub, Jenkins, GitLab, Azure setup
- `pom-karate-config.xml` — Maven dependency instructions
- `SETUP_CHECKLIST.md` — This checklist

### Karate Resources
- [Karate GitHub](https://github.com/intuit/karate)
- [Karate Docs](https://karatelabs.github.io/karate/)
- [Karate Examples](https://github.com/intuit/karate/tree/master/karate-demo)

### Testing Best Practices
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [REST API Testing](https://martinfowler.com/bliki/TestPyramid.html)
- [BDD & Gherkin](https://cucumber.io/docs/gherkin/)

## Timeline Summary

| Phase | Duration | Key Output |
|-------|----------|------------|
| 1. Backend Config | 1-2 hours | Maven, DB, Env setup |
| 2. File Setup | 30 min | 10 feature files + config |
| 3. Local Testing | 1-2 hours | Passing smoke tests |
| 4. CI/CD | 2-4 hours | GitHub/Jenkins integration |
| 5. Documentation | 1 hour | Team handoff docs |
| 6. Ongoing | Forever | Maintenance & expansion |
| **TOTAL** | **~8-10 hours** | **Production-ready API tests** |

## Sign-off

- [ ] Setup verified by: _________________ Date: _______
- [ ] Tests passing in CI/CD: _________________ Date: _______
- [ ] Team trained: _________________ Date: _______
- [ ] Documentation reviewed: _________________ Date: _______

**Status**: Ready for production use ✓
