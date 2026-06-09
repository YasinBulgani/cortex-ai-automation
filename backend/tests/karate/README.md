# Karate API Test Framework

Comprehensive API testing framework for the Neurex QA automation platform using Karate DSL.

## Overview

- **10 critical endpoint feature files** covering authentication, project management, test cases, and execution
- **BDD syntax** (Given-When-Then) for readable test specifications
- **Multi-role RBAC testing** with admin, manager, tester, and viewer scenarios
- **Tenant isolation verification** (RLS — Row Level Security)
- **Rate limiting and boundary condition tests**
- **Cascade delete verification**
- **5 parallel execution threads** via Maven configuration

## Structure

```
backend/tests/karate/
├── karate-config.js              # Global configuration & test data setup
├── TestRunner.java                # JUnit 5 test runner
├── README.md                      # This file
├── features/
│   ├── 01_auth_login.feature       # Login endpoint tests
│   ├── 02_auth_me.feature          # User profile endpoint tests
│   ├── 03_projects_create.feature  # Project creation tests
│   ├── 04_projects_get_by_id.feature # Project retrieval tests
│   ├── 05_test_cases_create.feature  # Test case creation tests
│   ├── 06_test_cases_get.feature     # Test case retrieval tests
│   ├── 07_test_runs_trigger.feature  # Test execution trigger tests
│   ├── 08_test_runs_status.feature   # Test run status polling tests
│   ├── 09_permissions_rbac.feature   # RBAC and permission tests
│   └── 10_cascade_delete.feature     # Cascade delete verification tests
└── utils/
    └── helpers.js                   # Reusable test utilities
```

## Configuration

### karate-config.js

The global configuration file defines:
- **baseUrl**: API base URL (default: `http://localhost:8000`)
- **env**: Environment profile (dev/stage/prod)
- **headers**: Common HTTP headers
- **testUsers**: Pre-configured user accounts by role (admin, manager, tester, viewer)
- **testData**: Shared test data templates

```javascript
var config = {
  baseUrl: 'http://localhost:8000',
  env: 'dev',
  testUsers: {
    admin: { email: 'admin@example.com', password: 'admin123' },
    manager: { email: 'manager@example.com', password: 'manager123' },
    tester: { email: 'tester@example.com', password: 'tester123' },
    viewer: { email: 'viewer@example.com', password: 'viewer123' }
  }
};
```

## Running Tests

### Prerequisites

1. Backend running on `http://localhost:8000` (or configure via `-Dbase.url`)
2. Test database seeded with default users
3. Maven installed with Java 11+
4. Karate dependencies in backend `pom.xml`

### Maven Commands

```bash
# Run all tests (5 parallel threads)
mvn test -Dtest=TestRunner -Dkarate.threads=5

# Run smoke tests only (@smoke tag)
mvn test -Dtest=TestRunner -Dkarate.options="--tags @smoke"

# Run critical tests only (@critical tag)
mvn test -Dtest=TestRunner -Dkarate.options="--tags @critical"

# Run RBAC tests only (@rbac tag)
mvn test -Dtest=TestRunner -Dkarate.options="--tags @rbac"

# Run against different environment
mvn test -Dtest=TestRunner -Dbase.url=https://api-stage.example.com

# Run with debug output
mvn test -Dtest=TestRunner -Dkarate.options="-D debug"

# Generate HTML report
mvn test -Dtest=TestRunner -Dkarate.options="--format html"
```

### JUnit 5 (IDE Integration)

Run directly from IDE via the `TestRunner` class:
- Right-click `TestRunner.java` → Run
- Methods: `testAll()`, `testSmoke()`, `testCritical()`, `testRBAC()`

## Test Coverage

### 1. Authentication (01_auth_login.feature)
- **Happy path**: Valid login returns 200 with JWT token
- **Error cases**: Wrong password (401), non-existent user (401)
- **Boundary**: Empty fields (422), invalid email format (422)
- **Security**: Rate limiting (429 after 10 failed attempts)
- **HTTP cookies**: Secure HttpOnly cookie storage

### 2. User Profile (02_auth_me.feature)
- **Happy path**: GET /auth/me with valid token returns user
- **Auth**: Cookie-based and Bearer token authentication
- **Error cases**: Missing auth (401), malformed token (401)
- **RBAC**: Verify role-based permission list
- **Boundary**: Invalid token format (401)

### 3. Project Creation (03_projects_create.feature)
- **Happy path**: POST with valid data returns 201
- **Error cases**: Duplicate name (409), non-existent user (401)
- **Boundary**: Empty name (422), name exceeds max length (422), invalid URL (422)
- **RBAC**: Verify project:create permission required
- **Multi-tenancy**: Project scopes to user's organization

### 4. Project Retrieval (04_projects_get_by_id.feature)
- **Happy path**: GET returns 200 with all fields
- **Error cases**: Non-existent ID (404), missing auth (401)
- **Boundary**: Invalid UUID format (400)
- **RBAC**: Tenant isolation — cannot access other tenant's project
- **Schema**: Verify all required fields present

### 5. Test Case Creation (05_test_cases_create.feature)
- **Happy path**: POST with valid data returns 201
- **Error cases**: Non-existent project (404), missing auth (401)
- **Boundary**: Empty title (422), invalid priority (422)
- **RBAC**: test_case:create permission required
- **Multi-tenancy**: Test case scopes to tenant

### 6. Test Case Retrieval (06_test_cases_get.feature)
- **Happy path**: GET returns 200 with all fields
- **Error cases**: Non-existent ID (404), missing auth (401)
- **Boundary**: Invalid UUID format (400)
- **RBAC**: Tenant isolation verification
- **Schema**: All required fields present (id, title, project_id, status, priority, created_by)

### 7. Test Execution Trigger (07_test_runs_trigger.feature)
- **Happy path**: POST returns 201 with run_id in queued state
- **Error cases**: Non-existent project (404), empty test case list (422)
- **Boundary**: Invalid environment (422)
- **RBAC**: test_run:create permission required
- **Polling**: Verify run can be queried immediately after trigger

### 8. Test Run Status (08_test_runs_status.feature)
- **Happy path**: GET returns 200 with current status
- **Error cases**: Non-existent run (404), missing auth (401)
- **Boundary**: Invalid UUID format (400)
- **RBAC**: Tenant isolation for run access
- **Status values**: queued, running, passed, failed, error

### 9. Permission Management (09_permissions_rbac.feature)
- **Role hierarchy**: Admin > Manager > Tester > Viewer
- **Permission verification**: admin, project:create, test_case:edit, etc.
- **Cross-role**: Manager cannot delete projects (admin-only)
- **Viewer restrictions**: Can read but not edit test cases
- **Role matrix**: Comprehensive permission mapping

### 10. Cascade Delete (10_cascade_delete.feature)
- **Happy path**: DELETE /projects/{id} returns 204
- **Cascade**: All associated test cases deleted
- **Cascade**: All associated test runs deleted
- **Error cases**: Non-existent project (404), missing auth (401)
- **RBAC**: Admin-only permission
- **Soft delete**: Project archived/inaccessible after deletion

## Test Scenarios by Category

### Smoke Tests (@smoke)
Quick sanity checks for core functionality:
- 01_auth_login: Valid login
- 02_auth_me: User profile
- 03_projects_create: Project creation
- 04_projects_get_by_id: Project retrieval
- 05_test_cases_create: Test case creation
- 06_test_cases_get: Test case retrieval
- 07_test_runs_trigger: Run trigger
- 08_test_runs_status: Run status
- 10_cascade_delete: Soft delete behavior

**Run time**: ~30 seconds

### Critical Tests (@critical)
Core functionality and security-critical paths:
- Authentication failures (401 Unauthorized)
- Authorization failures (403 Forbidden)
- Not found errors (404)
- All permission boundaries

**Run time**: ~45 seconds

### RBAC Tests (@rbac)
Role-Based Access Control verification:
- Admin > Manager > Tester > Viewer permissions
- Permission matrix verification
- Cross-tenant isolation
- Resource ownership validation

**Run time**: ~60 seconds

### Boundary Tests (@boundary)
Input validation and edge cases:
- Empty fields (422 Unprocessable Entity)
- Max length violations
- Invalid enum values
- Malformed data formats

**Run time**: ~30 seconds

### Rate Limiting Tests (@ratelimit)
Brute-force and DoS protection:
- 10 failed login attempts in 5 minutes → 429 Too Many Requests

**Run time**: ~20 seconds (configured with shorter interval for testing)

### Isolation Tests (@isolation)
Multi-tenancy and data isolation:
- User's organization scope
- Cross-tenant access blocking
- RLS verification at database layer

**Run time**: ~30 seconds

## Assertion Patterns

### HTTP Status Codes
```gherkin
Then status 200                  # Success
Then status 201                  # Created
Then status 204                  # No Content
Then status 400                  # Bad Request
Then status 401                  # Unauthorized
Then status 403                  # Forbidden
Then status 404                  # Not Found
Then status 409                  # Conflict
Then status 422                  # Unprocessable Entity
Then status 429                  # Too Many Requests
```

### Response Matching
```gherkin
And match response.id != null                    # Presence
And match response.email == 'admin@example.com' # Exact value
And match response.token_type == 'bearer'       # Case-sensitive string
And match response.roles[*] contains 'admin'    # Array contains
And match response.permissions contains 'read'  # List membership
And match response.status in ['active', 'archived'] # Enum values
And match response.created_at != null           # Timestamp presence
And match response.detail contains 'permission' # Pattern match
```

### Header Assertions
```gherkin
And match responseHeaders['set-cookie'][0] contains 'HttpOnly'
And match responseHeaders['content-type'] == 'application/json'
```

## API Endpoints Tested

| Method | Endpoint | Feature | Status |
|--------|----------|---------|--------|
| POST | /api/v1/auth/login | 01_auth_login | ✓ |
| GET | /api/v1/auth/me | 02_auth_me | ✓ |
| POST | /api/v1/contexts/projects | 03_projects_create | ✓ |
| GET | /api/v1/contexts/projects/{id} | 04_projects_get_by_id | ✓ |
| DELETE | /api/v1/contexts/projects/{id} | 10_cascade_delete | ✓ |
| POST | /api/v1/test-management/test-cases | 05_test_cases_create | ✓ |
| GET | /api/v1/test-management/test-cases/{case_id} | 06_test_cases_get | ✓ |
| POST | /api/v1/test-management/runs/trigger | 07_test_runs_trigger | ✓ |
| GET | /api/v1/test-management/runs/{run_id}/status | 08_test_runs_status | ✓ |
| Authorization layer | RBAC enforcement | 09_permissions_rbac | ✓ |

## Error Handling

### Expected Error Responses

```json
{
  "detail": "Error message in English or Turkish",
  "status": 401
}
```

All endpoints return error details in `response.detail` field. Tests verify:
- Correct HTTP status code
- Error message presence
- Error message content (for security-relevant errors)

## Extending the Test Suite

### Adding a New Feature File

1. Create `features/NN_<feature_name>.feature`
2. Define scenarios with BDD syntax
3. Include `@smoke`, `@critical`, `@rbac`, or `@boundary` tags
4. Use standard assertion patterns from existing tests

### Example Feature Template

```gherkin
Feature: New Endpoint Tests
  Background:
    * url baseUrl
    * def token = testUsers.admin

  @smoke @critical
  Scenario: Test new happy path
    Given path '/api/v1/endpoint'
    And header Authorization = 'Bearer ' + token
    When method post
    Then status 201
    And match response.id != null
```

### Using Helper Functions

```gherkin
Given path '/api/v1/users'
And request { name: 'Test ' + java.lang.System.currentTimeMillis() }
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Karate API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-java@v2
        with:
          java-version: '11'
      - name: Run Karate tests
        run: |
          cd backend
          mvn test -Dtest=TestRunner \
            -Dbase.url=http://localhost:8000 \
            -Dkarate.threads=5
      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: karate-report
          path: target/karate-reports/
```

### Jenkins Pipeline Example

```groovy
stage('API Tests') {
  steps {
    dir('backend') {
      sh '''
        mvn test -Dtest=TestRunner \
          -Dbase.url=${API_URL} \
          -Dkarate.threads=5
      '''
    }
  }
  post {
    always {
      junit '**/target/surefire-reports/**/*.xml'
      publishHTML([
        reportDir: 'target/karate-reports',
        reportFiles: 'karate-summary.html'
      ])
    }
  }
}
```

## Troubleshooting

### Tests fail with "Not authenticated"
- Verify test users exist in database
- Check karate-config.js has correct credentials
- Ensure JWT secret is configured consistently

### Rate limit tests fail with 429 immediately
- Rate limit window in auth router is 5 minutes
- Tests that sleep or wait may trigger false positives
- Run rate limit tests in isolation: `mvn test -Dtest=TestRunner -Dkarate.options="--tags @ratelimit"`

### Cross-tenant isolation tests inconclusive
- Requires two separate user accounts from different organizations
- Seed database with multi-tenant test data before running
- Consider parametrizing tests with org_id

### Flaky timing issues in trigger/status tests
- Use `java.lang.Thread.sleep(milliseconds)` between trigger and status check
- Status checks should poll with exponential backoff (500ms → 1s → 2s)
- Set `readTimeout` high enough for slow test environment

## Performance Baselines

| Test Suite | Count | Avg Duration | P95 | P99 |
|-----------|-------|--------------|-----|-----|
| Smoke | 9 | 0.5s | 1.2s | 1.8s |
| Critical | 20 | 1.5s | 3.2s | 4.5s |
| RBAC | 6 | 1.2s | 2.8s | 3.5s |
| **Total** | **~90** | **~60s** | **~120s** | **~150s** |

## References

- [Karate Documentation](https://karatelabs.github.io/karate/)
- [Gherkin/BDD Syntax](https://cucumber.io/docs/gherkin/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP API Security](https://owasp.org/www-project-api-security/)

## Support

For issues, see backend test logs:
```bash
mvn test -Dtest=TestRunner -X   # Enable debug mode
```

Check Karate HTML report:
```
target/karate-reports/karate-summary.html
```
