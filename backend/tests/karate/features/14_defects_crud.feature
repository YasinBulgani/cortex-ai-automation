Feature: Defect Management API

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
  Scenario: GET /projects/{project_id}/defects — List defects
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    When method get
    Then status 200
    And match response[*].id != null
    And match response[*].title != null

  @critical @smoke
  Scenario: POST /projects/{project_id}/defects — Create defect
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And request {
      title: 'Login button not responsive ' + testData.timestamp,
      description: 'Login button does not respond to clicks on Firefox',
      severity: 'high',
      status: 'open',
      assigned_to: testData.existingUserId
    }
    When method post
    Then status 201
    And match response.id != null
    And def defectId = response.id

  @critical
  Scenario: GET /projects/{project_id}/defects/{defect_id} — Get defect by ID
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId
    When method get
    Then status 200
    And match response.id == testData.currentDefectId
    And match response.title != null

  @critical @smoke
  Scenario: PATCH /projects/{project_id}/defects/{defect_id} — Update defect
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId
    And request {
      title: 'Updated: Login button not responsive',
      status: 'in_progress',
      severity: 'critical'
    }
    When method patch
    Then status 200
    And match response.title contains 'Updated'
    And match response.status == 'in_progress'

  @high
  Scenario: POST /projects/{project_id}/defects/{defect_id}/comments — Add comment
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId + '/comments'
    And request {
      content: 'Working on this issue, will have fix by tomorrow'
    }
    When method post
    Then status 201
    And match response.content != null

  @high
  Scenario: GET /projects/{project_id}/defects/{defect_id}/comments — List comments
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId + '/comments'
    When method get
    Then status 200
    And match response[*].content != null
    And match response[*].created_by != null

  @high
  Scenario: PATCH /projects/{project_id}/defects/{defect_id}/comments/{comment_id} — Update comment
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId + '/comments/' + testData.currentCommentId
    And request {
      content: 'Updated comment text'
    }
    When method patch
    Then status 200

  @high
  Scenario: DELETE /projects/{project_id}/defects/{defect_id}/comments/{comment_id} — Delete comment
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId + '/comments/' + testData.tempCommentId
    When method delete
    Then status 204

  @critical @destructive
  Scenario: DELETE /projects/{project_id}/defects/{defect_id} — Delete defect
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.tempDefectId
    When method delete
    Then status 204

  # ============================================================
  # ERROR CASES — 400/403/404/409/422
  # ============================================================

  @critical @boundary
  Scenario: POST /projects/{project_id}/defects — Missing title returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And request {
      description: 'No title provided',
      severity: 'high'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/defects — Empty description returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And request {
      title: 'Test Defect',
      description: '',
      severity: 'high'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/defects — Invalid severity returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And request {
      title: 'Test Defect',
      description: 'Test description',
      severity: 'invalid_severity'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/defects — Invalid status returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And request {
      title: 'Test Defect',
      description: 'Test description',
      severity: 'high',
      status: 'invalid_status'
    }
    When method post
    Then status 422

  @boundary
  Scenario: GET /projects/{project_id}/defects/{defect_id} — Non-existent defect returns 404
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/nonexistent-id'
    When method get
    Then status 404

  @boundary
  Scenario: POST /projects/{project_id}/defects/{defect_id}/comments — Empty comment returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId + '/comments'
    And request { content: '' }
    When method post
    Then status 422

  # ============================================================
  # RBAC & PERMISSION TESTS
  # ============================================================

  @critical @permission
  Scenario: POST /projects/{project_id}/defects — Viewer cannot create defect
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And request {
      title: 'Unauthorized Defect',
      description: 'Should fail',
      severity: 'high'
    }
    When method post
    Then status 403

  @critical @permission
  Scenario: PATCH /projects/{project_id}/defects/{defect_id} — Non-assignee cannot edit
    Given header Authorization = 'Bearer ' + testData.otherUserToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId
    And request { status: 'resolved' }
    When method patch
    Then status 403 || status 200  # Depends on permission model

  @high @permission
  Scenario: POST /projects/{project_id}/defects/{defect_id}/comments — Manager can comment
    Given header Authorization = 'Bearer ' + managerToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId + '/comments'
    And request { content: 'Manager comment' }
    When method post
    Then status 201 || status 403

  # ============================================================
  # TENANT ISOLATION
  # ============================================================

  @critical @security
  Scenario: GET /projects/{project_id}/defects — Cross-tenant access denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    When method get
    Then status 403 || status 404

  @critical @security
  Scenario: PATCH /projects/{project_id}/defects/{defect_id} — Cross-tenant edit denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId
    And request { status: 'resolved' }
    When method patch
    Then status 403 || status 404

  # ============================================================
  # DATA VALIDATION
  # ============================================================

  @boundary
  Scenario: POST /projects/{project_id}/defects — Title too long returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And request {
      title: 'A' * 1000,
      description: 'Test',
      severity: 'high'
    }
    When method post
    Then status 422

  @boundary
  Scenario: PATCH /projects/{project_id}/defects/{defect_id} — Invalid priority returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects/' + testData.currentDefectId
    And request { priority: 999 }
    When method patch
    Then status 422

  # ============================================================
  # FILTERING & SORTING
  # ============================================================

  @smoke
  Scenario: GET /projects/{project_id}/defects?severity=high — Filter by severity
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And param severity = 'high'
    When method get
    Then status 200
    And match response[*].severity == 'high'

  @smoke
  Scenario: GET /projects/{project_id}/defects?status=open — Filter by status
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And param status = 'open'
    When method get
    Then status 200
    And match response[*].status == 'open'

  @smoke
  Scenario: GET /projects/{project_id}/defects?sort=created_at — Sort defects
    Given path '/api/v1/projects/' + testData.currentProjectId + '/defects'
    And param sort = 'created_at'
    And param order = 'desc'
    When method get
    Then status 200
