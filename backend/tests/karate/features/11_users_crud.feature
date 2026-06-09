Feature: User Management API

  Background:
    * url baseUrl
    * def adminToken = testTokens.admin
    * def managerToken = testTokens.manager
    * def viewerToken = testTokens.viewer
    * header Authorization = 'Bearer ' + adminToken
    * header Content-Type = 'application/json'

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
    And match response.total_count >= 0
    And match response.items[0].id != null
    And match response.items[0].email != null
    And assert response.items.length <= 10

  @smoke
  Scenario: GET /users?status=active — Filter active users
    Given path '/api/v1/users'
    And param status = 'active'
    When method get
    Then status 200
    And match response.total_count >= 0

  @critical @smoke
  Scenario: GET /users/{user_id} — Get user by ID
    Given path '/api/v1/users/' + testData.existingUserId
    When method get
    Then status 200
    And match response.id == testData.existingUserId
    And match response.email != null

  @critical @smoke
  Scenario: POST /users — Admin creates new user
    Given path '/api/v1/users'
    And request {
      email: 'newuser-' + testData.timestamp + '@example.com',
      first_name: 'New',
      last_name: 'User',
      roles: ['viewer']
    }
    When method post
    Then status 201
    And match response.id != null
    And match response.email contains 'newuser-'
    And match response.roles[*] contains 'viewer'

  @critical
  Scenario: PATCH /users/{user_id} — Update user details
    Given path '/api/v1/users/' + testData.existingUserId
    And request {
      first_name: 'Updated',
      last_name: 'User'
    }
    When method patch
    Then status 200
    And match response.first_name == 'Updated'
    And match response.last_name == 'User'

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

  @boundary
  Scenario: POST /users — Empty email returns 422
    Given path '/api/v1/users'
    And request {
      email: '',
      first_name: 'Invalid',
      last_name: 'User'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /users — Invalid email format returns 422
    Given path '/api/v1/users'
    And request {
      email: 'not-an-email',
      first_name: 'Invalid',
      last_name: 'User'
    }
    When method post
    Then status 422

  @boundary
  Scenario: GET /users/{user_id} — Non-existent user returns 404
    Given path '/api/v1/users/nonexistent-id'
    When method get
    Then status 404

  @boundary
  Scenario: POST /users — Missing required field returns 422
    Given path '/api/v1/users'
    And request {
      first_name: 'NoEmail',
      last_name: 'User'
    }
    When method post
    Then status 422

  # ============================================================
  # RBAC & PERMISSION TESTS
  # ============================================================

  @critical @permission
  Scenario: POST /users — Manager cannot create users
    Given header Authorization = 'Bearer ' + managerToken
    And path '/api/v1/users'
    And request {
      email: 'unauthorized-' + testData.timestamp + '@example.com',
      first_name: 'Unauthorized',
      last_name: 'User'
    }
    When method post
    Then status 403

  @critical @permission
  Scenario: PATCH /users/{user_id} — Manager cannot update user
    Given header Authorization = 'Bearer ' + managerToken
    And path '/api/v1/users/' + testData.existingUserId
    And request { first_name: 'Hacked' }
    When method patch
    Then status 403

  @permission
  Scenario: GET /users — Viewer has limited visibility
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/users'
    When method get
    Then status 200 || status 403

  # ============================================================
  # DATA VALIDATION
  # ============================================================

  @boundary
  Scenario: POST /users — First name too short returns 422
    Given path '/api/v1/users'
    And request {
      email: 'test-' + testData.timestamp + '@example.com',
      first_name: 'A',
      last_name: 'User'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /users — Invalid role returns 422
    Given path '/api/v1/users'
    And request {
      email: 'test-' + testData.timestamp + '@example.com',
      first_name: 'Test',
      last_name: 'User',
      roles: ['invalid_role']
    }
    When method post
    Then status 422

  # ============================================================
  # PAGINATION & SORTING
  # ============================================================

  @smoke
  Scenario: GET /users — Pagination limit parameter works
    Given path '/api/v1/users'
    And param limit = 5
    And param offset = 0
    When method get
    Then status 200
    And assert response.items.length <= 5
    And match response.limit == 5

  @smoke
  Scenario: GET /users — Offset parameter works
    Given path '/api/v1/users'
    And param limit = 5
    And param offset = 5
    When method get
    Then status 200
    And match response.offset == 5
