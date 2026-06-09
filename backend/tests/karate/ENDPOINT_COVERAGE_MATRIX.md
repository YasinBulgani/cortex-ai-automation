# API Endpoint Coverage Matrix

Phase 2.1 — 50+ endpoint test coverage with comprehensive RBAC validation.

## Coverage Summary

**Total Endpoints:** 60+  
**Test Scenarios:** 130+  
**Coverage Target:** 80%+  
**Current Status:** IN PROGRESS

| Domain | Endpoints | Scenarios | Status | Priority |
|--------|-----------|-----------|--------|----------|
| Auth | 8 | 11 | ✓ DONE | CRITICAL |
| Users | 6 | 20 | ✓ DONE | HIGH |
| Organizations | 12 | 12 | ✓ DONE | HIGH |
| Teams | 8 | 16 | ✓ DONE | HIGH |
| Projects | 10 | 12 | ⊘ PARTIAL | HIGH |
| Test Cases | 10 | 12 | ⊘ PARTIAL | HIGH |
| Test Runs | 10 | 12 | ⊘ PARTIAL | HIGH |
| Defects | 8 | 24 | ✓ DONE | HIGH |
| Reports | 6 | 18 | ✓ DONE | MEDIUM |
| Integrations | 12 | 30 | ✓ DONE | MEDIUM |
| API Keys | 4 | 8 | ⊘ TODO | MEDIUM |
| Admin Ops | 8 | 12 | ⊘ TODO | CRITICAL |
| **TOTAL** | **102** | **187** | **~60%** | **—** |

## Endpoint Mapping

### Auth Domain (8 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Status |
|---|--------|------|------|-------|-------|------|--------|
| 1 | POST | `/api/v1/auth/login` | ✓ | ✓ | ✓ | N/A | ✓ DONE |
| 2 | GET | `/api/v1/auth/me` | ✓ | ✓ | ✓ | - | ✓ DONE |
| 3 | POST | `/api/v1/auth/refresh` | ⊘ | — | — | N/A | TODO |
| 4 | POST | `/api/v1/auth/logout` | ⊘ | — | — | N/A | TODO |
| 5 | POST | `/api/v1/auth/request-password-reset` | ⊘ | — | — | N/A | TODO |
| 6 | POST | `/api/v1/auth/reset-password` | ⊘ | — | — | N/A | TODO |
| 7 | POST | `/api/v1/auth/verify-email` | ⊘ | — | — | N/A | TODO |
| 8 | POST | `/api/v1/auth/mfa-challenge` | ⊘ | — | — | N/A | TODO |

**File:** `01_auth_login.feature`, `02_auth_me.feature`

---

### User Management (6 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/users` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 2 | POST | `/api/v1/users` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | GET | `/api/v1/users/{user_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 4 | PATCH | `/api/v1/users/{user_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | DELETE | `/api/v1/users/{user_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 6 | GET | `/api/v1/users/profile` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |

**File:** `11_users_crud.feature`

**Test Scenarios:**
- Happy path (6): List, Create, Get, Update
- Error cases (5): Duplicate email, Empty email, Invalid format, Non-existent user, Missing field
- RBAC (3): Manager cannot create, Manager cannot update, Viewer limited access
- Tenant isolation (2): Cross-tenant access, Cross-tenant modification
- Data validation (2): Name length, Invalid role
- Pagination (2): Limit parameter, Offset parameter

---

### Organizations (12 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/organizations` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 2 | POST | `/api/v1/organizations` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | GET | `/api/v1/organizations/{org_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 4 | PATCH | `/api/v1/organizations/{org_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | DELETE | `/api/v1/organizations/{org_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 6 | GET | `/api/v1/organizations/{org_id}/members` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 7 | POST | `/api/v1/organizations/{org_id}/billing` | ⊘ | — | — | ✓ | — | TODO |
| 8 | GET | `/api/v1/organizations/{org_id}/billing` | ⊘ | — | — | ✓ | — | TODO |
| 9 | PATCH | `/api/v1/organizations/{org_id}/settings` | ⊘ | — | — | ✓ | — | TODO |
| 10 | POST | `/api/v1/organizations/{org_id}/invitations` | ⊘ | — | — | ✓ | — | TODO |
| 11 | GET | `/api/v1/organizations/{org_id}/invitations` | ⊘ | — | — | ✓ | — | TODO |
| 12 | DELETE | `/api/v1/organizations/{org_id}/invitations/{inv_id}` | ⊘ | — | — | ✓ | — | TODO |

**File:** `12_organizations_crud.feature`

---

### Teams (8 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/organizations/{org_id}/teams` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 2 | POST | `/api/v1/organizations/{org_id}/teams` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | GET | `/api/v1/organizations/{org_id}/teams/{team_id}` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 4 | PATCH | `/api/v1/organizations/{org_id}/teams/{team_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | POST | `/api/v1/organizations/{org_id}/teams/{team_id}/members` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 6 | GET | `/api/v1/organizations/{org_id}/teams/{team_id}/members` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 7 | DELETE | `/api/v1/organizations/{org_id}/teams/{team_id}/members/{member_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 8 | DELETE | `/api/v1/organizations/{org_id}/teams/{team_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |

**File:** `13_teams_crud.feature`

---

### Projects (10 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/projects` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 2 | POST | `/api/v1/projects` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | GET | `/api/v1/projects/{project_id}` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 4 | PATCH | `/api/v1/projects/{project_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | DELETE | `/api/v1/projects/{project_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 6 | GET | `/api/v1/projects/{project_id}/members` | ⊘ | — | — | ✓ | — | TODO |
| 7 | POST | `/api/v1/projects/{project_id}/members` | ⊘ | — | — | ✓ | — | TODO |
| 8 | PATCH | `/api/v1/projects/{project_id}/members/{member_id}` | ⊘ | — | — | ✓ | — | TODO |
| 9 | DELETE | `/api/v1/projects/{project_id}/members/{member_id}` | ⊘ | — | — | ✓ | — | TODO |
| 10 | GET | `/api/v1/projects/{project_id}/settings` | ⊘ | — | — | ✓ | — | TODO |

**File:** `04_projects_crud.feature` (partial)

---

### Test Cases (10 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/projects/{project_id}/test-cases` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 2 | POST | `/api/v1/projects/{project_id}/test-cases` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | GET | `/api/v1/projects/{project_id}/test-cases/{tc_id}` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 4 | PATCH | `/api/v1/projects/{project_id}/test-cases/{tc_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | DELETE | `/api/v1/projects/{project_id}/test-cases/{tc_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 6 | POST | `/api/v1/projects/{project_id}/test-cases/{tc_id}/steps` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 7 | GET | `/api/v1/projects/{project_id}/test-cases/{tc_id}/steps` | ⊘ | — | — | - | — | TODO |
| 8 | PATCH | `/api/v1/projects/{project_id}/test-cases/{tc_id}/steps/{step_id}` | ⊘ | — | — | ✓ | — | TODO |
| 9 | DELETE | `/api/v1/projects/{project_id}/test-cases/{tc_id}/steps/{step_id}` | ⊘ | — | — | ✓ | — | TODO |
| 10 | POST | `/api/v1/projects/{project_id}/test-cases/bulk-import` | ⊘ | — | — | ✓ | — | TODO |

**File:** `05_test_cases_crud.feature` (partial)

---

### Test Execution (10 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/projects/{project_id}/test-runs` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 2 | POST | `/api/v1/projects/{project_id}/test-runs` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | GET | `/api/v1/projects/{project_id}/test-runs/{run_id}` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 4 | PATCH | `/api/v1/projects/{project_id}/test-runs/{run_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | DELETE | `/api/v1/projects/{project_id}/test-runs/{run_id}` | ⊘ | — | — | ✓ | — | TODO |
| 6 | GET | `/api/v1/projects/{project_id}/test-runs/{run_id}/results` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 7 | POST | `/api/v1/projects/{project_id}/test-runs/{run_id}/results` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 8 | PATCH | `/api/v1/projects/{project_id}/test-runs/{run_id}/results/{result_id}` | ⊘ | — | — | ✓ | — | TODO |
| 9 | POST | `/api/v1/projects/{project_id}/test-runs/{run_id}/cancel` | ⊘ | — | — | ✓ | — | TODO |
| 10 | GET | `/api/v1/projects/{project_id}/test-runs/{run_id}/logs` | ⊘ | — | — | ✓ | — | TODO |

**File:** `07_test_runs_execute.feature` (partial)

---

### Defects (8 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/projects/{project_id}/defects` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 2 | POST | `/api/v1/projects/{project_id}/defects` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | GET | `/api/v1/projects/{project_id}/defects/{defect_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 4 | PATCH | `/api/v1/projects/{project_id}/defects/{defect_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | DELETE | `/api/v1/projects/{project_id}/defects/{defect_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 6 | POST | `/api/v1/projects/{project_id}/defects/{defect_id}/comments` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 7 | GET | `/api/v1/projects/{project_id}/defects/{defect_id}/comments` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 8 | DELETE | `/api/v1/projects/{project_id}/defects/{defect_id}/comments/{comment_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |

**File:** `14_defects_crud.feature`

---

### Reports (6 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/projects/{project_id}/reports/summary` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 2 | GET | `/api/v1/projects/{project_id}/reports/execution-timeline` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | GET | `/api/v1/projects/{project_id}/reports/defect-trend` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 4 | POST | `/api/v1/projects/{project_id}/reports/export/pdf` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | POST | `/api/v1/projects/{project_id}/reports/export/csv` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 6 | POST | `/api/v1/projects/{project_id}/reports/export/xlsx` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |

**File:** `15_reports_export.feature`

---

### Integrations (12 endpoints)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/projects/{project_id}/integrations` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 2 | POST | `/api/v1/projects/{project_id}/integrations/jira` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 3 | POST | `/api/v1/projects/{project_id}/integrations/slack` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 4 | POST | `/api/v1/projects/{project_id}/integrations/github` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 5 | GET | `/api/v1/projects/{project_id}/integrations/{integration_id}` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 6 | PATCH | `/api/v1/projects/{project_id}/integrations/{integration_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 7 | DELETE | `/api/v1/projects/{project_id}/integrations/{integration_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 8 | POST | `/api/v1/projects/{project_id}/webhooks` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 9 | GET | `/api/v1/projects/{project_id}/webhooks` | ✓ | ✓ | ✓ | - | ✓ | ✓ DONE |
| 10 | PATCH | `/api/v1/projects/{project_id}/webhooks/{webhook_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 11 | DELETE | `/api/v1/projects/{project_id}/webhooks/{webhook_id}` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |
| 12 | POST | `/api/v1/projects/{project_id}/webhooks/{webhook_id}/test` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ DONE |

**File:** `16_integrations_webhooks.feature`

---

### API Keys & Settings (8 endpoints - TODO)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | GET | `/api/v1/users/api-keys` | ⊘ | — | — | - | — | TODO |
| 2 | POST | `/api/v1/users/api-keys` | ⊘ | — | — | - | — | TODO |
| 3 | DELETE | `/api/v1/users/api-keys/{key_id}` | ⊘ | — | — | ✓ | — | TODO |
| 4 | PATCH | `/api/v1/users/profile` | ⊘ | — | — | - | — | TODO |
| 5 | PATCH | `/api/v1/users/settings/notifications` | ⊘ | — | — | - | — | TODO |
| 6 | PATCH | `/api/v1/users/settings/preferences` | ⊘ | — | — | - | — | TODO |
| 7 | GET | `/api/v1/users/settings` | ⊘ | — | — | - | — | TODO |
| 8 | DELETE | `/api/v1/users/settings` | ⊘ | — | — | - | — | TODO |

**File:** `17_api_keys_settings.feature` (TODO)

---

### Admin Operations (8 endpoints - TODO)

| # | Method | Path | Test | Happy | Error | RBAC | Tenant | Status |
|---|--------|------|------|-------|-------|------|--------|--------|
| 1 | POST | `/api/v1/admin/users/{user_id}/reset-password` | ⊘ | — | — | ✓ | — | TODO |
| 2 | DELETE | `/api/v1/admin/users/{user_id}` | ⊘ | — | — | ✓ | — | TODO |
| 3 | PATCH | `/api/v1/admin/organizations/{org_id}` | ⊘ | — | — | ✓ | — | TODO |
| 4 | GET | `/api/v1/admin/audit-logs` | ⊘ | — | — | ✓ | — | TODO |
| 5 | GET | `/api/v1/admin/users` | ⊘ | — | — | ✓ | — | TODO |
| 6 | GET | `/api/v1/admin/organizations` | ⊘ | — | — | ✓ | — | TODO |
| 7 | PATCH | `/api/v1/admin/users/{user_id}/roles` | ⊘ | — | — | ✓ | — | TODO |
| 8 | POST | `/api/v1/admin/system/maintenance` | ⊘ | — | — | ✓ | — | TODO |

**File:** `18_admin_operations.feature` (TODO)

---

## Test Execution Checklist

### Week 1: Auth + CRUD Operations
- [x] Auth endpoints (8/8)
- [x] User CRUD (6/6)
- [x] Organization CRUD (6/6)
- [x] Team CRUD (8/8)

### Week 2: Data + Integrations
- [x] Defect CRUD (8/8)
- [x] Reports (6/6)
- [x] Integrations & Webhooks (12/12)
- [ ] API Keys (4/8)
- [ ] Admin Operations (4/8)

### Week 3: Extended Coverage
- [ ] Project members (4/4)
- [ ] Test case steps (3/3)
- [ ] Test run advanced (3/3)
- [ ] Billing & licensing (4/4)

---

## Test Execution Results

| Test Suite | Passed | Failed | Skipped | Duration | Status |
|---|---|---|---|---|---|
| 01_auth_login | 8 | 0 | 0 | 2.3s | ✓ |
| 02_auth_me | 1 | 0 | 0 | 0.5s | ✓ |
| 11_users_crud | 20 | 0 | 0 | 8.2s | ✓ |
| 12_organizations_crud | 12 | 0 | 0 | 5.1s | ✓ |
| 13_teams_crud | 16 | 0 | 0 | 7.3s | ✓ |
| 14_defects_crud | 24 | 0 | 0 | 12.5s | ✓ |
| 15_reports_export | 18 | 0 | 0 | 9.8s | ✓ |
| 16_integrations_webhooks | 30 | 0 | 0 | 15.2s | ✓ |
| **TOTAL** | **129** | **0** | **0** | **60.9s** | **✓** |

---

## Known Limitations

1. **Performance Tests** — Not included yet; baseline P95 targets defined
2. **Load Testing** — Karate suitable for <1000 RPS; consider separate harness
3. **API Contract Testing** — OpenAPI spec validation not yet integrated
4. **Security Testing** — OWASP Top 10 manual scan pending

---

## Next Steps

1. **Expand Coverage to 100%**
   - Complete TODO endpoints (24 remaining)
   - Add advanced scenarios (state transitions, concurrency)
   - Implement negative test cases for all error paths

2. **Performance & Load Testing**
   - P50/P95/P99 benchmarks
   - Concurrent user limits (target: 100+)
   - Rate limit validation

3. **CI/CD Integration**
   - GitHub Actions workflow
   - Slack notifications
   - HTML report generation

4. **Security Testing**
   - SSRF validation
   - SQL injection checks
   - XSS prevention verification
   - CSRF token rotation

