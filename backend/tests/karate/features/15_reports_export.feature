Feature: Reports and Analytics API

  Background:
    * url baseUrl
    * def adminToken = testTokens.admin
    * def managerToken = testTokens.manager
    * def viewerToken = testTokens.viewer
    * header Authorization = 'Bearer ' + adminToken
    * header Content-Type = 'application/json'

  # ============================================================
  # HAPPY PATH — 200
  # ============================================================

  @smoke @critical
  Scenario: GET /projects/{project_id}/reports/summary — Get execution summary report
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/summary'
    When method get
    Then status 200
    And match response.total_tests >= 0
    And match response.passed_count >= 0
    And match response.failed_count >= 0
    And match response.execution_time_seconds >= 0

  @medium @smoke
  Scenario: GET /projects/{project_id}/reports/execution-timeline — Get timeline data
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/execution-timeline'
    And param days = 30
    When method get
    Then status 200
    And match response[*].date != null
    And match response[*].passed >= 0
    And match response[*].failed >= 0

  @medium
  Scenario: GET /projects/{project_id}/reports/defect-trend — Get defect metrics
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/defect-trend'
    When method get
    Then status 200
    And match response.total_defects >= 0
    And match response.open_count >= 0
    And match response.resolved_count >= 0

  @medium
  Scenario: GET /projects/{project_id}/reports/test-case-coverage — Get test coverage
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/test-case-coverage'
    When method get
    Then status 200
    And match response.total_requirements >= 0
    And match response.covered_count >= 0
    And match response.coverage_percent >= 0
    And assert response.coverage_percent <= 100

  @medium
  Scenario: GET /projects/{project_id}/reports/test-execution-metrics — Get execution metrics
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/test-execution-metrics'
    When method get
    Then status 200
    And match response.total_executions >= 0
    And match response.average_duration_seconds >= 0
    And match response.success_rate >= 0

  @medium
  Scenario: GET /projects/{project_id}/reports/team-performance — Get team performance
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/team-performance'
    When method get
    Then status 200
    And match response[*].team_id != null
    And match response[*].tests_executed >= 0
    And match response[*].defects_found >= 0

  # ============================================================
  # EXPORT ENDPOINTS
  # ============================================================

  @high
  Scenario: POST /projects/{project_id}/reports/export/pdf — Export as PDF
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/pdf'
    And request {
      report_type: 'execution_summary',
      date_range: 'last_30_days'
    }
    When method post
    Then status 200
    And match responseHeaders['content-type'] contains 'application/pdf'
    And match responseHeaders['content-disposition'] != null

  @high
  Scenario: POST /projects/{project_id}/reports/export/csv — Export as CSV
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/csv'
    And request {
      data_type: 'test_cases',
      filters: { status: 'approved' }
    }
    When method post
    Then status 200
    And match responseHeaders['content-type'] contains 'text/csv'
    And match responseHeaders['content-disposition'] contains 'attachment'

  @high
  Scenario: POST /projects/{project_id}/reports/export/xlsx — Export as Excel
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/xlsx'
    And request {
      report_type: 'defect_analysis'
    }
    When method post
    Then status 200
    And match responseHeaders['content-type'] contains 'spreadsheetml'

  @high
  Scenario: POST /projects/{project_id}/reports/export/json — Export as JSON
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/json'
    And request {
      report_type: 'full_report',
      include_attachments: false
    }
    When method post
    Then status 200
    And match responseHeaders['content-type'] contains 'application/json'

  # ============================================================
  # ERROR CASES — 400/403/404/422
  # ============================================================

  @boundary
  Scenario: POST /projects/{project_id}/reports/export/pdf — Invalid report type returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/pdf'
    And request {
      report_type: 'invalid_type',
      date_range: 'last_30_days'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/reports/export/csv — Invalid data type returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/csv'
    And request {
      data_type: 'invalid_type'
    }
    When method post
    Then status 422

  @boundary
  Scenario: GET /projects/{project_id}/reports/summary — Invalid project returns 404
    Given path '/api/v1/projects/nonexistent-id/reports/summary'
    When method get
    Then status 404

  @boundary
  Scenario: GET /projects/{project_id}/reports/execution-timeline — Invalid days parameter
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/execution-timeline'
    And param days = -5
    When method get
    Then status 400 || status 422

  @boundary
  Scenario: GET /projects/{project_id}/reports/execution-timeline — Days too large
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/execution-timeline'
    And param days = 3650
    When method get
    Then status 400 || status 422

  # ============================================================
  # RBAC & PERMISSION TESTS
  # ============================================================

  @medium @permission
  Scenario: GET /projects/{project_id}/reports/summary — Viewer can view reports
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/reports/summary'
    When method get
    Then status 200 || status 403

  @medium @permission
  Scenario: POST /projects/{project_id}/reports/export/pdf — Only members can export
    Given header Authorization = 'Bearer ' + testData.otherUserToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/pdf'
    And request {
      report_type: 'execution_summary',
      date_range: 'last_30_days'
    }
    When method post
    Then status 403

  # ============================================================
  # TENANT ISOLATION
  # ============================================================

  @critical @security
  Scenario: GET /projects/{project_id}/reports/summary — Cross-tenant access denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/reports/summary'
    When method get
    Then status 403 || status 404

  @critical @security
  Scenario: POST /projects/{project_id}/reports/export/pdf — Cross-tenant export denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/pdf'
    And request {
      report_type: 'execution_summary',
      date_range: 'last_30_days'
    }
    When method post
    Then status 403 || status 404

  # ============================================================
  # FILTERING & PARAMETERS
  # ============================================================

  @smoke
  Scenario: GET /projects/{project_id}/reports/execution-timeline — Filter by environment
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/execution-timeline'
    And param environment = 'staging'
    When method get
    Then status 200

  @smoke
  Scenario: GET /projects/{project_id}/reports/team-performance — Filter by team
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/team-performance'
    And param team_id = testData.currentTeamId
    When method get
    Then status 200

  @smoke
  Scenario: POST /projects/{project_id}/reports/export/csv — Filter by date range
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/csv'
    And request {
      data_type: 'test_runs',
      filters: {
        date_from: '2024-01-01',
        date_to: '2024-12-31'
      }
    }
    When method post
    Then status 200

  # ============================================================
  # PERFORMANCE & STRESS
  # ============================================================

  @performance
  Scenario: GET /projects/{project_id}/reports/summary — Response time < 2s
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/summary'
    When method get
    Then status 200
    And assert responseTime < 2000

  @performance
  Scenario: POST /projects/{project_id}/reports/export/csv — Large export completes
    Given path '/api/v1/projects/' + testData.currentProjectId + '/reports/export/csv'
    And request {
      data_type: 'test_cases',
      filters: {}
    }
    When method post
    Then status 200
    And assert responseTime < 30000
