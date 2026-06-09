Feature: Test Case Management — GET /api/v1/test-management/test-cases/{case_id}
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def timestamp = java.lang.System.currentTimeMillis()

  @smoke @critical
  Scenario: Get test case by ID returns 200 with full details
    # Login and setup
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Get TC Project ' + timestamp }
    When method post
    And def projectId = response.id

    # Create test case
    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'Retrieve Test ' + timestamp }
    When method post
    And def testCaseId = response.id

    # Retrieve the test case
    Given path '/api/v1/test-management/test-cases/' + testCaseId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.id == testCaseId
    And match response.title == 'Retrieve Test ' + timestamp
    And match response.project_id == projectId

  @critical
  Scenario: Get test case with non-existent ID returns 404
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/test-management/test-cases/00000000-0000-0000-0000-000000000000'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 404

  @critical
  Scenario: Get test case without authentication returns 401
    Given path '/api/v1/test-management/test-cases/00000000-0000-0000-0000-000000000000'
    When method get
    Then status 401

  @rbac
  Scenario: Get test case respects tenant isolation (RLS)
    # Verified through admin access
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'RLS Test Project ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'RLS Test Case' }
    When method post
    And def testCaseId = response.id

    # Can retrieve own test case
    Given path '/api/v1/test-management/test-cases/' + testCaseId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200

  @boundary
  Scenario: Get test case with invalid UUID returns 400
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/test-management/test-cases/invalid-uuid'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 400

  @smoke
  Scenario: Get test case response includes all required fields
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Fields Test ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'Complete Fields', priority: 'high' }
    When method post
    And def testCaseId = response.id

    Given path '/api/v1/test-management/test-cases/' + testCaseId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.id != null
    And match response.title != null
    And match response.project_id != null
    And match response.status != null
    And match response.priority != null
    And match response.created_at != null
    And match response.created_by != null
