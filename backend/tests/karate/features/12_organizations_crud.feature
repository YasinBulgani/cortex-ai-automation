Feature: Organization Management API

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
  Scenario: GET /organizations — List current organization
    Given path '/api/v1/organizations'
    When method get
    Then status 200
    And match response.id != null
    And match response.name != null

  @critical @smoke
  Scenario: POST /organizations — Create new organization
    Given path '/api/v1/organizations'
    And request {
      name: 'Test Organization ' + testData.timestamp,
      workspace: 'test-org-' + testData.timestamp,
      billing_email: 'billing-' + testData.timestamp + '@example.com'
    }
    When method post
    Then status 201
    And match response.id != null
    And def orgId = response.id

  @critical
  Scenario: GET /organizations/{org_id} — Get organization by ID
    Given path '/api/v1/organizations/' + testData.currentOrgId
    When method get
    Then status 200
    And match response.id == testData.currentOrgId
    And match response.name != null

  @critical @smoke
  Scenario: PATCH /organizations/{org_id} — Update organization
    Given path '/api/v1/organizations/' + testData.currentOrgId
    And request {
      name: 'Updated Organization',
      billing_email: 'updated-' + testData.timestamp + '@example.com'
    }
    When method patch
    Then status 200
    And match response.name == 'Updated Organization'

  @smoke
  Scenario: GET /organizations/{org_id}/members — List organization members
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/members'
    When method get
    Then status 200
    And match response[*].user_id != null
    And match response[*].role != null

  # ============================================================
  # ERROR CASES — 400/403/404/409/422
  # ============================================================

  @critical @boundary
  Scenario: POST /organizations — Duplicate workspace returns 409
    Given path '/api/v1/organizations'
    And request {
      name: 'Org 1',
      workspace: 'existing-workspace',
      billing_email: 'billing@org.com'
    }
    When method post
    Then status 409

  @boundary
  Scenario: POST /organizations — Empty name returns 422
    Given path '/api/v1/organizations'
    And request {
      name: '',
      workspace: 'test-workspace',
      billing_email: 'billing@org.com'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /organizations — Invalid email returns 422
    Given path '/api/v1/organizations'
    And request {
      name: 'Test Organization',
      workspace: 'test-workspace-' + testData.timestamp,
      billing_email: 'not-an-email'
    }
    When method post
    Then status 422

  @boundary
  Scenario: GET /organizations/{org_id} — Non-existent org returns 404
    Given path '/api/v1/organizations/nonexistent-id'
    When method get
    Then status 404

  @boundary
  Scenario: POST /organizations — Missing required fields returns 422
    Given path '/api/v1/organizations'
    And request {
      name: 'Test Organization'
    }
    When method post
    Then status 422

  # ============================================================
  # RBAC & PERMISSION TESTS
  # ============================================================

  @critical @permission
  Scenario: POST /organizations — Only admins can create org
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/organizations'
    And request {
      name: 'Unauthorized Org',
      workspace: 'unauth-' + testData.timestamp,
      billing_email: 'billing@org.com'
    }
    When method post
    Then status 403

  @critical @permission
  Scenario: PATCH /organizations/{org_id} — Owner can edit
    Given path '/api/v1/organizations/' + testData.currentOrgId
    And request { name: 'Owner Updated Org' }
    When method patch
    Then status 200

  @critical @permission
  Scenario: PATCH /organizations/{org_id} — Non-owner denied
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/organizations/' + testData.otherOrgId
    And request { name: 'Hacked Name' }
    When method patch
    Then status 403

  # ============================================================
  # TENANT ISOLATION
  # ============================================================

  @critical @security
  Scenario: GET /organizations/{org_id} — Cross-tenant access denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/organizations/' + testData.currentOrgId
    When method get
    Then status 403 || status 404

  @critical @security
  Scenario: GET /organizations/{org_id}/members — Cross-tenant access denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/organizations/' + testData.currentOrgId + '/members'
    When method get
    Then status 403 || status 404

  # ============================================================
  # DATA VALIDATION
  # ============================================================

  @boundary
  Scenario: POST /organizations — Workspace too short returns 422
    Given path '/api/v1/organizations'
    And request {
      name: 'Test',
      workspace: 'ab',
      billing_email: 'test@org.com'
    }
    When method post
    Then status 422

  @boundary
  Scenario: PATCH /organizations/{org_id} — Workspace cannot be modified
    Given path '/api/v1/organizations/' + testData.currentOrgId
    And request {
      workspace: 'new-workspace'
    }
    When method patch
    Then status 400 || status 422

  # ============================================================
  # PAGINATION (if applicable)
  # ============================================================

  @smoke
  Scenario: GET /organizations/{org_id}/members — Pagination works
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/members'
    And param limit = 5
    When method get
    Then status 200
