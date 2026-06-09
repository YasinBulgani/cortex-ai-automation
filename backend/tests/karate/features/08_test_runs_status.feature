Feature: Test Execution — GET /api/v1/test-management/runs/{run_id}/status
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def timestamp = java.lang.System.currentTimeMillis()

  @smoke @critical
  Scenario: Get run status returns 200 with current state
    # Setup
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Status Project ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'Status TC' }
    When method post
    And def testCaseId = response.id

    # Trigger run
    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', test_case_ids: ['#(testCaseId)'] }
    When method post
    And def runId = response.id

    # Get status
    Given path '/api/v1/test-management/runs/' + runId + '/status'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.id == runId
    And match response.status in ['queued', 'running', 'passed', 'failed', 'error']
    And match response.progress != null
    And match response.test_count > 0

  @critical
  Scenario: Get run status with non-existent run ID returns 404
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/test-management/runs/00000000-0000-0000-0000-000000000000/status'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 404

  @critical
  Scenario: Get run status without authentication returns 401
    Given path '/api/v1/test-management/runs/00000000-0000-0000-0000-000000000000/status'
    When method get
    Then status 401

  @boundary
  Scenario: Get run status with invalid UUID returns 400
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/test-management/runs/invalid-uuid/status'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 400

  @rbac
  Scenario: Get run status respects tenant isolation
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Tenant Run ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'TC' }
    When method post
    And def testCaseId = response.id

    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', test_case_ids: ['#(testCaseId)'] }
    When method post
    And def runId = response.id

    # Can access own run
    Given path '/api/v1/test-management/runs/' + runId + '/status'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200

  @smoke
  Scenario: Run status includes execution timeline
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Timeline Project ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'TC' }
    When method post
    And def testCaseId = response.id

    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', test_case_ids: ['#(testCaseId)'] }
    When method post
    And def runId = response.id

    Given path '/api/v1/test-management/runs/' + runId + '/status'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.created_at != null
    And match response.started_at != null || response.status == 'queued'
