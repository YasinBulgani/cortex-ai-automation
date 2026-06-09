Feature: Authentication — Login endpoint
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def managerUser = testUsers.manager

  @smoke @critical
  Scenario: Login with valid admin credentials returns access token
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    Then status 200
    And match response.token_type == 'bearer'
    And match response.access_token != null
    And match response.access_token contains '.'
    And match response.expires_in > 0
    And def adminToken = response.access_token

  @smoke
  Scenario: Login sets HTTP-only secure cookies
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    Then status 200
    And match responseHeaders['set-cookie'][0] contains 'bgts_access_token'
    And match responseHeaders['set-cookie'][0] contains 'HttpOnly'
    And match responseHeaders['set-cookie'][1] contains 'bgts_refresh_token'

  @critical
  Scenario: Login with wrong password returns 401 Unauthorized
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: 'wrongpassword123' }
    When method post
    Then status 401
    And match response.detail contains 'hatalı'

  @critical
  Scenario: Login with non-existent email returns 401
    Given path '/api/v1/auth/login'
    And request { email: 'nonexistent@example.com', password: 'anypassword' }
    When method post
    Then status 401

  @boundary
  Scenario: Login with empty email returns 422 Unprocessable Entity
    Given path '/api/v1/auth/login'
    And request { email: '', password: 'password123' }
    When method post
    Then status 422

  @boundary
  Scenario: Login with missing password returns 422
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)' }
    When method post
    Then status 422

  @boundary
  Scenario: Login with invalid email format returns 422
    Given path '/api/v1/auth/login'
    And request { email: 'not-an-email', password: 'password' }
    When method post
    Then status 422

  @ratelimit
  Scenario: Login rate limiting — 10 failed attempts in 5 minutes triggers 429
    * def credentials = { email: 'admin@example.com', password: 'wrong' }
    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 401

    # 11th attempt should trigger rate limit
    Given path '/api/v1/auth/login'
    And request credentials
    When method post
    Then status 429
    And match response.detail contains 'çok fazla'
