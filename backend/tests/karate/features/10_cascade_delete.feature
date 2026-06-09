Feature: Cascade Delete — DELETE /api/v1/contexts/projects/{id}
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def timestamp = java.lang.System.currentTimeMillis()

  @critical
  Scenario: Delete project cascades to delete all associated test cases
    # Setup: Login, create project, create multiple test cases
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Cascade Delete Project ' + timestamp }
    When method post
    And def projectId = response.id

    # Create test case 1
    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'TC1 ' + timestamp }
    When method post
    And def testCaseId1 = response.id

    # Create test case 2
    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'TC2 ' + timestamp }
    When method post
    And def testCaseId2 = response.id

    # Verify test cases exist
    Given path '/api/v1/test-management/test-cases/' + testCaseId1
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200

    Given path '/api/v1/test-management/test-cases/' + testCaseId2
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200

    # Delete project
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + token
    When method delete
    Then status 204

    # Verify project is gone
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 404

    # Verify test cases are also gone
    Given path '/api/v1/test-management/test-cases/' + testCaseId1
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 404

    Given path '/api/v1/test-management/test-cases/' + testCaseId2
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 404

  @critical
  Scenario: Delete project cascades to delete test runs and results
    # Setup
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Cascade Runs Project ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'Cascade TC' }
    When method post
    And def testCaseId = response.id

    # Trigger test run
    Given path '/api/v1/test-management/runs/trigger'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', test_case_ids: ['#(testCaseId)'] }
    When method post
    And def runId = response.id

    # Verify run exists
    Given path '/api/v1/test-management/runs/' + runId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200

    # Delete project
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + token
    When method delete
    Then status 204

    # Verify run is also gone
    Given path '/api/v1/test-management/runs/' + runId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 404

  @critical
  Scenario: Delete project without authentication returns 401
    Given path '/api/v1/contexts/projects/00000000-0000-0000-0000-000000000000'
    When method delete
    Then status 401

  @critical
  Scenario: Delete project with non-existent ID returns 404
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects/00000000-0000-0000-0000-000000000000'
    And header Authorization = 'Bearer ' + token
    When method delete
    Then status 404

  @rbac
  Scenario: Delete project requires admin permission
    # Admin should succeed
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def adminToken = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + adminToken
    And request { name: 'Admin Delete ' + timestamp }
    When method post
    And def projectId = response.id

    # Tester tries to delete — should fail
    Given path '/api/v1/auth/login'
    And request { email: '#(testerUser.email)', password: '#(testerUser.password)' }
    When method post
    And def testerToken = response.access_token

    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + testerToken
    When method delete
    Then status 403

    # Admin can delete
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + adminToken
    When method delete
    Then status 204

  @boundary
  Scenario: Delete project with invalid UUID returns 400
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects/not-a-uuid'
    And header Authorization = 'Bearer ' + token
    When method delete
    Then status 400

  @smoke
  Scenario: Delete soft-deletes project (archived state)
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Soft Delete ' + timestamp }
    When method post
    And def projectId = response.id

    # Delete
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + token
    When method delete
    Then status 204

    # Project should be inaccessible (soft deleted)
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 404
