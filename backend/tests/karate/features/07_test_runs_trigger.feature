Feature: Test Execution — POST /api/v1/test-management/runs/trigger
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def timestamp = java.lang.System.currentTimeMillis()

  @smoke @critical
  Scenario: Trigger test run with valid test case IDs returns 201
    # Setup: Login, create project, create test case
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Run Project ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'Run TC ' + timestamp }
    When method post
    And def testCaseId = response.id

    # Trigger run
    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request
      """
      {
        project_id: '#(projectId)',
        test_case_ids: ['#(testCaseId)'],
        environment: 'dev',
        browser: 'chrome'
      }
      """
    When method post
    Then status 201
    And match response.id != null
    And match response.status == 'queued'
    And match response.project_id == projectId
    And def runId = response.id

  @critical
  Scenario: Trigger run without authentication returns 401
    Given path '/api/v1/test-management/runs/trigger'
    And request { project_id: '00000000-0000-0000-0000-000000000000', test_case_ids: [] }
    When method post
    Then status 401

  @critical
  Scenario: Trigger run with non-existent project returns 404
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '00000000-0000-0000-0000-000000000000', test_case_ids: [] }
    When method post
    Then status 404

  @boundary
  Scenario: Trigger run with empty test_case_ids returns 422
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Empty Cases ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', test_case_ids: [] }
    When method post
    Then status 422

  @boundary
  Scenario: Trigger run with invalid environment returns 422
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Env Test ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'TC' }
    When method post
    And def testCaseId = response.id

    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', test_case_ids: ['#(testCaseId)'], environment: 'invalid_env' }
    When method post
    Then status 422

  @rbac
  Scenario: Trigger run requires test_run:create permission
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'RBAC Run ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'TC' }
    When method post
    And def testCaseId = response.id

    # Admin should succeed
    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', test_case_ids: ['#(testCaseId)'] }
    When method post
    Then status 201

  @smoke
  Scenario: Triggered run can be queried immediately after creation
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Query Run ' + timestamp }
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

    # Immediately query the run
    Given path '/api/v1/test-management/runs/' + runId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.id == runId
