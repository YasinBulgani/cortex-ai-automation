# Regression Suite & Integration Test Blueprint
**Date:** 2026-06-09  
**Target:** 180+ regression test collection  
**Timeline:** 2 weeks (4 engineers)  
**Execution:** Daily regression 45 minutes, 4-worker parallel

---

## Executive Summary

This document defines the complete regression suite for Cortex AI Automation (Neurex) covering:
- **Unit Tests:** 100+ (core modules, services, utilities)
- **API Tests:** 50+ (REST endpoints, contract, integration)
- **UI E2E Tests:** 20 (workflow scenarios × variants)
- **Integration Tests:** 10+ (async, cross-service, DB, notifications)

**Total: 180+ tests** running daily in 45 minutes across 4 workers.

---

## Part 1: Unit Test Collection (100+ tests)

### 1.1 Core Modules (30 tests)

#### Authentication & Security (8 tests)
```
tests/unit/test_auth_service.py
├─ test_hash_password_strength
├─ test_verify_password_correct
├─ test_verify_password_incorrect
├─ test_jwt_token_generation
├─ test_jwt_token_expiration
├─ test_mfa_otp_generation
├─ test_mfa_otp_verification
└─ test_session_revocation

tests/unit/test_permissions.py
├─ test_role_grant_permission
├─ test_role_deny_permission
├─ test_permission_inheritance_hierarchy
├─ test_admin_override_restrictions
└─ test_organization_boundary_enforcement
```

#### Data Models & Schemas (12 tests)
```
tests/unit/test_schemas_validation.py
├─ TestCaseSchema
│  ├─ test_valid_test_case_schema
│  ├─ test_invalid_steps_order
│  ├─ test_missing_required_fields
│  ├─ test_priority_enum_values
│  └─ test_nested_step_validation
├─ ProjectSchema
│  ├─ test_project_key_uniqueness_constraint
│  ├─ test_project_name_max_length
│  ├─ test_invalid_dates
│  └─ test_status_enum_validation
└─ RunSchema
   ├─ test_run_duration_calculation
   ├─ test_run_result_aggregation
   └─ test_run_json_serialization

tests/unit/test_model_relationships.py
├─ test_project_has_many_test_cases
├─ test_test_case_belongs_to_project
├─ test_test_run_has_many_results
├─ test_defect_links_to_test_case
└─ test_user_team_assignment
```

#### Utilities & Helpers (10 tests)
```
tests/unit/test_datetime_helpers.py
├─ test_parse_iso8601_datetime
├─ test_format_datetime_to_utc
├─ test_datetime_zone_conversion
├─ test_datetime_range_calculations
└─ test_datetime_comparison_logic

tests/unit/test_string_helpers.py
├─ test_slug_generation
├─ test_html_escape_unescaping
├─ test_markdown_to_html_conversion
├─ test_string_truncation
└─ test_case_insensitive_search

tests/unit/test_json_helpers.py
├─ test_deep_merge_objects
├─ test_flatten_nested_dict
├─ test_filter_sensitive_keys
└─ test_circular_reference_detection
```

### 1.2 Service Layer (35 tests)

#### Test Management Service (12 tests)
```
tests/unit/test_test_management_service.py
├─ TestCreateTestCase
│  ├─ test_create_with_valid_data
│  ├─ test_create_with_duplicate_title_in_project
│  ├─ test_create_auto_increment_order
│  └─ test_create_sets_tenant_context
├─ TestUpdateTestCase
│  ├─ test_update_partial_fields
│  ├─ test_update_preserves_unchanged_fields
│  ├─ test_update_prevents_project_change
│  └─ test_update_version_increment
├─ TestListTestCases
│  ├─ test_list_with_pagination
│  ├─ test_list_with_filters
│  ├─ test_list_sorted_by_created_date
│  └─ test_list_respects_tenant_boundary
└─ TestDeleteTestCase
   ├─ test_delete_soft_deletes_record
   └─ test_delete_cascades_to_results
```

#### Automation Service (10 tests)
```
tests/unit/test_automation_service.py
├─ TestCreateAutomation
│  ├─ test_create_with_valid_config
│  ├─ test_create_generates_schedule_id
│  └─ test_create_sets_active_status
├─ TestRunAutomation
│  ├─ test_run_returns_execution_id
│  ├─ test_run_validates_input_params
│  ├─ test_run_handles_timeout
│  └─ test_run_stores_execution_history
├─ TestListAutorun
│  ├─ test_list_returns_paginated_results
│  └─ test_list_filters_by_status
└─ TestScheduler
   ├─ test_scheduler_initializes_apscheduler
   └─ test_scheduler_persists_cron_to_db
```

#### Defect Management Service (8 tests)
```
tests/unit/test_defects_service.py
├─ TestCreateDefect
│  ├─ test_create_with_valid_data
│  ├─ test_create_sets_reporter_id
│  ├─ test_create_triggers_notification
│  └─ test_create_links_test_case
├─ TestUpdateDefect
│  ├─ test_update_status_to_resolved
│  └─ test_update_assignee_notifies_user
├─ TestQueryDefects
│  ├─ test_query_by_severity_filter
│  └─ test_query_by_test_case_id
```

#### AI Domain Services (5 tests)
```
tests/unit/test_ai_intelligence_service.py
├─ test_semantic_cache_hit_rate
├─ test_llm_response_formatting
├─ test_ai_model_selection_logic
├─ test_token_counting_accuracy
└─ test_ai_gateway_fallback_chain
```

### 1.3 Domain-Specific Utilities (25 tests)

#### Locator & Selector Helpers (8 tests)
```
tests/unit/test_locator_strategies.py
├─ TestCSSSelector
│  ├─ test_parse_css_selector
│  ├─ test_css_selector_to_xpath
│  └─ test_css_specificity_calculation
├─ TestXPathSelector
│  ├─ test_parse_xpath_expression
│  ├─ test_xpath_attribute_matching
│  └─ test_xpath_text_matching
├─ TestImageLocator
│  ├─ test_image_ocr_extraction
│  └─ test_image_bounding_box_calculation
```

#### BDD & Gherkin Helpers (10 tests)
```
tests/unit/test_gherkin_parser.py
├─ TestFeatureParsing
│  ├─ test_parse_feature_header
│  ├─ test_parse_background_steps
│  ├─ test_parse_scenario_blocks
│  └─ test_extract_tags_from_scenario
├─ TestStepDefinition
│  ├─ test_step_regex_matching
│  ├─ test_step_parameter_extraction
│  ├─ test_step_datatype_coercion
│  └─ test_step_timeout_handling
└─ TestScenarioOutlines
   ├─ test_example_table_expansion
   └─ test_scenario_outline_permutations
```

#### Test Data Generation (7 tests)
```
tests/unit/test_synthetic_data_gen.py
├─ TestRandomDataGeneration
│  ├─ test_generate_random_email
│  ├─ test_generate_random_phone
│  ├─ test_generate_random_credit_card
│  └─ test_pii_masking_compliance
├─ TestBoundaryValueGeneration
│  ├─ test_generate_min_max_values
│  └─ test_generate_boundary_dates
└─ TestCombinatorial
   └─ test_pairwise_test_generation
```

---

## Part 2: API Integration Tests (50+ tests)

### 2.1 Authentication Endpoints (8 tests)

```python
# tests/integration/test_auth_endpoints.py

class TestAuthEndpoints:
    def test_login_valid_credentials(self, client, db_ready):
        """POST /api/v1/auth/login with valid email/password"""
        response = client.post("/api/v1/auth/login", json={
            "email": "admin@example.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "admin@example.com"
        
    def test_login_invalid_credentials(self, client):
        """POST /api/v1/auth/login with wrong password"""
        response = client.post("/api/v1/auth/login", json={
            "email": "admin@example.com",
            "password": "wrong123"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"
        
    def test_login_nonexistent_user(self, client):
        """POST /api/v1/auth/login with unknown email"""
        response = client.post("/api/v1/auth/login", json={
            "email": "unknown@example.com",
            "password": "password"
        })
        assert response.status_code == 401
        
    def test_refresh_token_valid(self, client, admin_token):
        """POST /api/v1/auth/refresh with valid refresh token"""
        # First login
        login_response = client.post("/api/v1/auth/login", json={
            "email": "admin@example.com",
            "password": "admin123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        
    def test_logout_invalidates_session(self, client, auth_headers):
        """POST /api/v1/auth/logout clears session"""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify token is no longer valid
        check = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert check.status_code == 401
        
    def test_mfa_enable_send_otp(self, client, auth_headers):
        """POST /api/v1/auth/mfa/enable sends OTP"""
        response = client.post(
            "/api/v1/auth/mfa/enable",
            headers=auth_headers,
            json={"method": "email"}
        )
        assert response.status_code == 200
        assert response.json()["otp_sent"] is True
        
    def test_mfa_verify_otp(self, client, auth_headers, mocker):
        """POST /api/v1/auth/mfa/verify with OTP code"""
        # Mock OTP service
        mocker.patch("app.domains.auth.service.verify_otp", return_value=True)
        
        response = client.post(
            "/api/v1/auth/mfa/verify",
            headers=auth_headers,
            json={"code": "123456"}
        )
        assert response.status_code == 200
        
    def test_password_reset_request(self, client):
        """POST /api/v1/auth/password-reset sends email"""
        response = client.post(
            "/api/v1/auth/password-reset",
            json={"email": "admin@example.com"}
        )
        assert response.status_code == 200
```

### 2.2 Project Management Endpoints (8 tests)

```python
# tests/integration/test_project_endpoints.py

class TestProjectEndpoints:
    def test_create_project(self, client, admin_token, auth_headers):
        """POST /api/v1/projects creates new project"""
        response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "E2E Test Project",
                "key": "ETP",
                "description": "Integration test project"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "E2E Test Project"
        assert data["key"] == "ETP"
        assert "id" in data
        
    def test_list_projects(self, client, auth_headers):
        """GET /api/v1/projects lists user projects"""
        response = client.get(
            "/api/v1/projects",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json()["items"], list)
        
    def test_get_project_by_id(self, client, auth_headers):
        """GET /api/v1/projects/{id} returns project"""
        # Create first
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"name": "Test", "key": "TST"}
        )
        project_id = create_resp.json()["id"]
        
        # Fetch
        response = client.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == project_id
        
    def test_update_project(self, client, auth_headers):
        """PATCH /api/v1/projects/{id} updates project"""
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"name": "Original", "key": "ORG"}
        )
        project_id = create_resp.json()["id"]
        
        response = client.patch(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
            json={"name": "Updated"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"
        
    def test_delete_project(self, client, auth_headers):
        """DELETE /api/v1/projects/{id} soft-deletes"""
        create_resp = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"name": "ToDelete", "key": "DEL"}
        )
        project_id = create_resp.json()["id"]
        
        response = client.delete(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers
        )
        assert response.status_code == 204
        
        # Verify soft delete
        check = client.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers
        )
        assert check.status_code == 404
        
    def test_project_member_add(self, client, auth_headers):
        """POST /api/v1/projects/{id}/members adds user"""
        response = client.post(
            "/api/v1/projects/proj-001/members",
            headers=auth_headers,
            json={"user_id": "user-123", "role": "tester"}
        )
        assert response.status_code == 201
        
    def test_project_member_remove(self, client, auth_headers):
        """DELETE /api/v1/projects/{id}/members/{userId} removes user"""
        response = client.delete(
            "/api/v1/projects/proj-001/members/user-123",
            headers=auth_headers
        )
        assert response.status_code == 204
        
    def test_project_isolation_cross_tenant(self, client, operator_headers):
        """GET /api/v1/projects forbids cross-tenant access"""
        # Operator tries to access admin's project
        response = client.get(
            "/api/v1/projects/admin-proj-001",
            headers=operator_headers
        )
        assert response.status_code == 403 or response.status_code == 404
```

### 2.3 Test Case Endpoints (8 tests)

```python
# tests/integration/test_testcase_endpoints.py

class TestTestCaseEndpoints:
    def test_create_test_case(self, client, auth_headers):
        """POST /api/v1/test-cases creates new TC"""
        response = client.post(
            "/api/v1/test-cases",
            headers=auth_headers,
            json={
                "project_id": "proj-001",
                "title": "Login with valid credentials",
                "priority": "high",
                "steps": [
                    {"order": 1, "action": "Open login page", "expected": "Login form displayed"},
                    {"order": 2, "action": "Enter email", "expected": "Email accepted"}
                ]
            }
        )
        assert response.status_code == 201
        assert "id" in response.json()
        
    def test_list_test_cases_paginated(self, client, auth_headers):
        """GET /api/v1/test-cases with pagination"""
        response = client.get(
            "/api/v1/test-cases?page=1&limit=20",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) <= 20
        
    def test_list_test_cases_filters(self, client, auth_headers):
        """GET /api/v1/test-cases with filters"""
        response = client.get(
            "/api/v1/test-cases?priority=high&status=active",
            headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        for item in items:
            assert item["priority"] == "high"
            assert item["status"] == "active"
            
    def test_update_test_case(self, client, auth_headers):
        """PATCH /api/v1/test-cases/{id} updates TC"""
        response = client.patch(
            "/api/v1/test-cases/tc-001",
            headers=auth_headers,
            json={"title": "Updated TC Title", "priority": "critical"}
        )
        assert response.status_code == 200
        
    def test_bulk_delete_test_cases(self, client, auth_headers):
        """POST /api/v1/test-cases/bulk-delete removes multiple"""
        response = client.post(
            "/api/v1/test-cases/bulk-delete",
            headers=auth_headers,
            json={"ids": ["tc-001", "tc-002", "tc-003"]}
        )
        assert response.status_code == 200
        
    def test_duplicate_test_case(self, client, auth_headers):
        """POST /api/v1/test-cases/{id}/duplicate clones TC"""
        response = client.post(
            "/api/v1/test-cases/tc-001/duplicate",
            headers=auth_headers
        )
        assert response.status_code == 201
        new_id = response.json()["id"]
        assert new_id != "tc-001"
        
    def test_bulk_update_priority(self, client, auth_headers):
        """POST /api/v1/test-cases/bulk-update changes priority"""
        response = client.post(
            "/api/v1/test-cases/bulk-update",
            headers=auth_headers,
            json={
                "ids": ["tc-001", "tc-002"],
                "priority": "critical"
            }
        )
        assert response.status_code == 200
        
    def test_export_test_cases_csv(self, client, auth_headers):
        """GET /api/v1/test-cases/export?format=csv exports data"""
        response = client.get(
            "/api/v1/test-cases/export?format=csv",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
```

### 2.4 Test Execution Endpoints (8 tests)

```python
# tests/integration/test_execution_endpoints.py

class TestExecutionEndpoints:
    def test_start_test_run(self, client, auth_headers):
        """POST /api/v1/test-runs starts execution"""
        response = client.post(
            "/api/v1/test-runs",
            headers=auth_headers,
            json={
                "project_id": "proj-001",
                "test_case_ids": ["tc-001", "tc-002"],
                "environment": "staging"
            }
        )
        assert response.status_code == 201
        run_id = response.json()["id"]
        assert response.json()["status"] in ["pending", "running"]
        
    def test_list_test_runs(self, client, auth_headers):
        """GET /api/v1/test-runs lists runs"""
        response = client.get(
            "/api/v1/test-runs",
            headers=auth_headers
        )
        assert response.status_code == 200
        
    def test_get_test_run_status(self, client, auth_headers):
        """GET /api/v1/test-runs/{id} returns run details"""
        response = client.get(
            "/api/v1/test-runs/run-001",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "id" in response.json()
        
    def test_submit_test_result(self, client, auth_headers):
        """POST /api/v1/test-runs/{id}/results submits result"""
        response = client.post(
            "/api/v1/test-runs/run-001/results",
            headers=auth_headers,
            json={
                "test_case_id": "tc-001",
                "status": "passed",
                "duration_ms": 5000,
                "notes": "Test completed successfully"
            }
        )
        assert response.status_code == 201
        
    def test_bulk_submit_results(self, client, auth_headers):
        """POST /api/v1/test-runs/{id}/results/bulk submits many"""
        response = client.post(
            "/api/v1/test-runs/run-001/results/bulk",
            headers=auth_headers,
            json={
                "results": [
                    {"test_case_id": "tc-001", "status": "passed"},
                    {"test_case_id": "tc-002", "status": "failed"}
                ]
            }
        )
        assert response.status_code == 200
        
    def test_abort_test_run(self, client, auth_headers):
        """POST /api/v1/test-runs/{id}/abort stops execution"""
        response = client.post(
            "/api/v1/test-runs/run-001/abort",
            headers=auth_headers
        )
        assert response.status_code == 200
        
    def test_rerun_failed_tests(self, client, auth_headers):
        """POST /api/v1/test-runs/{id}/rerun-failed retries"""
        response = client.post(
            "/api/v1/test-runs/run-001/rerun-failed",
            headers=auth_headers
        )
        assert response.status_code == 201
        
    def test_generate_run_report(self, client, auth_headers):
        """GET /api/v1/test-runs/{id}/report generates HTML"""
        response = client.get(
            "/api/v1/test-runs/run-001/report",
            headers=auth_headers
        )
        assert response.status_code == 200
```

### 2.5 Additional API Categories (18 tests)

| Category | Tests | Examples |
|----------|-------|----------|
| **Defects** | 4 | Create/Update/List/Link to TC |
| **Automation** | 4 | Create/Run/Schedule/Monitor execution |
| **Integrations** | 3 | Jira sync, API test webhook, N8N trigger |
| **Reporting** | 4 | Dashboard metrics, trend charts, export |
| **Notifications** | 3 | Email sent, in-app alert, webhook delivery |

---

## Part 3: UI/E2E Test Scenarios (20 tests)

### 3.1 Critical User Workflows (5 tests)

```python
# e2e/critical-flows.spec.ts

test.describe('Critical User Workflows', () => {
  
  test('Complete Login → Create Project → Add Test Case → Execute Flow', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'admin@example.com');
    await page.fill('[data-testid="password"]', 'admin123');
    await page.click('[data-testid="submit"]');
    await page.waitForURL('/dashboard');
    
    // 2. Create project
    await page.click('[data-testid="create-project"]');
    await page.fill('[data-testid="project-name"]', 'E2E Test Project');
    await page.fill('[data-testid="project-key"]', 'ETP');
    await page.click('[data-testid="save-project"]');
    
    // 3. Add test case
    await page.click('[data-testid="add-test-case"]');
    await page.fill('[data-testid="tc-title"]', 'Login Test');
    await page.fill('[data-testid="tc-step-1"]', 'Open login page');
    await page.click('[data-testid="save-tc"]');
    
    // 4. Execute
    await page.click('[data-testid="run-tests"]');
    await page.waitForSelector('[data-testid="run-complete"]');
    
    // Verify
    const status = await page.textContent('[data-testid="run-status"]');
    expect(status).toContain('Passed');
  });
  
  test('Create Defect → Assign → Update Status → Close', async ({ page }) => {
    // Create defect flow
    await login(page);
    await page.click('[data-testid="defects"]');
    await page.click('[data-testid="new-defect"]');
    await page.fill('[data-testid="defect-title"]', 'Login button unresponsive');
    await page.selectOption('[data-testid="severity"]', 'high');
    await page.click('[data-testid="save-defect"]');
    
    // Assign
    await page.click('[data-testid="assign"]');
    await page.click('[data-testid="assignee-option"]');
    
    // Update status
    await page.selectOption('[data-testid="status"]', 'in_progress');
    await page.click('[data-testid="save"]');
    
    // Verify
    const status = await page.textContent('[data-testid="defect-status"]');
    expect(status).toBe('In Progress');
  });
  
  test('Create Test Plan → Add Test Cases → Schedule Run', async ({ page }) => {
    // Full test planning workflow
  });
  
  test('Generate Report → Share with Team', async ({ page }) => {
    // Reporting workflow
  });
  
  test('Configure Automation → Schedule Execution', async ({ page }) => {
    // Automation setup workflow
  });
});
```

### 3.2 Feature-Specific Workflows (10 tests)

| Workflow | Tests |
|----------|-------|
| **Test Management** | Create/Edit/Delete/Bulk operations |
| **Test Execution** | Start run, submit results, abort |
| **Defect Management** | Create/Link/Update status/Close |
| **Reporting** | Dashboard, charts, export |
| **Automation** | Record script, create schedule, monitor |

### 3.3 Cross-Browser & Platform (5 tests)

```python
# e2e/cross-browser.spec.ts

// Run on: Chrome, Firefox, WebKit, Mobile Chrome
test('Core flow works on all browsers', async ({ page, browserName }) => {
  console.log(`Testing on ${browserName}`);
  
  // Login and verify UI renders correctly
  await page.goto('/login');
  expect(await page.isVisible('[data-testid="login-form"]')).toBeTruthy();
  
  // Responsive layout check
  if (browserName === 'chromium' || browserName === 'firefox') {
    await page.setViewportSize({ width: 1920, height: 1080 });
  } else {
    await page.setViewportSize({ width: 375, height: 667 });
  }
  
  // Complete login
  await login(page);
  expect(await page.isVisible('[data-testid="dashboard"]')).toBeTruthy();
});
```

---

## Part 4: Integration Test Patterns (10+ tests)

### 4.1 Database Integrity Tests

```python
# tests/integration/test_db_integrity.py

class TestDatabaseIntegrity:
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_project_cascade_delete(self, db_session):
        """Verify cascade delete removes all related data"""
        # Create project with test cases and runs
        project = create_test_project(db_session)
        test_cases = [create_test_case(db_session, project.id) for _ in range(3)]
        runs = [create_test_run(db_session, project.id, [tc.id for tc in test_cases])]
        
        # Delete project
        db_session.delete(project)
        db_session.commit()
        
        # Verify cascade
        assert db_session.query(TestCase).filter_by(project_id=project.id).count() == 0
        assert db_session.query(TestRun).filter_by(project_id=project.id).count() == 0
        
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_foreign_key_constraint_enforcement(self, db_session):
        """Verify FK constraints prevent orphaned records"""
        with pytest.raises(IntegrityError):
            # Attempt to create test case with non-existent project
            tc = TestCase(project_id="invalid-project", title="Test")
            db_session.add(tc)
            db_session.commit()
            
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_unique_constraint_enforcement(self, db_session):
        """Verify unique constraints prevent duplicates"""
        project1 = create_test_project(db_session, key="PRJ")
        
        with pytest.raises(IntegrityError):
            # Duplicate key should fail
            project2 = TestProject(name="Project 2", key="PRJ", tenant_id=project1.tenant_id)
            db_session.add(project2)
            db_session.commit()
            
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_rls_policy_enforcement(self, db_session):
        """Verify Row-Level Security prevents cross-tenant access"""
        tenant1 = create_tenant(db_session)
        tenant2 = create_tenant(db_session)
        
        proj1 = create_test_project(db_session, tenant_id=tenant1.id)
        
        # Query as tenant2 (simulated via context)
        with set_tenant_context(tenant2.id):
            result = db_session.query(TestProject).filter_by(id=proj1.id).first()
            assert result is None  # Should be blocked by RLS
```

### 4.2 Async Operation Tests

```python
# tests/integration/test_async_operations.py

class TestAsyncOperations:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_test_run_execution_lifecycle(self, db_session, async_client):
        """Verify async test execution from start to completion"""
        # 1. Create and start run
        response = await async_client.post("/api/v1/test-runs", json={
            "project_id": "proj-001",
            "test_case_ids": ["tc-001", "tc-002"]
        })
        run_id = response.json()["id"]
        
        # 2. Poll for completion (with timeout)
        max_wait = 60
        start = time.time()
        while time.time() - start < max_wait:
            response = await async_client.get(f"/api/v1/test-runs/{run_id}")
            if response.json()["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(2)
        
        # 3. Verify results persisted
        final = response.json()
        assert final["status"] in ["completed", "failed"]
        assert len(final["results"]) == 2
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_background_job_completion(self, redis_client, db_session):
        """Verify async background job runs to completion"""
        # Trigger async job
        job_id = trigger_bulk_export_job(["tc-001", "tc-002", "tc-003"])
        
        # Poll Redis for completion
        max_attempts = 30
        for attempt in range(max_attempts):
            status = redis_client.get(f"job:{job_id}:status")
            if status == b"completed":
                break
            await asyncio.sleep(1)
        
        # Verify result
        result_data = redis_client.get(f"job:{job_id}:result")
        assert result_data is not None
```

### 4.3 Cross-Service Integration Tests

```python
# tests/integration/test_cross_service.py

class TestCrossServiceIntegration:
    @pytest.mark.integration
    def test_auth_to_project_flow(self, client, db_ready):
        """Verify auth → project creation → test case → execution chain"""
        # 1. Auth
        auth_resp = client.post("/api/v1/auth/login", json={
            "email": "admin@example.com",
            "password": "admin123"
        })
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create project (requires auth)
        proj_resp = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"name": "Cross-Service Test", "key": "CST"}
        )
        project_id = proj_resp.json()["id"]
        assert proj_resp.status_code == 201
        
        # 3. Add test case (requires project)
        tc_resp = client.post(
            "/api/v1/test-cases",
            headers=headers,
            json={
                "project_id": project_id,
                "title": "Cross-service TC",
                "steps": [{"order": 1, "action": "Test", "expected": "Pass"}]
            }
        )
        tc_id = tc_resp.json()["id"]
        assert tc_resp.status_code == 201
        
        # 4. Execute (requires test case)
        run_resp = client.post(
            "/api/v1/test-runs",
            headers=headers,
            json={
                "project_id": project_id,
                "test_case_ids": [tc_id]
            }
        )
        assert run_resp.status_code == 201
        
    @pytest.mark.integration
    def test_engine_integration_test_execution(self, client, auth_headers, mocker):
        """Verify backend → engine communication for test execution"""
        # Mock engine response
        mocker.patch(
            "app.domains.engine.client.execute_test",
            return_value={"status": "passed", "duration_ms": 5000}
        )
        
        # Create and execute test
        response = client.post(
            "/api/v1/test-runs",
            headers=auth_headers,
            json={"project_id": "proj-001", "test_case_ids": ["tc-001"]}
        )
        
        assert response.status_code == 201
        # Verify engine was called
        from app.domains.engine.client import execute_test
        execute_test.assert_called()
```

### 4.4 Notification & Event Tests

```python
# tests/integration/test_notifications.py

class TestNotificationIntegration:
    @pytest.mark.integration
    def test_defect_creation_triggers_notification(self, client, auth_headers, mocker, db_session):
        """Verify defect creation sends email notification"""
        # Mock email service
        mock_email = mocker.patch("app.domains.notifications.email.send_email")
        
        # Create defect
        response = client.post(
            "/api/v1/defects",
            headers=auth_headers,
            json={
                "project_id": "proj-001",
                "title": "Critical bug",
                "severity": "critical"
            }
        )
        
        assert response.status_code == 201
        
        # Verify email sent
        mock_email.assert_called_once()
        call_args = mock_email.call_args
        assert "bug" in call_args[1]["subject"].lower()
        
    @pytest.mark.integration
    def test_test_run_completion_notification(self, client, auth_headers, mocker, db_session):
        """Verify run completion sends webhook & email"""
        mock_webhook = mocker.patch("app.domains.webhooks.trigger")
        mock_email = mocker.patch("app.domains.notifications.email.send_email")
        
        # Create and complete run
        run_response = client.post(
            "/api/v1/test-runs",
            headers=auth_headers,
            json={"project_id": "proj-001", "test_case_ids": ["tc-001"]}
        )
        run_id = run_response.json()["id"]
        
        # Submit results (simulates completion)
        result_response = client.post(
            f"/api/v1/test-runs/{run_id}/results/bulk",
            headers=auth_headers,
            json={"results": [{"test_case_id": "tc-001", "status": "passed"}]}
        )
        
        # Verify notifications triggered
        mock_webhook.assert_called()
        mock_email.assert_called()
```

---

## Part 5: Test Data Management

### 5.1 Fixtures & Factories

```python
# backend/tests/factories.py

from factory import Factory, Sequence, SubFactory
from factory.sqlalchemy import SQLAlchemyModelFactory
from app.infra.models import (
    User, Organization, Team, TestProject, TestCase, 
    TestRun, TestResult, Defect
)

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        
    id = Sequence(lambda n: f"user-{n}")
    email = Sequence(lambda n: f"user{n}@test.com")
    full_name = Sequence(lambda n: f"Test User {n}")
    password_hash = "hashed_password"
    is_active = True
    tenant_id = SubFactory("tests.factories.TenantFactory")

class TenantFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Organization
        
    id = Sequence(lambda n: f"tenant-{n}")
    name = Sequence(lambda n: f"Test Org {n}")
    owner_id = SubFactory(UserFactory)

class TeamFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Team
        
    id = Sequence(lambda n: f"team-{n}")
    name = Sequence(lambda n: f"Test Team {n}")
    tenant_id = SubFactory(TenantFactory)

class ProjectFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TestProject
        
    id = Sequence(lambda n: f"proj-{n}")
    name = Sequence(lambda n: f"Test Project {n}")
    key = Sequence(lambda n: f"TST{n}")
    tenant_id = SubFactory(TenantFactory)
    owner_id = SubFactory(UserFactory)

class TestCaseFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TestCase
        
    id = Sequence(lambda n: f"tc-{n}")
    project_id = SubFactory(ProjectFactory)
    title = Sequence(lambda n: f"Test Case {n}")
    priority = "medium"
    status = "active"

class TestRunFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TestRun
        
    id = Sequence(lambda n: f"run-{n}")
    project_id = SubFactory(ProjectFactory)
    status = "pending"
    created_by = SubFactory(UserFactory)

class DefectFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Defect
        
    id = Sequence(lambda n: f"def-{n}")
    project_id = SubFactory(ProjectFactory)
    title = Sequence(lambda n: f"Defect {n}")
    severity = "medium"
    status = "open"
```

### 5.2 Test Data Seed Script

```bash
# backend/tests/seeds.sh
#!/bin/bash

# Create test tenants
psql -U postgres -d neurex -c "
INSERT INTO organizations (id, name, owner_id) VALUES 
  ('tenant-1', 'Test Org 1', 'user-admin'),
  ('tenant-2', 'Test Org 2', 'user-op');
"

# Create test users
psql -U postgres -d neurex -c "
INSERT INTO users (id, email, full_name, tenant_id, password_hash) VALUES
  ('user-admin', 'admin@example.com', 'Admin User', 'tenant-1', '$2a$...'),
  ('user-op', 'operator@test.com', 'Operator', 'tenant-1', '$2a$...'),
  ('user-viewer', 'viewer@test.com', 'Viewer', 'tenant-1', '$2a$...');
"

# Create test projects (100 projects for load testing)
for i in {1..100}; do
  psql -U postgres -d neurex -c "
  INSERT INTO test_projects (id, name, key, tenant_id, owner_id) VALUES
    ('proj-$i', 'Project $i', 'PRJ$i', 'tenant-1', 'user-admin');
  "
done

# Create test cases (1000 for pagination testing)
for i in {1..1000}; do
  proj_id="proj-$((i % 100 + 1))"
  psql -U postgres -d neurex -c "
  INSERT INTO test_cases (id, project_id, title, priority, status) VALUES
    ('tc-$i', '$proj_id', 'Test Case $i', 'medium', 'active');
  "
done

echo "Test data seed completed"
```

### 5.3 Data Cleanup & Isolation

```python
# backend/tests/conftest.py — additions

@pytest.fixture(scope="function")
def db_transaction_rollback(db_session):
    """Wrap test in DB transaction that rolls back after test."""
    # Begin nested transaction
    savepoint = db_session.begin_nested()
    yield db_session
    # Rollback to savepoint
    savepoint.rollback()

@pytest.fixture(autouse=True)
def cleanup_test_data(db_session):
    """Auto-cleanup test-created data after each test."""
    yield
    # Clear test-specific tables
    db_session.query(TestRun).filter(TestRun.id.like("test-%")).delete()
    db_session.query(TestCase).filter(TestCase.id.like("test-%")).delete()
    db_session.query(TestProject).filter(TestProject.id.like("test-%")).delete()
    db_session.commit()
```

---

## Part 6: Execution & Reporting

### 6.1 Regression Test Runbook

```bash
# Makefile targets

## Daily Regression Suite (45 minutes)
make test-regression:
	@echo "▶ Running regression suite (180+ tests)..."
	cd backend && $(PYTHON) -m pytest \
		--cov=app \
		--cov-report=html:../reports/coverage \
		-n 4 \
		-m "not slow and not ai" \
		--junit-xml=../reports/junit.xml \
		-v
	@echo "✓ Regression suite complete"

## Targeted Test Runs
make test-unit:         # Unit tests only (100+, ~5min)
make test-integration:  # Integration tests (~15min)
make test-api:          # API tests (~10min)
make test-security:     # Security tests (~5min)
make test-smoke:        # Smoke tests (~2min)

## Parallel Execution (4 workers)
pytest -n 4 --dist loadscope

## With Coverage Report
pytest --cov=app --cov-report=html --cov-report=term-missing

## With Fail-Fast (stop on first failure)
pytest -x

## Specific Test Category
pytest -m integration
pytest -m regression
pytest -m security
```

### 6.2 CI/CD Integration

```yaml
# .github/workflows/regression.yml

name: Regression Suite

on:
  schedule:
    - cron: '0 8 * * *'  # Daily 8 AM
  workflow_dispatch:

jobs:
  regression:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          
      - name: Start services
        run: docker-compose up -d postgres redis
        
      - name: Run migrations
        run: cd backend && alembic upgrade head
        
      - name: Run regression tests
        run: |
          cd backend
          pytest \
            --cov=app \
            --cov-report=xml \
            --junit-xml=junit.xml \
            -n 4 \
            -m "not slow and not ai" \
            tests/
            
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          
      - name: Upload test results
        if: always()
        uses: EnricoMi/publish-unit-test-result-action@v2
        with:
          files: backend/junit.xml
          
      - name: Slack notification
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Regression suite failed - check logs"
            }
```

### 6.3 Test Report Generation

```python
# backend/tests/report_generator.py

class RegressionReport:
    def __init__(self, junit_xml_path):
        self.results = self._parse_junit(junit_xml_path)
        
    def generate_html_report(self, output_path):
        """Generate HTML report with charts & metrics"""
        html = f"""
        <html>
        <head>
            <title>Regression Test Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>Regression Test Results</h1>
            <h2>Summary</h2>
            <p>Total: {self.total_tests}</p>
            <p>Passed: {self.passed_tests} ({self.pass_rate}%)</p>
            <p>Failed: {self.failed_tests}</p>
            <p>Skipped: {self.skipped_tests}</p>
            <p>Duration: {self.total_duration}s</p>
            
            <h2>Trend Chart</h2>
            <canvas id="trendChart"></canvas>
            
            <h2>Category Breakdown</h2>
            <table>
                <tr><th>Category</th><th>Tests</th><th>Passed</th><th>Failed</th></tr>
                {self._render_category_rows()}
            </table>
            
            <h2>Failed Tests</h2>
            {self._render_failed_tests()}
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html)
```

---

## Part 7: Implementation Timeline (2 weeks, 4 engineers)

| Week | Sprint | Focus | Tests Added | Lead |
|------|--------|-------|-------------|------|
| 1 | Days 1-3 | Unit test collection | 100+ | Engineer A |
| 1 | Days 4-5 | API integration tests | 50+ | Engineer B |
| 2 | Days 6-7 | UI/E2E scenarios | 20 | Engineer C |
| 2 | Days 8-10 | Integration patterns | 10+ | Engineer D |

### Milestones
- **Day 3:** 100 unit tests green
- **Day 5:** 150 tests (100 unit + 50 API)
- **Day 7:** 170 tests (+ 20 E2E)
- **Day 10:** 180+ full regression suite
- **Day 14:** CI/CD integration complete, daily runs stable

---

## Success Criteria

1. **Coverage:** 70%+ code coverage minimum
2. **Execution Time:** Daily regression < 45 minutes on 4 workers
3. **Pass Rate:** 100% green (no flaky tests)
4. **Maintainability:** <10% test code maintenance per sprint
5. **Documentation:** Every test has purpose comment and traceability ID
6. **Isolation:** No test depends on another test's output
7. **Clarity:** Test names clearly describe scenario and expected outcome

---

## Appendix: Test Template

```python
# backend/tests/integration/test_example.py

import pytest
from fastapi.testclient import TestClient

class TestExampleDomain:
    """Example domain integration tests.
    
    These tests verify the complete workflow from API endpoint through
    service layer to database, ensuring data integrity and business logic.
    """
    
    @pytest.mark.integration
    @pytest.mark.P1
    def test_create_and_retrieve_entity(self, client: TestClient, auth_headers: dict, db_session):
        """Test: Create entity via API → Verify stored in DB → Retrieve via API
        
        Traceability: REQ-DOMAIN-001, TC-DOMAIN-001
        Expected: Entity stored with correct values
        """
        # Arrange
        payload = {
            "name": "Test Entity",
            "status": "active"
        }
        
        # Act
        response = client.post(
            "/api/v1/entities",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        entity_id = response.json()["id"]
        
        # Verify in database
        entity = db_session.query(Entity).filter_by(id=entity_id).first()
        assert entity is not None
        assert entity.name == "Test Entity"
        
        # Verify via API retrieve
        get_response = client.get(
            f"/api/v1/entities/{entity_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Test Entity"
```

---

## Related Documents

- [Test Infrastructure](test_infrastructure.md) — Current test setup
- [CI/CD Pipeline](ci-cd.md) — GitHub Actions integration
- [CLAUDE.md](CLAUDE.md) — Project conventions & test guidelines

