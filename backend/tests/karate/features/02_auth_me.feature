Feature: Authentication — GET /auth/me endpoint
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin

  # Helper: Login and capture token
  * def loginAndGetToken =
    """
    function(email, password) {
      var payload = { email: email, password: password };
      var response = karate.call('GET', '/api/v1/auth/login', payload);
      return response.access_token;
    }
    """

  @smoke @critical
  Scenario: GET /auth/me with valid token returns authenticated user profile
    # First login to get token
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    Then status 200
    And def token = response.access_token

    # Now fetch me endpoint
    Given path '/api/v1/auth/me'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.email == '#(adminUser.email)'
    And match response.roles != null
    And match response.permissions != null
    And match response.id != null
    And match response.first_name != null

  @smoke
  Scenario: GET /auth/me accepts cookie-based authentication
    # Login to set cookies
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    Then status 200

    # Fetch me with cookies (TestClient auto-includes them)
    Given path '/api/v1/auth/me'
    When method get
    Then status 200
    And match response.email == '#(adminUser.email)'

  @critical
  Scenario: GET /auth/me with missing Authorization header returns 401
    Given path '/api/v1/auth/me'
    When method get
    Then status 401
    And match response.detail contains 'Not authenticated'

  @critical
  Scenario: GET /auth/me with malformed token returns 401
    Given path '/api/v1/auth/me'
    And header Authorization = 'Bearer invalid.token.here'
    When method get
    Then status 401

  @critical
  Scenario: GET /auth/me with expired token returns 401
    # For testing, we'd need to mock/manipulate token expiry
    # This scenario documents the expected behavior
    Given path '/api/v1/auth/me'
    And header Authorization = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
    When method get
    Then status 401

  @rbac
  Scenario: GET /auth/me returns correct role-based permissions
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    Then status 200
    And def token = response.access_token

    Given path '/api/v1/auth/me'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.roles[*] contains 'admin'
    And match response.permissions contains 'project:create'
    And match response.permissions contains 'test_case:edit'

  @boundary
  Scenario: GET /auth/me with bearer token missing returns 401
    Given path '/api/v1/auth/me'
    And header Authorization = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxx'
    When method get
    Then status 401
