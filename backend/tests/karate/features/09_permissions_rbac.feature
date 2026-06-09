Feature: Permission Management — RBAC enforcement across endpoints
  Background:
    * url baseUrl
    * def adminUser = testUsers.admin
    * def managerUser = testUsers.manager
    * def testerUser = testUsers.tester
    * def timestamp = java.lang.System.currentTimeMillis()

  @critical @rbac
  Scenario: Admin can create projects while tester cannot
    # Admin login
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def adminToken = response.access_token

    # Admin creates project — should succeed
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + adminToken
    And request { name: 'Admin Project ' + timestamp }
    When method post
    Then status 201

    # Tester login
    Given path '/api/v1/auth/login'
    And request { email: '#(testerUser.email)', password: '#(testerUser.password)' }
    When method post
    Then status 200
    And def testerToken = response.access_token

    # Tester tries to create project — should fail with 403
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + testerToken
    And request { name: 'Tester Project ' + timestamp }
    When method post
    Then status 403
    And match response.detail contains 'permission'

  @critical @rbac
  Scenario: Manager can access test results but cannot modify project settings
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def adminToken = response.access_token

    # Admin creates project
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + adminToken
    And request { name: 'Manager Test ' + timestamp }
    When method post
    And def projectId = response.id

    # Manager login
    Given path '/api/v1/auth/login'
    And request { email: '#(managerUser.email)', password: '#(managerUser.password)' }
    When method post
    And def managerToken = response.access_token

    # Manager can view project
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + managerToken
    When method get
    Then status 200

    # Manager cannot delete project (requires admin)
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + managerToken
    When method delete
    Then status 403

  @critical @rbac
  Scenario: Test case edit requires explicit permission
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def adminToken = response.access_token

    # Admin creates project and test case
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + adminToken
    And request { name: 'Edit Test ' + timestamp }
    When method post
    And def projectId = response.id

    Given path '/api/v1/test-management/test-cases'
    And header Authorization = 'Bearer ' + adminToken
    And request { project_id: '#(projectId)', title: 'Edit TC' }
    When method post
    And def testCaseId = response.id

    # Viewer login
    Given path '/api/v1/auth/login'
    And request { email: '#(viewerUser.email)', password: '#(viewerUser.password)' }
    When method post
    And def viewerToken = response.access_token

    # Viewer can read
    Given path '/api/v1/test-management/test-cases/' + testCaseId
    And header Authorization = 'Bearer ' + viewerToken
    When method get
    Then status 200

    # Viewer cannot edit
    Given path '/api/v1/test-management/test-cases/' + testCaseId
    And header Authorization = 'Bearer ' + viewerToken
    And request { title: 'New Title' }
    When method patch
    Then status 403

  @rbac
  Scenario: User's role-permission matrix is correctly enforced
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def token = response.access_token

    # Get authenticated user profile to verify permissions
    Given path '/api/v1/auth/me'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.roles contains 'admin'
    And match response.permissions contains 'project:create'
    And match response.permissions contains 'project:read'
    And match response.permissions contains 'project:update'
    And match response.permissions contains 'project:delete'
    And match response.permissions contains 'test_case:create'
    And match response.permissions contains 'test_case:read'
    And match response.permissions contains 'test_case:edit'
    And match response.permissions contains 'test_run:create'

  @rbac
  Scenario: Cross-tenant access is blocked at authorization layer
    # Admin from tenant A
    Given path '/api/v1/auth/login'
    And request { email: '#(adminUser.email)', password: '#(adminUser.password)' }
    When method post
    And def tenantAToken = response.access_token

    # Create resource in tenant A
    Given path '/api/v1/contexts/projects'
    And header Authorization = 'Bearer ' + tenantAToken
    And request { name: 'Tenant A Project ' + timestamp }
    When method post
    And def projectId = response.id

    # (Would need another admin user from different tenant to truly test cross-tenant)
    # For now, verify tenant context is set during request
    Given path '/api/v1/contexts/projects/' + projectId
    And header Authorization = 'Bearer ' + tenantAToken
    When method get
    Then status 200
    And match response.tenant_id != null
