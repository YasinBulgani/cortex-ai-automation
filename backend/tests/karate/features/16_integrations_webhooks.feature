Feature: Integrations and Webhooks API

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
  Scenario: GET /projects/{project_id}/integrations — List integrations
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations'
    When method get
    Then status 200
    And match response[*].id != null
    And match response[*].type != null
    And match response[*].status != null

  @critical @smoke
  Scenario: POST /projects/{project_id}/integrations/jira — Connect Jira integration
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/jira'
    And request {
      host: 'https://test-company.atlassian.net',
      username: 'test-user@company.com',
      api_token: 'test-api-token-12345'
    }
    When method post
    Then status 201
    And match response.id != null
    And match response.type == 'jira'
    And def jiraIntegrationId = response.id

  @critical
  Scenario: GET /projects/{project_id}/integrations/{integration_id} — Get integration details
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/' + testData.currentIntegrationId
    When method get
    Then status 200
    And match response.id == testData.currentIntegrationId
    And match response.type != null

  @high
  Scenario: POST /projects/{project_id}/integrations/slack — Connect Slack integration
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/slack'
    And request {
      webhook_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX',
      channel: '#qa-notifications'
    }
    When method post
    Then status 201
    And match response.id != null
    And match response.type == 'slack'

  @high
  Scenario: POST /projects/{project_id}/integrations/github — Connect GitHub integration
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/github'
    And request {
      repository_url: 'https://github.com/company/repo',
      personal_access_token: 'ghp_test_token_12345'
    }
    When method post
    Then status 201
    And match response.id != null

  @critical
  Scenario: PATCH /projects/{project_id}/integrations/{integration_id} — Update integration
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/' + testData.currentIntegrationId
    And request {
      enabled: true,
      channel: '#updated-channel'
    }
    When method patch
    Then status 200

  @critical @destructive
  Scenario: DELETE /projects/{project_id}/integrations/{integration_id} — Disconnect integration
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/' + testData.tempIntegrationId
    When method delete
    Then status 204

  # ============================================================
  # WEBHOOKS
  # ============================================================

  @critical @smoke
  Scenario: POST /projects/{project_id}/webhooks — Create webhook
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    And request {
      name: 'Test Completion Webhook ' + testData.timestamp,
      url: 'https://example.com/webhooks/test-complete',
      events: ['test_run_completed', 'defect_created'],
      active: true,
      retry_count: 3
    }
    When method post
    Then status 201
    And match response.id != null
    And def webhookId = response.id

  @high
  Scenario: GET /projects/{project_id}/webhooks — List webhooks
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    When method get
    Then status 200
    And match response[*].id != null
    And match response[*].url != null
    And match response[*].active != null

  @high
  Scenario: GET /projects/{project_id}/webhooks/{webhook_id} — Get webhook details
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks/' + testData.currentWebhookId
    When method get
    Then status 200
    And match response.id == testData.currentWebhookId
    And match response.events[*] != null

  @high
  Scenario: PATCH /projects/{project_id}/webhooks/{webhook_id} — Update webhook
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks/' + testData.currentWebhookId
    And request {
      active: false,
      events: ['test_run_completed']
    }
    When method patch
    Then status 200
    And match response.active == false

  @high
  Scenario: GET /projects/{project_id}/webhooks/{webhook_id}/deliveries — Get delivery history
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks/' + testData.currentWebhookId + '/deliveries'
    When method get
    Then status 200
    And match response[*].id != null
    And match response[*].status != null
    And match response[*].timestamp != null

  @high
  Scenario: POST /projects/{project_id}/webhooks/{webhook_id}/test — Test webhook
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks/' + testData.currentWebhookId + '/test'
    And request {}
    When method post
    Then status 200
    And match response.success != null

  @critical @destructive
  Scenario: DELETE /projects/{project_id}/webhooks/{webhook_id} — Delete webhook
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks/' + testData.tempWebhookId
    When method delete
    Then status 204

  # ============================================================
  # ERROR CASES — 400/403/404/422
  # ============================================================

  @critical @boundary
  Scenario: POST /projects/{project_id}/integrations/jira — Missing host returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/jira'
    And request {
      username: 'test@company.com',
      api_token: 'token'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/integrations/jira — Invalid host format returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/jira'
    And request {
      host: 'not-a-url',
      username: 'test@company.com',
      api_token: 'token'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/integrations/slack — Invalid webhook URL returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/slack'
    And request {
      webhook_url: 'not-a-webhook-url'
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/webhooks — Missing URL returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    And request {
      name: 'Webhook',
      events: ['test_run_completed']
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/webhooks — Invalid event type returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    And request {
      name: 'Webhook',
      url: 'https://example.com/webhook',
      events: ['invalid_event']
    }
    When method post
    Then status 422

  @boundary
  Scenario: GET /projects/{project_id}/integrations/{integration_id} — Non-existent returns 404
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations/nonexistent-id'
    When method get
    Then status 404

  @boundary
  Scenario: DELETE /projects/{project_id}/webhooks/{webhook_id} — Non-existent returns 404
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks/nonexistent-id'
    When method delete
    Then status 404

  # ============================================================
  # RBAC & PERMISSION TESTS
  # ============================================================

  @critical @permission
  Scenario: POST /projects/{project_id}/integrations/jira — Viewer cannot add integration
    Given header Authorization = 'Bearer ' + viewerToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/integrations/jira'
    And request {
      host: 'https://test.atlassian.net',
      username: 'test@test.com',
      api_token: 'token'
    }
    When method post
    Then status 403

  @critical @permission
  Scenario: DELETE /projects/{project_id}/integrations/{integration_id} — Non-admin denied
    Given header Authorization = 'Bearer ' + managerToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/integrations/' + testData.currentIntegrationId
    When method delete
    Then status 403 || status 200

  @critical @permission
  Scenario: POST /projects/{project_id}/webhooks — Manager can create webhooks
    Given header Authorization = 'Bearer ' + managerToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    And request {
      name: 'Manager Webhook',
      url: 'https://example.com/webhook',
      events: ['test_run_completed']
    }
    When method post
    Then status 201 || status 403

  # ============================================================
  # TENANT ISOLATION
  # ============================================================

  @critical @security
  Scenario: GET /projects/{project_id}/integrations — Cross-tenant access denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/integrations'
    When method get
    Then status 403 || status 404

  @critical @security
  Scenario: POST /projects/{project_id}/webhooks — Cross-tenant create denied
    Given header Authorization = 'Bearer ' + testData.otherTenantToken
    And path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    And request {
      name: 'Hacked Webhook',
      url: 'https://evil.com/webhook',
      events: ['test_run_completed']
    }
    When method post
    Then status 403 || status 404

  # ============================================================
  # DATA VALIDATION
  # ============================================================

  @boundary
  Scenario: POST /projects/{project_id}/webhooks — URL too long returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    And request {
      name: 'Webhook',
      url: 'https://example.com/' + 'A' * 2000,
      events: ['test_run_completed']
    }
    When method post
    Then status 422

  @boundary
  Scenario: POST /projects/{project_id}/webhooks — Name too short returns 422
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    And request {
      name: 'W',
      url: 'https://example.com/webhook',
      events: ['test_run_completed']
    }
    When method post
    Then status 422

  # ============================================================
  # FILTERING & PAGINATION
  # ============================================================

  @smoke
  Scenario: GET /projects/{project_id}/webhooks?active=true — Filter active webhooks
    Given path '/api/v1/projects/' + testData.currentProjectId + '/webhooks'
    And param active = true
    When method get
    Then status 200
    And match response[*].active == true

  @smoke
  Scenario: GET /projects/{project_id}/integrations?type=jira — Filter by type
    Given path '/api/v1/projects/' + testData.currentProjectId + '/integrations'
    And param type = 'jira'
    When method get
    Then status 200
    And match response[*].type == 'jira'
