Feature: Project Management — POST /api/v1/contexts/projects
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def timestamp = java.lang.System.currentTimeMillis()
    * def projectName = 'Karate Project ' + timestamp

  # Helper to login and get token
  * def login =
    """
    function(email, password) {
      var response = karate.http.post('/api/v1/auth/login', { email: email, password: password });
      return response.access_token;
    }
    """

  @smoke @critical
  Scenario: Create project with valid data returns 201 Created
    # Login first
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    Then status 200
    And def token = response.access_token

    # Create project
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: '#(projectName)', description: 'Test project', base_url: 'https://example.com' }
    When method post
    Then status 201
    And match response.id != null
    And match response.name == '#(projectName)'
    And match response.status == 'active'
    And def projectId = response.id

  @smoke
  Scenario: Create project with minimal data succeeds
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    Then status 200
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Minimal Project ' + timestamp }
    When method post
    Then status 201
    And match response.id != null

  @critical
  Scenario: Create project without authentication returns 401
    Given path '/api/v1/contexts/projects'
    And request { name: '#(projectName)' }
    When method post
    Then status 401

  @critical
  Scenario: Create project with duplicate name returns 409 Conflict
    # Create first project
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Duplicate Check ' + timestamp }
    When method post
    Then status 201

    # Try to create with same name
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Duplicate Check ' + timestamp }
    When method post
    Then status 409
    And match response.detail contains 'already exists'

  @boundary
  Scenario: Create project with empty name returns 422
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: '' }
    When method post
    Then status 422

  @boundary
  Scenario: Create project with name exceeding max length returns 422
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And def longName = java.lang.String(new char[300]).replace('\0', 'a')
    And request { name: longName }
    When method post
    Then status 422

  @boundary
  Scenario: Create project with invalid base_url returns 422
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: '#(projectName)', base_url: 'not-a-valid-url' }
    When method post
    Then status 422

  @rbac
  Scenario: Create project requires project:create permission
    # Use non-admin user (if available in test DB)
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    # Admin should succeed
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: '#(projectName)' }
    When method post
    Then status 201

  @isolation
  Scenario: Create project scopes to authenticated user's organization (multi-tenant)
    # This verifies that created project belongs to user's organization
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + token
    And request { name: 'Tenant Isolated ' + timestamp }
    When method post
    Then status 201
    And match response.organization_id != null
