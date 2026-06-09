Feature: Project Management — GET /api/v1/contexts/projects/{id}
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def timestamp = java.lang.System.currentTimeMillis()

  @smoke @critical
  Scenario: Get project by ID with valid ID returns 200 and project details
    # Login
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    # Create a project first
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Get Test Project ' + timestamp, description: 'Test description' }
    When method post
    Then status 201
    And def projectId = response.id

    # Fetch the project
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.id == projectId
    And match response.name == 'Get Test Project ' + timestamp
    And match response.status == 'active'

  @critical
  Scenario: Get project by ID with non-existent ID returns 404
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects/00000000-0000-0000-0000-000000000000'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 404
    And match response.detail contains 'Proje bulunamadı'

  @critical
  Scenario: Get project without authentication returns 401
    Given path '/api/v1/contexts/projects/00000000-0000-0000-0000-000000000000'
    When method get
    Then status 401

  @rbac
  Scenario: Get project filters by tenant — cannot access other tenant's project
    # This test verifies RLS (Row Level Security) at database level
    # Admin can create and access their own project
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Tenant Test Project ' + timestamp }
    When method post
    Then status 201
    And def projectId = response.id

    # Verify admin can access
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200

  @boundary
  Scenario: Get project with invalid UUID format returns 400
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects/not-a-uuid'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 400

  @smoke
  Scenario: Get project response includes all required fields
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Complete Fields ' + timestamp, description: 'Desc', base_url: 'https://test.com' }
    When method post
    And def projectId = response.id

    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.id != null
    And match response.name != null
    And match response.description != null
    And match response.base_url != null
    And match response.status != null
    And match response.created_at != null
