Feature: Team Management API

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
  Scenario: GET /organizations/{org_id}/teams — List teams
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams'
    When method get
    Then status 200
    And match response[*].id != null
    And match response[*].name != null

  @critical @smoke
  Scenario: POST /organizations/{org_id}/teams — Create team
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams'
    And request {
      name: 'QA Team ' + testData.timestamp,
      description: 'Quality Assurance Team'
    }
    When method post
    Then status 201
    And match response.id != null
    And def teamId = response.id

  @critical
  Scenario: GET /organizations/{org_id}/teams/{team_id} — Get team by ID
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId
    When method get
    Then status 200
    And match response.id == testData.currentTeamId
    And match response.name != null

  @critical @smoke
  Scenario: PATCH /organizations/{org_id}/teams/{team_id} — Update team
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId
    And request {
      name: 'Updated QA Team',
      description: 'Updated description'
    }
    When method patch
    Then status 200
    And match response.name == 'Updated QA Team'

  @high
  Scenario: GET /organizations/{org_id}/teams/{team_id}/members — List team members
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId + '/members'
    When method get
    Then status 200
    And match response[*].user_id != null
    And match response[*].role != null

  @high
  Scenario: POST /organizations/{org_id}/teams/{team_id}/members — Add member to team
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId + '/members'
    And request {
      user_id: testData.existingUserId,
      role: 'member'
    }
    When method post
    Then status 201
    And match response.user_id == testData.existingUserId

  @high
  Scenario: DELETE /organizations/{org_id}/teams/{team_id}/members/{member_id} — Remove member
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId + '/members/' + testData.existingMemberId
    When method delete
    Then status 204

  @critical @destructive
  Scenario: DELETE /organizations/{org_id}/teams/{team_id} — Delete team
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.tempTeamId
    When method delete
    Then status 204

  # ============================================================
  # ERROR CASES — 400/403/404/409/422
  # ============================================================

  @critical @boundary
  Scenario: POST /organizations/{org_id}/teams — Duplicate name returns 409
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams'
    And request {
      name: 'Existing Team',
      description: 'Duplicate'
    }
    When method post
    Then status 409

  @boundary
  Scenario: POST /organizations/{org_id}/teams — Empty name returns 422
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams'
    And request {
      name: '',
      description: 'Empty name'
    }
    When method post
    Then status 422

  @boundary
  Scenario: GET /organizations/{org_id}/teams/{team_id} — Non-existent team returns 404
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/nonexistent-id'
    When method get
    Then status 404

  @boundary
  Scenario: POST /organizations/{org_id}/teams/{team_id}/members — Invalid user_id returns 400
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId + '/members'
    And request {
      user_id: 'nonexistent-user',
      role: 'member'
    }
    When method post
    Then status 400 || status 404

  @boundary
  Scenario: POST /organizations/{org_id}/teams/{team_id}/members — Invalid role returns 422
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId + '/members'
    And request {
      user_id: testData.existingUserId,
      role: 'invalid_role'
    }
    When method post
    Then status 422

  # ============================================================
  # RBAC & PERMISSION TESTS
  # ============================================================

  @critical @permission
  Scenario: POST /organizations/{org_id}/teams — Non-admin cannot create team
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/organizations/' + testData.currentOrgId + '/teams'
    And request {
      name: 'Unauthorized Team',
      description: 'Should fail'
    }
    When method post
    Then status 403

  @critical @permission
  Scenario: PATCH /organizations/{org_id}/teams/{team_id} — Non-admin cannot edit team
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId
    And request { name: 'Hacked Name' }
    When method patch
    Then status 403

  @critical @permission
  Scenario: DELETE /organizations/{org_id}/teams/{team_id} — Non-admin cannot delete
    Given header Authorization = 'Bearer ' + managerToken
    And path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId
    When method delete
    Then status 403

  @permission
  Scenario: POST /organizations/{org_id}/teams/{team_id}/members — Manager can add members
    Given header Authorization = 'Bearer ' + managerToken
    And path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId + '/members'
    And request {
      user_id: testData.existingUserId,
      role: 'member'
    }
    When method post
    Then status 201 || status 403

  # ============================================================
  # TENANT ISOLATION
  # ============================================================

  @critical @security
  Scenario: GET /organizations/{org_id}/teams — Cross-tenant access denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/organizations/' + testData.currentOrgId + '/teams'
    When method get
    Then status 403 || status 404

  @critical @security
  Scenario: PATCH /organizations/{org_id}/teams/{team_id} — Cross-tenant edit denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/organizations/' + testData.currentOrgId + '/teams/' + testData.currentTeamId
    And request { name: 'Hacked' }
    When method patch
    Then status 403 || status 404

  # ============================================================
  # DATA VALIDATION
  # ============================================================

  @boundary
  Scenario: POST /organizations/{org_id}/teams — Name too long returns 422
    Given path '/api/v1/organizations/' + testData.currentOrgId + '/teams'
    And request {
      name: 'A' * 300,
      description: 'Long name'
    }
    When method post
    Then status 422
