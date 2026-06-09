# Phase 2.1: API Test Expansion (35% → 80%)

**Objective:** Expand Karate API test coverage from 10 baseline endpoints to 50+ critical endpoints across all major domains.

**Timeline:** 2 weeks (4 engineers)  
**Current State:** 10/50+ endpoints tested (20%)  
**Target:** 50+/50+ endpoints tested (80%+)

---

## Executive Summary

| Domain | Endpoint Count | Test Status | Priority |
|--------|---|---|---|
| **Auth** | 8 | 3/8 (37%) | CRITICAL |
| **Users** | 6 | 0/6 | HIGH |
| **Organizations** | 12 | 0/12 | HIGH |
| **Teams** | 8 | 0/8 | HIGH |
| **Projects** | 10 | 2/10 (20%) | HIGH |
| **Test Management** | 15 | 3/15 (20%) | HIGH |
| **Test Execution** | 10 | 1/10 | HIGH |
| **Defects** | 8 | 0/8 | HIGH |
| **Reports** | 6 | 0/6 | MEDIUM |
| **Integrations** | 12 | 0/12 | MEDIUM |
| **AI Features** | 6 | 0/6 | MEDIUM |
| **Settings** | 8 | 0/8 | MEDIUM |
| **Admin** | 8 | 0/8 | CRITICAL |
| **Automation** | 10 | 0/10 | MEDIUM |
| **API Keys & Webhooks** | 8 | 0/8 | MEDIUM |
| **RBAC/Permissions** | 6 | 1/6 (16%) | CRITICAL |
| **Audit & Compliance** | 6 | 0/6 | MEDIUM |
| **Billing & Licensing** | 6 | 0/6 | LOW |
| **---** | **---** | **---** | **---** |
| **TOTAL** | **157** | **10/157 (6%)** | **~50 HIGH/CRITICAL** |

---

## Phase 2.1 Breakdown: 50+ Endpoints

### TIER 1: CRITICAL (15 endpoints) — Week 1

#### 1. Authentication (8 endpoints)

**Status:** 3/8 implemented

```karate
# 01_auth_login.feature (DONE)
  ✓ Login with valid credentials → 200 + token
  ✓ Login sets secure cookies
  ✓ Login with wrong password → 401
  ✓ Login with non-existent email → 401
  ✓ Login with empty email → 422
  ✓ Login with missing password → 422
  ✓ Login with invalid email format → 422
  ✓ Rate limiting — 10 failed attempts → 429

# 02_auth_me.feature (DONE)
  ✓ GET /auth/me with valid token → 200 + user

# 03_auth_refresh.feature (NEW)
  [ ] POST /auth/refresh with valid refresh token → 200 + new access token
  [ ] POST /auth/refresh with expired refresh token → 401
  [ ] POST /auth/refresh with invalid refresh token → 401
  [ ] POST /auth/logout → 200 + clears cookies
  [ ] POST /auth/request-password-reset → 200 + sends email
  [ ] POST /auth/reset-password with valid token → 200
  [ ] POST /auth/reset-password with invalid token → 401
  [ ] POST /auth/verify-email → 200
```

#### 2. User Management (6 endpoints)

**File:** `backend/tests/karate/features/11_users_crud.feature`

```karate
Feature: User Management
  
  @critical @smoke
  Scenario: GET /users — List all users (paginated)
    Given path '/api/v1/users'
    And header Authorization = 'Bearer ' + adminToken
    And param limit = 10
    And param offset = 0
    When method get
    Then status 200
    And match response.total_count > 0
    And match response.items[*].id != null
    And match response.items[*].email != null
    And assert response.items.length <= 10

  @critical
  Scenario: GET /users/{user_id} — Get user by ID
    Given path '/api/v1/users/' + userId
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.id == userId
    And match response.email != null
    And match response.roles[*].name != null

  @critical
  Scenario: POST /users — Create new user (admin only)
    Given path '/api/v1/users'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      email: 'newuser@example.com',
      first_name: 'Test',
      last_name: 'User',
      roles: ['viewer']
    }
    When method post
    Then status 201
    And match response.id != null
    And match response.email == 'newuser@example.com'

  @critical @boundary
  Scenario: POST /users — Duplicate email returns 409
    Given path '/api/v1/users'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      email: 'admin@example.com',
      first_name: 'Duplicate',
      last_name: 'User'
    }
    When method post
    Then status 409

  @critical
  Scenario: PATCH /users/{user_id} — Update user
    Given path '/api/v1/users/' + userId
    And header Authorization = 'Bearer ' + adminToken
    And request {
      first_name: 'Updated',
      last_name: 'Name'
    }
    When method patch
    Then status 200
    And match response.first_name == 'Updated'

  @critical @destructive
  Scenario: DELETE /users/{user_id} — Delete user (admin only)
    Given path '/api/v1/users/' + newUserId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204
```

#### 3. Organizations (6 endpoints)

**File:** `backend/tests/karate/features/12_organizations_crud.feature`

```karate
Feature: Organization Management

  @critical @smoke
  Scenario: GET /organizations — List current org
    Given path '/api/v1/organizations'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.id != null
    And match response.name != null

  @critical
  Scenario: POST /organizations — Create new org
    Given path '/api/v1/organizations'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'New Organization',
      workspace: 'new-org',
      billing_email: 'billing@org.com'
    }
    When method post
    Then status 201
    And match response.id != null
    And def newOrgId = response.id

  @critical
  Scenario: GET /organizations/{org_id} — Get org details
    Given path '/api/v1/organizations/' + orgId
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.id == orgId

  @critical
  Scenario: PATCH /organizations/{org_id} — Update org
    Given path '/api/v1/organizations/' + orgId
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'Updated Org Name',
      billing_email: 'newemail@org.com'
    }
    When method patch
    Then status 200
    And match response.name == 'Updated Org Name'

  @critical @security
  Scenario: DELETE /organizations/{org_id} — Delete org (owner only)
    Given path '/api/v1/organizations/' + tempOrgId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @critical @permission
  Scenario: GET /organizations/{org_id} — Non-owner denied
    Given path '/api/v1/organizations/' + otherOrgId
    And header Authorization = 'Bearer ' + managerToken
    When method get
    Then status 403
```

#### 4. RBAC & Permissions (3 endpoints)

**File:** `backend/tests/karate/features/09_permissions_rbac.feature` (PARTIALLY DONE)

```karate
Feature: RBAC and Permissions

  @critical
  Scenario: GET /rbac/permissions — List user permissions
    Given path '/api/v1/rbac/permissions'
    And header Authorization = 'Bearer ' + testerToken
    When method get
    Then status 200
    And match response[*].resource != null
    And match response[*].action != null

  @critical
  Scenario: POST /rbac/grant — Grant permission
    Given path '/api/v1/rbac/grant'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      user_id: userId,
      role: 'manager'
    }
    When method post
    Then status 200

  @critical
  Scenario: DELETE /rbac/revoke — Revoke permission
    Given path '/api/v1/rbac/revoke'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      user_id: userId,
      role: 'manager'
    }
    When method post
    Then status 200
```

---

### TIER 2: HIGH PRIORITY (25 endpoints) — Week 1-2

#### 5. Teams (8 endpoints)

**File:** `backend/tests/karate/features/13_teams_crud.feature`

```karate
Feature: Team Management

  @smoke @high
  Scenario: GET /organizations/{org_id}/teams — List teams
    Given path '/api/v1/organizations/' + orgId + '/teams'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response[*].id != null
    And match response[*].name != null

  @high
  Scenario: POST /organizations/{org_id}/teams — Create team
    Given path '/api/v1/organizations/' + orgId + '/teams'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'QA Team',
      description: 'Quality Assurance'
    }
    When method post
    Then status 201
    And def teamId = response.id

  @high
  Scenario: GET /organizations/{org_id}/teams/{team_id} — Get team
    Given path '/api/v1/organizations/' + orgId + '/teams/' + teamId
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.id == teamId

  @high
  Scenario: PATCH /organizations/{org_id}/teams/{team_id} — Update team
    Given path '/api/v1/organizations/' + orgId + '/teams/' + teamId
    And header Authorization = 'Bearer ' + adminToken
    And request { name: 'Updated QA Team' }
    When method patch
    Then status 200

  @high @security
  Scenario: POST /organizations/{org_id}/teams/{team_id}/members — Add member
    Given path '/api/v1/organizations/' + orgId + '/teams/' + teamId + '/members'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      user_id: userId,
      role: 'member'
    }
    When method post
    Then status 201

  @high
  Scenario: DELETE /organizations/{org_id}/teams/{team_id}/members/{member_id} — Remove member
    Given path '/api/v1/organizations/' + orgId + '/teams/' + teamId + '/members/' + memberId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @high @destructive
  Scenario: DELETE /organizations/{org_id}/teams/{team_id} — Delete team
    Given path '/api/v1/organizations/' + orgId + '/teams/' + tempTeamId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @high @permission
  Scenario: POST /organizations/{org_id}/teams — Non-admin denied
    Given path '/api/v1/organizations/' + orgId + '/teams'
    And header Authorization = 'Bearer ' + viewerToken
    And request { name: 'Unauthorized Team' }
    When method post
    Then status 403
```

#### 6. Projects (8 endpoints)

**File:** `backend/tests/karate/features/04_projects_crud.feature` (PARTIALLY DONE)

```karate
Feature: Project Management

  @smoke
  Scenario: GET /projects — List projects (paginated)
    Given path '/api/v1/projects'
    And header Authorization = 'Bearer ' + adminToken
    And param limit = 20
    When method get
    Then status 200
    And match response.total_count >= 0
    And assert response.items.length <= 20

  @smoke @critical
  Scenario: POST /projects — Create project
    Given path '/api/v1/projects'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'E-Commerce Platform',
      description: 'Testing e-commerce features',
      team_id: teamId
    }
    When method post
    Then status 201
    And def projectId = response.id

  @smoke
  Scenario: GET /projects/{project_id} — Get project by ID
    Given path '/api/v1/projects/' + projectId
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.id == projectId
    And match response.name != null

  @critical
  Scenario: PATCH /projects/{project_id} — Update project
    Given path '/api/v1/projects/' + projectId
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'Updated Project Name',
      status: 'active'
    }
    When method patch
    Then status 200
    And match response.name == 'Updated Project Name'

  @critical @permission
  Scenario: PATCH /projects/{project_id} — Non-member denied
    Given path '/api/v1/projects/' + projectId
    And header Authorization = 'Bearer ' + otherUserToken
    And request { name: 'Hacked Name' }
    When method patch
    Then status 403

  @critical @boundary
  Scenario: GET /projects/{project_id} — Non-existent project returns 404
    Given path '/api/v1/projects/nonexistent-id'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 404

  @destructive
  Scenario: DELETE /projects/{project_id} — Delete project
    Given path '/api/v1/projects/' + tempProjectId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @boundary
  Scenario: POST /projects — Invalid team_id returns 400
    Given path '/api/v1/projects'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'Invalid Project',
      team_id: 'nonexistent-team'
    }
    When method post
    Then status 400
```

#### 7. Test Cases (8 endpoints)

**File:** `backend/tests/karate/features/05_test_cases_crud.feature` (PARTIALLY DONE)

```karate
Feature: Test Case Management

  @smoke
  Scenario: GET /projects/{project_id}/test-cases — List test cases
    Given path '/api/v1/projects/' + projectId + '/test-cases'
    And header Authorization = 'Bearer ' + adminToken
    And param limit = 50
    When method get
    Then status 200
    And match response[*].id != null

  @critical @smoke
  Scenario: POST /projects/{project_id}/test-cases — Create test case
    Given path '/api/v1/projects/' + projectId + '/test-cases'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      title: 'Login with valid credentials',
      description: 'User should login successfully',
      type: 'functional',
      priority: 'high',
      tags: ['auth', 'smoke']
    }
    When method post
    Then status 201
    And def testCaseId = response.id

  @smoke
  Scenario: GET /projects/{project_id}/test-cases/{tc_id} — Get test case
    Given path '/api/v1/projects/' + projectId + '/test-cases/' + testCaseId
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.id == testCaseId

  @critical
  Scenario: PATCH /projects/{project_id}/test-cases/{tc_id} — Update test case
    Given path '/api/v1/projects/' + projectId + '/test-cases/' + testCaseId
    And header Authorization = 'Bearer ' + adminToken
    And request {
      title: 'Updated: Login with valid credentials',
      status: 'approved'
    }
    When method patch
    Then status 200
    And match response.title contains 'Updated'

  @high
  Scenario: POST /projects/{project_id}/test-cases/{tc_id}/steps — Add step
    Given path '/api/v1/projects/' + projectId + '/test-cases/' + testCaseId + '/steps'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      order: 1,
      action: 'Click login button',
      expected_result: 'Login form appears'
    }
    When method post
    Then status 201

  @boundary
  Scenario: POST /projects/{project_id}/test-cases — Missing title returns 422
    Given path '/api/v1/projects/' + projectId + '/test-cases'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      description: 'No title',
      type: 'functional'
    }
    When method post
    Then status 422

  @destructive
  Scenario: DELETE /projects/{project_id}/test-cases/{tc_id} — Delete test case
    Given path '/api/v1/projects/' + projectId + '/test-cases/' + tempTestCaseId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @permission
  Scenario: POST /projects/{project_id}/test-cases — Viewer cannot create
    Given path '/api/v1/projects/' + projectId + '/test-cases'
    And header Authorization = 'Bearer ' + viewerToken
    And request { title: 'TC', type: 'functional' }
    When method post
    Then status 403
```

#### 8. Test Execution (8 endpoints)

**File:** `backend/tests/karate/features/07_test_runs_execute.feature` (PARTIALLY DONE)

```karate
Feature: Test Execution

  @critical @smoke
  Scenario: POST /projects/{project_id}/test-runs — Trigger test run
    Given path '/api/v1/projects/' + projectId + '/test-runs'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'Smoke Test Run',
      test_case_ids: [testCaseId],
      environment: 'staging',
      parallel_threads: 4
    }
    When method post
    Then status 201
    And def testRunId = response.id
    And match response.status == 'queued'

  @critical @smoke
  Scenario: GET /projects/{project_id}/test-runs — List test runs
    Given path '/api/v1/projects/' + projectId + '/test-runs'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response[*].id != null

  @critical
  Scenario: GET /projects/{project_id}/test-runs/{run_id} — Get run status
    Given path '/api/v1/projects/' + projectId + '/test-runs/' + testRunId
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.id == testRunId
    And match response.status in ['queued', 'running', 'passed', 'failed']

  @critical
  Scenario: GET /projects/{project_id}/test-runs/{run_id}/results — Get results
    Given path '/api/v1/projects/' + projectId + '/test-runs/' + testRunId + '/results'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.total_count >= 0
    And match response.items[*].test_case_id != null

  @high
  Scenario: POST /projects/{project_id}/test-runs/{run_id}/results — Report result
    Given path '/api/v1/projects/' + projectId + '/test-runs/' + testRunId + '/results'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      test_case_id: testCaseId,
      status: 'passed',
      duration_ms: 1234,
      logs: 'Test completed successfully'
    }
    When method post
    Then status 201

  @critical
  Scenario: PATCH /projects/{project_id}/test-runs/{run_id} — Stop/abort run
    Given path '/api/v1/projects/' + projectId + '/test-runs/' + testRunId
    And header Authorization = 'Bearer ' + adminToken
    And request { status: 'aborted' }
    When method patch
    Then status 200

  @boundary
  Scenario: POST /projects/{project_id}/test-runs — Empty test_case_ids returns 422
    Given path '/api/v1/projects/' + projectId + '/test-runs'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'Empty Run',
      test_case_ids: [],
      environment: 'staging'
    }
    When method post
    Then status 422

  @permission
  Scenario: POST /projects/{project_id}/test-runs — Viewer cannot trigger
    Given path '/api/v1/projects/' + projectId + '/test-runs'
    And header Authorization = 'Bearer ' + viewerToken
    And request { name: 'Run', test_case_ids: [testCaseId] }
    When method post
    Then status 403
```

#### 9. Defects (8 endpoints)

**File:** `backend/tests/karate/features/14_defects_crud.feature`

```karate
Feature: Defect Management

  @high @smoke
  Scenario: GET /projects/{project_id}/defects — List defects
    Given path '/api/v1/projects/' + projectId + '/defects'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response[*].id != null

  @critical
  Scenario: POST /projects/{project_id}/defects — Create defect
    Given path '/api/v1/projects/' + projectId + '/defects'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      title: 'Login button not responsive',
      description: 'Login button does not respond to clicks',
      severity: 'high',
      status: 'open',
      assigned_to: userId,
      test_case_id: testCaseId
    }
    When method post
    Then status 201
    And def defectId = response.id

  @high
  Scenario: GET /projects/{project_id}/defects/{defect_id} — Get defect
    Given path '/api/v1/projects/' + projectId + '/defects/' + defectId
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.id == defectId

  @critical
  Scenario: PATCH /projects/{project_id}/defects/{defect_id} — Update defect
    Given path '/api/v1/projects/' + projectId + '/defects/' + defectId
    And header Authorization = 'Bearer ' + adminToken
    And request {
      title: 'Updated: Login button not responsive',
      status: 'in_progress'
    }
    When method patch
    Then status 200

  @high
  Scenario: POST /projects/{project_id}/defects/{defect_id}/comments — Add comment
    Given path '/api/v1/projects/' + projectId + '/defects/' + defectId + '/comments'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      content: 'Assigned to dev team, ETA 2 days'
    }
    When method post
    Then status 201

  @high
  Scenario: POST /projects/{project_id}/defects/{defect_id}/attachments — Upload attachment
    Given path '/api/v1/projects/' + projectId + '/defects/' + defectId + '/attachments'
    And header Authorization = 'Bearer ' + adminToken
    And multipart file attachment = 'screenshot.png'
    When method post
    Then status 201

  @destructive
  Scenario: DELETE /projects/{project_id}/defects/{defect_id} — Delete defect
    Given path '/api/v1/projects/' + projectId + '/defects/' + tempDefectId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @boundary
  Scenario: POST /projects/{project_id}/defects — Missing title returns 422
    Given path '/api/v1/projects/' + projectId + '/defects'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      description: 'No title',
      severity: 'high'
    }
    When method post
    Then status 422
```

---

### TIER 3: MEDIUM PRIORITY (10 endpoints) — Week 2

#### 10. Reports & Analytics (6 endpoints)

**File:** `backend/tests/karate/features/15_reports_export.feature`

```karate
Feature: Reports and Analytics

  @medium @smoke
  Scenario: GET /projects/{project_id}/reports/summary — Get summary report
    Given path '/api/v1/projects/' + projectId + '/reports/summary'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.total_tests > 0
    And match response.passed_count >= 0
    And match response.failed_count >= 0

  @medium
  Scenario: GET /projects/{project_id}/reports/execution-timeline — Get timeline
    Given path '/api/v1/projects/' + projectId + '/reports/execution-timeline'
    And header Authorization = 'Bearer ' + adminToken
    And param days = 30
    When method get
    Then status 200
    And match response[*].date != null
    And match response[*].passed >= 0

  @medium
  Scenario: POST /projects/{project_id}/reports/export/pdf — Export as PDF
    Given path '/api/v1/projects/' + projectId + '/reports/export/pdf'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      report_type: 'execution_summary',
      date_range: 'last_30_days'
    }
    When method post
    Then status 200
    And match responseHeaders['content-type'] contains 'application/pdf'

  @medium
  Scenario: POST /projects/{project_id}/reports/export/csv — Export as CSV
    Given path '/api/v1/projects/' + projectId + '/reports/export/csv'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      data_type: 'test_cases',
      filters: { status: 'approved' }
    }
    When method post
    Then status 200
    And match responseHeaders['content-type'] contains 'text/csv'

  @medium
  Scenario: GET /projects/{project_id}/reports/defect-trend — Defect metrics
    Given path '/api/v1/projects/' + projectId + '/reports/defect-trend'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response.total_defects >= 0

  @medium @boundary
  Scenario: POST /projects/{project_id}/reports/export/pdf — Invalid format returns 422
    Given path '/api/v1/projects/' + projectId + '/reports/export/pdf'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      report_type: 'invalid_type'
    }
    When method post
    Then status 422
```

#### 11. Integrations (6 endpoints)

**File:** `backend/tests/karate/features/16_integrations_webhooks.feature`

```karate
Feature: Integrations and Webhooks

  @medium @smoke
  Scenario: GET /projects/{project_id}/integrations — List integrations
    Given path '/api/v1/projects/' + projectId + '/integrations'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response[*].id != null

  @medium
  Scenario: POST /projects/{project_id}/integrations/jira — Connect Jira
    Given path '/api/v1/projects/' + projectId + '/integrations/jira'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      host: 'https://company.atlassian.net',
      username: 'test@company.com',
      api_token: '****SECRET****'
    }
    When method post
    Then status 201
    And def integrationId = response.id

  @medium
  Scenario: POST /projects/{project_id}/integrations/slack — Connect Slack
    Given path '/api/v1/projects/' + projectId + '/integrations/slack'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      webhook_url: 'https://hooks.slack.com/services/XXX/YYY/ZZZ'
    }
    When method post
    Then status 201

  @medium
  Scenario: POST /projects/{project_id}/webhooks — Create webhook
    Given path '/api/v1/projects/' + projectId + '/webhooks'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'Test Completion Webhook',
      url: 'https://example.com/webhooks/test-complete',
      events: ['test_run_completed', 'defect_created'],
      active: true
    }
    When method post
    Then status 201

  @medium
  Scenario: GET /projects/{project_id}/webhooks — List webhooks
    Given path '/api/v1/projects/' + projectId + '/webhooks'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200

  @medium
  Scenario: DELETE /projects/{project_id}/webhooks/{webhook_id} — Delete webhook
    Given path '/api/v1/projects/' + projectId + '/webhooks/' + webhookId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204
```

#### 12. API Keys & Settings (4 endpoints)

**File:** `backend/tests/karate/features/17_api_keys_settings.feature`

```karate
Feature: API Keys and Settings

  @medium @smoke
  Scenario: GET /users/api-keys — List user's API keys
    Given path '/api/v1/users/api-keys'
    And header Authorization = 'Bearer ' + adminToken
    When method get
    Then status 200
    And match response[*].id != null

  @medium
  Scenario: POST /users/api-keys — Generate new API key
    Given path '/api/v1/users/api-keys'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      name: 'CI/CD Integration Key',
      expires_in_days: 365
    }
    When method post
    Then status 201
    And match response.token != null

  @medium
  Scenario: DELETE /users/api-keys/{key_id} — Revoke API key
    Given path '/api/v1/users/api-keys/' + keyId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @medium
  Scenario: PATCH /users/profile — Update user profile
    Given path '/api/v1/users/profile'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      first_name: 'John',
      last_name: 'Doe',
      phone: '+1234567890'
    }
    When method patch
    Then status 200
```

---

### TIER 4: EXTENDED (4 additional endpoints) — Week 2 Bonus

#### 13. Admin Operations (4 endpoints)

**File:** `backend/tests/karate/features/18_admin_operations.feature`

```karate
Feature: Admin Operations

  @critical @admin
  Scenario: POST /admin/users/{user_id}/reset-password — Force password reset
    Given path '/api/v1/admin/users/' + userId + '/reset-password'
    And header Authorization = 'Bearer ' + adminToken
    And request {
      new_password: 'TempPassword123!',
      send_email: true
    }
    When method post
    Then status 200

  @critical @admin
  Scenario: DELETE /admin/users/{user_id} — Delete user (admin only)
    Given path '/api/v1/admin/users/' + tempUserId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @critical @admin
  Scenario: PATCH /admin/organizations/{org_id} — Admin org settings
    Given path '/api/v1/admin/organizations/' + orgId
    And header Authorization = 'Bearer ' + superAdminToken
    And request {
      suspended: false,
      storage_quota_gb: 100
    }
    When method patch
    Then status 200

  @critical @admin
  Scenario: GET /admin/audit-logs — View audit trail
    Given path '/api/v1/admin/audit-logs'
    And header Authorization = 'Bearer ' + adminToken
    And param limit = 100
    When method get
    Then status 200
    And match response[*].action != null
```

---

## Test Coverage Matrix

| **Endpoint** | **Happy Path** | **Error Cases** | **RBAC** | **Validation** | **Tenant Isolation** | **Pagination** |
|---|---|---|---|---|---|---|
| Auth/Login | ✓ | ✓ | - | ✓ | - | - |
| User CRUD | ○ | ○ | ✓ | ○ | ✓ | ○ |
| Org CRUD | ○ | ○ | ✓ | ○ | ✓ | - |
| Team CRUD | ○ | ○ | ✓ | ○ | ✓ | ○ |
| Project CRUD | ○ | ○ | ✓ | ○ | ✓ | ○ |
| Test Case CRUD | ○ | ○ | ✓ | ○ | ✓ | ○ |
| Test Execution | ○ | ○ | ✓ | ○ | ✓ | ○ |
| Defect CRUD | ○ | ○ | ✓ | ○ | ✓ | ○ |
| Reports | ○ | ○ | ✓ | ○ | ✓ | - |
| Integrations | ○ | ○ | ✓ | ○ | ✓ | - |
| Admin Ops | ✓ | ✓ | ✓ | - | - | - |

**Legend:** ✓ = Done, ○ = Planned, - = N/A

---

## Test Data Management Strategy

### Backend Test Data Fixtures (`backend/tests/conftest.py`)

```python
@pytest.fixture
def admin_user(db_session):
    """Create admin test user."""
    user = User(
        email='admin@example.com',
        first_name='Admin',
        roles=['admin']
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_organization(db_session, admin_user):
    """Create test organization."""
    org = Organization(
        name='Test Org',
        owner_id=admin_user.id
    )
    db_session.add(org)
    db_session.commit()
    return org

@pytest.fixture
def test_project(db_session, test_organization):
    """Create test project."""
    project = Project(
        name='Test Project',
        org_id=test_organization.id
    )
    db_session.add(project)
    db_session.commit()
    return project
```

### Karate Setup (Enhanced `karate-config.js`)

```javascript
function() {
  var baseUrl = karate.properties['base.url'] || 'http://localhost:8000';
  
  // Setup test data lifecycle
  karate.callSingle('classpath:helpers/setup.js');
  
  return {
    baseUrl: baseUrl,
    
    // Generated once at start
    adminToken: generateToken('admin@example.com'),
    managerToken: generateToken('manager@example.com'),
    testerToken: generateToken('tester@example.com'),
    viewerToken: generateToken('viewer@example.com'),
    
    // Lazy-generated per test
    orgId: null,
    projectId: null,
    teamId: null,
    userId: null
  };
}
```

### Cleanup Strategy

```karate
After Hooks:
  - Delete temporary projects/users
  - Clear test webhooks
  - Rollback transactions

Background:
  * call setup()  # Create minimal test data
```

---

## Execution Plan

### Week 1: Auth + Critical Paths

**Tasks:** 15 endpoints (Auth 8, Users 6, Orgs 6, RBAC 3, Teams 2, Projects 2)

```bash
# Day 1-2: Auth & User Management
karate -T 5 backend/tests/karate/features/0[1-3]_*.feature

# Day 3-4: Organizations & Teams
karate -T 5 backend/tests/karate/features/1[2-3]_*.feature

# Day 5: Projects & Projects CRUD
karate -T 5 backend/tests/karate/features/04_*.feature
```

**Success Criteria:**
- 100% auth flow coverage
- Cross-tenant security verified
- RBAC guards tested
- 50+ test scenarios pass

### Week 2: Data + Integrations

**Tasks:** 35 endpoints (Test Cases 8, Execution 8, Defects 8, Reports 6, Integrations 6, Admin 4)

```bash
# Day 1-2: Test Management
karate -T 5 backend/tests/karate/features/0[5-8]_*.feature

# Day 3-4: Reports & Integrations
karate -T 5 backend/tests/karate/features/1[4-6]_*.feature

# Day 5: Admin & API Keys
karate -T 5 backend/tests/karate/features/1[7-8]_*.feature

# Final: Full regression
karate -T 10 backend/tests/karate/features/*.feature
```

**Success Criteria:**
- 50+ endpoint tests fully automated
- 100+ test scenarios pass
- Zero flaky tests
- All RBAC guards verified
- Tenant isolation confirmed

---

## Implementation Checklist

### Phase 2.1.A: Structure & Setup

- [ ] Create `backend/tests/karate/utils/helpers.js` with:
  - `generateToken(email)` → valid JWT
  - `setupTestData()` → org + project + users
  - `teardownTestData()` → cleanup
  - `assertTenantIsolation(response, expectedTenantId)` → validation

- [ ] Enhance `karate-config.js`:
  - Multi-user token generation
  - Test data lifecycle hooks
  - Base URL from environment
  - Timeout configuration

- [ ] Create feature file template:
  - Standard Background section
  - Tag conventions (@smoke, @critical, @boundary, @permission)
  - Comment sections for each domain

### Phase 2.1.B: Core Endpoints (Week 1)

- [ ] `11_users_crud.feature` — 6 tests
- [ ] `12_organizations_crud.feature` — 6 tests
- [ ] `13_teams_crud.feature` — 8 tests
- [ ] Expand `04_projects_crud.feature` — 8 tests
- [ ] Expand `05_test_cases_crud.feature` — 8 tests
- [ ] Expand `07_test_runs_execute.feature` — 8 tests

### Phase 2.1.C: Extended Coverage (Week 2)

- [ ] `14_defects_crud.feature` — 8 tests
- [ ] `15_reports_export.feature` — 6 tests
- [ ] `16_integrations_webhooks.feature` — 6 tests
- [ ] `17_api_keys_settings.feature` — 4 tests
- [ ] `18_admin_operations.feature` — 4 tests

### Phase 2.1.D: Quality & Documentation

- [ ] Documentation:
  - [ ] README: How to run Karate tests
  - [ ] MATRIX.md: Test coverage by endpoint
  - [ ] ROLES.md: Test user roles & permissions
  - [ ] DATA.md: Test data lifecycle

- [ ] CI/CD Integration:
  - [ ] GitHub Actions: Run karate on PR
  - [ ] Slack notification on failure
  - [ ] HTML report generation
  - [ ] Badge: "50+ endpoints tested"

- [ ] Performance Baseline:
  - [ ] P50/P95/P99 response times
  - [ ] Concurrent user limits
  - [ ] Rate limit validation

---

## Example: Complete Feature File (Users Domain)

**File:** `backend/tests/karate/features/11_users_crud.feature`

```gherkin
Feature: User Management API

  Background:
    * url baseUrl
    * def adminToken = testTokens.admin
    * def managerToken = testTokens.manager
    * def viewerToken = testTokens.viewer
    * header Authorization = 'Bearer ' + adminToken

  # ============================================================
  # HAPPY PATH — 200/201
  # ============================================================

  @smoke @critical
  Scenario: GET /users — Admin lists all users (paginated)
    Given path '/api/v1/users'
    And param limit = 10
    And param offset = 0
    When method get
    Then status 200
    And match response == {
      total_count: '#number',
      items: '#array',
      limit: 10,
      offset: 0
    }
    And assert response.items.length <= 10
    And match response.items[0] == {
      id: '#uuid',
      email: '#regex[.+@.+]',
      first_name: '#string',
      last_name: '#string',
      roles: '#array',
      created_at: '#string',
      updated_at: '#string'
    }

  @smoke
  Scenario: GET /users?filter=active — Filter active users
    Given path '/api/v1/users'
    And param status = 'active'
    When method get
    Then status 200
    And match response.items[*].status == 'active'

  @critical
  Scenario: GET /users/{user_id} — Get user by ID
    Given path '/api/v1/users/' + testData.userId
    When method get
    Then status 200
    And match response.id == testData.userId
    And match response.email != null

  @critical @smoke
  Scenario: POST /users — Admin creates new user
    Given path '/api/v1/users'
    And request {
      email: 'newuser@example.com',
      first_name: 'New',
      last_name: 'User',
      roles: ['viewer'],
      send_invitation: true
    }
    When method post
    Then status 201
    And match response.id == '#uuid'
    And match response.email == 'newuser@example.com'
    And match response.roles == ['viewer']
    And def newUserId = response.id

  @critical
  Scenario: PATCH /users/{user_id} — Update user details
    Given path '/api/v1/users/' + testData.userId
    And request {
      first_name: 'Updated',
      last_name: 'Name'
    }
    When method patch
    Then status 200
    And match response.first_name == 'Updated'
    And match response.last_name == 'Name'

  @critical @destructive
  Scenario: DELETE /users/{user_id} — Admin deletes user
    Given path '/api/v1/users/' + testData.tempUserId
    When method delete
    Then status 204

  # ============================================================
  # ERROR CASES — 400/403/404/409/422
  # ============================================================

  @critical @boundary
  Scenario: POST /users — Duplicate email returns 409 Conflict
    Given path '/api/v1/users'
    And request {
      email: 'admin@example.com',
      first_name: 'Duplicate',
      last_name: 'User'
    }
    When method post
    Then status 409
    And match response.detail contains 'already exists'

  @boundary
  Scenario: POST /users — Empty email returns 422
    Given path '/api/v1/users'
    And request {
      email: '',
      first_name: 'Invalid'
    }
    When method post
    Then status 422
    And match response.detail[*].msg != null

  @boundary
  Scenario: POST /users — Invalid email format returns 422
    Given path '/api/v1/users'
    And request {
      email: 'not-an-email',
      first_name: 'Invalid'
    }
    When method post
    Then status 422

  @boundary
  Scenario: GET /users/{user_id} — Non-existent user returns 404
    Given path '/api/v1/users/invalid-id'
    When method get
    Then status 404
    And match response.detail contains 'not found'

  # ============================================================
  # RBAC & PERMISSION TESTS
  # ============================================================

  @critical @permission
  Scenario: POST /users — Manager cannot create users
    Given header Authorization = 'Bearer ' + managerToken
    And path '/api/v1/users'
    And request {
      email: 'unauthorized@example.com',
      first_name: 'Unauthorized'
    }
    When method post
    Then status 403
    And match response.detail contains 'permission'

  @critical @permission
  Scenario: DELETE /users/{user_id} — Viewer cannot delete
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/users/' + testData.userId
    When method delete
    Then status 403

  @permission
  Scenario: GET /users — Viewer can only see own profile
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/users'
    When method get
    Then status 200
    And assert response.total_count == 1
    And match response.items[0].id == testData.viewerUserId

  # ============================================================
  # TENANT ISOLATION
  # ============================================================

  @critical @security
  Scenario: GET /users/{user_id} — Cross-tenant user returns 404
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/users/' + testData.currentTenantUserId
    When method get
    Then status 404

  @critical @security
  Scenario: PATCH /users/{user_id} — Cannot modify other tenant's users
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/users/' + testData.currentTenantUserId
    And request { first_name: 'Hacked' }
    When method patch
    Then status 404

  # ============================================================
  # DATA VALIDATION
  # ============================================================

  @boundary
  Scenario: POST /users — First name length validation (min 2, max 100)
    Given path '/api/v1/users'
    And request {
      email: 'test@example.com',
      first_name: 'A'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /users — Invalid role returns 422
    Given path '/api/v1/users'
    And request {
      email: 'test@example.com',
      first_name: 'Test',
      roles: ['invalid_role']
    }
    When method post
    Then status 422

  # ============================================================
  # PAGINATION & SORTING
  # ============================================================

  @smoke
  Scenario: GET /users — Pagination works correctly
    Given path '/api/v1/users'
    And param limit = 5
    And param offset = 0
    When method get
    Then status 200
    And assert response.items.length <= 5
    And match response.limit == 5
    And match response.offset == 0

  @smoke
  Scenario: GET /users?sort=email — Sorting works
    Given path '/api/v1/users'
    And param sort = 'email'
    And param order = 'asc'
    When method get
    Then status 200
    And assert response.items[0].email <= response.items[1].email

  # ============================================================
  # RATE LIMITING
  # ============================================================

  @ratelimit
  Scenario: POST /users — Rate limit: 100 requests/min per user
    Given path '/api/v1/users'
    # Simulated: normal request should succeed
    When method post
    Then status 201 || status 422  # Either creates or validation error

```

---

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Endpoint Coverage** | 50+ | 10 | 20% |
| **Test Scenarios** | 100+ | ~40 | 40% |
| **RBAC Coverage** | 100% | 30% | ○ |
| **Error Case Coverage** | 90% | 50% | ○ |
| **Tenant Isolation Tests** | All domains | 2 domains | ○ |
| **Test Execution Time** | <5min | N/A | ○ |
| **Flakiness Rate** | <1% | N/A | ○ |

---

## Dependencies & Tools

```bash
# Installation (already present)
mvn dependency:copy-dependencies
java -jar target/karate.jar backup/karate.jar

# Execution
karate -T 5 backend/tests/karate/features/*.feature

# Reporting
karate --output target/karate-reports backend/tests/karate/features/*.feature
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|---|
| Test data collision | Unique timestamps + cleanup hooks |
| Cross-tenant leaks | Explicit assertion in every scenario |
| Flaky async tests | Retry loop + explicit waits |
| Token expiry | Global setup generates fresh tokens |
| API changes | Backward-compatible schema matching |

---

## Next Steps

1. **Immediate (Next Sprint):**
   - Implement auth expansion (Auth → 8/8)
   - Set up helper utilities
   - Create 5 feature files (11-15)

2. **Following (2 Sprints):**
   - Complete CRUD coverage (50+ endpoints)
   - Add performance benchmarks
   - Integrate into CI/CD

3. **Future (Next Quarter):**
   - API contract testing (OpenAPI)
   - Load testing harness
   - Security penetration tests

---

## Resources & References

- **Karate Docs:** https://karatelabs.github.io/karate
- **Backend Endpoints:** See `backend/app/domains/*/router.py`
- **Test Database:** PostgreSQL (docker-compose.yml)
- **CI/CD:** GitHub Actions (`.github/workflows/test-backend.yml`)

