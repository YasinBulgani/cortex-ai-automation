Feature: Test Case Management — POST /api/v1/test-management/test-cases
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def timestamp = java.lang.System.currentTimeMillis()

  @smoke @critical
  Scenario: Create test case with valid data returns 201
    # Login
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    # Create project first
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'TC Project ' + timestamp }
    When method post
    And def projectId = response.id

    # Create test case
    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request
      """
      {
        project_id: '#(projectId)',
        title: 'Login Test ' + #(timestamp),
        description: 'Test login flow',
        priority: 'high',
        status: 'active',
        steps: [
          { step_number: 1, action: 'Navigate to login page', expected_result: 'Page loads' },
          { step_number: 2, action: 'Enter credentials', expected_result: 'Form accepts input' }
        ]
      }
      """
    When method post
    Then status 201
    And match response.id != null
    And match response.title contains 'Login Test'
    And match response.project_id == '#(projectId)'
    And def testCaseId = response.id

  @critical
  Scenario: Create test case without authentication returns 401
    Given path '/api/v1/test-management/test-cases'
    And request { project_id: '00000000-0000-0000-0000-000000000000', title: 'Test' }
    When method post
    Then status 401

  @critical
  Scenario: Create test case with non-existent project returns 404
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '00000000-0000-0000-0000-000000000000', title: 'Test' }
    When method post
    Then status 404

  @boundary
  Scenario: Create test case with empty title returns 422
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Empty Title Test ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: '' }
    When method post
    Then status 422

  @boundary
  Scenario: Create test case with invalid priority returns 422
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Priority Test ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'Test', priority: 'invalid_priority' }
    When method post
    Then status 422

  @rbac
  Scenario: Create test case requires test_case:create permission
    # Admin users should have this permission
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'RBAC Test ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'RBAC Test Case' }
    When method post
    Then status 201

  @isolation
  Scenario: Test case creation scopes to authenticated user's tenant
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Isolation Test ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + token
    And request { project_id: '#(projectId)', title: 'Isolated TC' }
    When method post
    Then status 201
    And match response.tenant_id != null
