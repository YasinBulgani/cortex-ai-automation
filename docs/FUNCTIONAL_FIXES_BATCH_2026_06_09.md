# Functional Fixes Batch: 6 Critical Bugs — 2026-06-09

**Status:** Implementation ready | **Tests:** TBD | **Severity:** FUNC-HIGH, SEC-HIGH

---

## Overview

This batch addresses 6 functional gaps identified in the competitive audit and architecture panel review:

| Bug ID | Category | Description | Impact | Status |
|--------|----------|-------------|--------|--------|
| **FUNC-HIGH-1** | Workflows | Review workflow state machine incomplete | Test QA blocked | ✅ Ready |
| **FUNC-HIGH-2** | RBAC | Defect retest lifecycle lacks RBAC guards | Security gap | ✅ Ready |
| **FUNC-HIGH-3** | Telemetry | Products telemetry all demo data | Data integrity | ✅ Ready |
| **FUNC-HIGH-4** | Security | API key rotation lifecycle missing | Credential hygiene | ✅ Ready |
| **SEC-HIGH-1** | Permissions | Admin wildcard permission unchecked | Privilege escalation risk | ✅ Ready |
| **SEC-HIGH-3** | Secrets | Gateway internal key no rotation mechanism | Long-lived secrets | ✅ Ready |

---

## Fix #1: Review Workflow State Machine

**File:** `/backend/app/domains/test_management/review_workflow.py`

### Problem
Test cases lack proper review workflow. Current migration adds columns but no state machine.

### Solution
Enum-based state machine with validated transitions:

```
    none
    ├─→ pending_review
    │   ├─→ approved ──→ none (reset)
    │   ├─→ rejected ──→ pending_review (re-review)
    │   └─→ none (cancel)
    ├─→ approved ──→ pending_review (request re-review)
    └─→ rejected ──→ none (dismiss)
```

### Key Classes
- `ReviewStatus` — Enum (none, pending_review, approved, rejected)
- `ReviewTransition` — Validates state machine
- `get_review_action()` — Determines action label for logging

### Integration Points
1. **Model update** — Test management case model
2. **Router endpoints** — POST/PATCH case review
3. **Permission check** — Reviewer role validation

### Tests
```python
def test_review_workflow_transitions():
    assert ReviewTransition.can_transition("none", "pending_review") == True
    assert ReviewTransition.can_transition("pending_review", "approved") == True
    assert ReviewTransition.can_transition("approved", "rejected") == False
```

---

## Fix #2: Defect Retest RBAC

**File:** `/backend/app/domains/test_management/defect_retest_rbac.py`

### Problem
Defect retest lifecycle (open → mark ready → execute → verify) lacks role-based guards.

### Solution
Two-part RBAC:

#### Part A: Role Permissions Matrix
```
qa_engineer:      open, write, verify, execute_retest
developer:        retest (mark as ready)
qa_automation:    execute_retest (run automation only)
manager:          read-only
admin:            all
```

#### Part B: Retest Status Transitions
```
not_ready ──→ ready
ready     ──→ in_progress, not_ready
in_progress ──→ passed, blocked, ready
passed    ──→ ready, not_ready
blocked   ──→ ready
```

### Key Classes
- `RetestRBACPolicy` — Role-based permission checks
- `RetestStatusTransitions` — Status state machine

### Integration Points
1. **defects/router.py** — Add `mark_retest()` endpoint with RBAC guard
2. **defects/service.py** — Update lifecycle functions
3. **deps.py** — Reuse `require_permission()`

### New Endpoint
```python
@router.post("/{defect_id}/mark-retest")
def mark_defect_retest(
    defect_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Requires defects.retest permission (Developer role)."""
```

### Tests
```python
def test_defect_retest_rbac():
    assert RetestRBACPolicy.can_mark_retest("developer") == True
    assert RetestRBACPolicy.can_mark_retest("qa_engineer") == False
    assert RetestRBACPolicy.can_execute_retest("qa_automation") == True
```

---

## Fix #3: Products Real Telemetry Pipeline

**File:** `/backend/app/domains/products/telemetry_aggregation.py`

### Problem
Products dashboard shows only demo/simulated data. Competitive audit shows real aggregation required.

### Solution
Real aggregation from test_management and automation domains:

#### Metrics Collected
1. **Test Cases** — total, flaky (flakiness_score > 0.5), coverage %
2. **Executions** — total runs, pass rate, automation runs (last 7 days)
3. **Defects** — open/closed count, resolution rate
4. **Trends** — sparkline data for pass_rate, execution_count, defect_count

#### Data Flow
```
test_management_runs ──┐
test_management_cases─┼→ get_product_stats() → {stats, trends}
automation_suite_runs ┤
defects               └─┘
```

### Key Functions
- `get_product_stats()` — Main aggregation (DB queries)
- `get_sparkline_data()` — Daily trend line (7-day window)

### Integration Points
1. **products/router.py** — Update `GET /products/{id}/telemetry`
2. **products/service.py** — Call real aggregation (flag isDemo=False)
3. **Caching** — Add Redis cache (1h TTL) for performance

### Sample Response
```json
{
  "test_cases": {
    "total": 234,
    "flaky": 12,
    "coverage_pct": 78
  },
  "executions": {
    "total_runs": 1200,
    "pass_rate": 94,
    "automation_runs": 450,
    "period_days": 7
  },
  "defects": {
    "open": 8,
    "closed": 42,
    "resolution_rate": 84
  },
  "isDemo": false,
  "lastUpdated": "2026-06-09T10:00:00Z"
}
```

### Tests
```python
def test_products_real_telemetry(db, seeded_project):
    stats = get_product_stats(db, seeded_project.id)
    assert stats["test_cases"]["total"] > 0
    assert 0 <= stats["executions"]["pass_rate"] <= 100
    assert not stats.get("isDemo", True)  # Must be real
```

---

## Fix #4: API Key Rotation Lifecycle

**Files:**
- `/backend/app/domains/api_keys/__init__.py`
- `/backend/app/domains/api_keys/models.py`
- `/backend/app/domains/api_keys/service.py`
- `/backend/app/domains/api_keys/router.py`

### Problem
No user API key management. Credentials never rotate. No lifecycle tracking.

### Solution
Complete API key management domain:

#### Features
1. **Create** — Generate secure API key (sk_*)
2. **Rotate** — New key, 24h overlap window, old key expires
3. **Revoke** — Immediate deactivation
4. **Audit** — Track creation, rotation, revocation with reasons

#### Model: ApiKey
```python
id, user_id, name, key_hash (never plaintext)
is_active, expires_at, revoked_at, revoked_reason
created_by, rotated_from_id, rotation_reason
last_used_at (audit trail)
```

#### Endpoints
```
POST   /api/v1/api-keys                    Create key
GET    /api/v1/api-keys                    List keys
POST   /api/v1/api-keys/{id}/rotate        Rotate key
DELETE /api/v1/api-keys/{id}               Revoke key
```

#### Key Security Features
- Plaintext key shown only once at creation
- Keys hashed with SHA256 (app/infra/crypto.py)
- Concurrent active keys during 24h rotation window
- Expiry tracking (default 90 days)
- Last-used timestamp for audit

### Integration Points
1. **Database** — New api_keys table (migration)
2. **Router registry** — Add api_keys domain to app/core/router_registry.py
3. **Auth middleware** — Support API key authentication (future)
4. **Cleanup** — Daily cron to delete old revoked keys

### Migration
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES sd_users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoked_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL,
    created_by VARCHAR(255),
    rotated_from_id UUID REFERENCES api_keys(id),
    rotation_reason VARCHAR(255),
    last_used_at TIMESTAMPTZ,
    INDEX(user_id, is_active),
    INDEX(expires_at)
);
```

### Tests
```python
def test_api_key_creation():
    key, plaintext = create_api_key(db, "user123", "my-key")
    assert key.is_active == True
    assert len(plaintext) > 20

def test_api_key_rotation():
    key1, pt1 = create_api_key(db, "user123", "key-v1")
    key2, pt2 = rotate_api_key(db, key1.id, "user123")
    assert verify_api_key(db, pt2, "user123") is not None
    # Old key valid for 24h more
    assert verify_api_key(db, pt1, "user123") is not None
```

---

## Fix #5: Admin Permission Wildcard Control

**File:** `/backend/app/domains/rbac/admin_permission_control.py`

### Problem
`admin.*` wildcard permission used without validation. Risk of permission bypass or escalation.

### Solution
Permission validation and filtering:

#### Validation Rules
```
Valid formats:
  - 'domain.action'      (e.g. 'defects.write')
  - 'admin.*'            (wildcard — always valid)
  - 'admin.specific'     (e.g. 'admin.manage_roles') — must be whitelisted

Invalid:
  - 'admin.*.write'      (nested wildcards)
  - 'admin_anything'     (wrong separator)
  - Unknown actions      (e.g. 'admin.super_bypass')
```

#### Whitelisted Admin Actions
```
admin.read
admin.write
admin.delete
admin.manage_roles
admin.manage_permissions
admin.manage_users
admin.manage_teams
admin.view_audit_logs
admin.configure_system
admin.manage_api_keys
admin.rotate_secrets
```

#### Key Classes
- `AdminPermissionControl` — Validation and filtering
  - `is_valid_admin_action(action)` — Check if admin.* action is whitelisted
  - `validate_permission_string(perm)` — Format validation
  - `filter_admin_permissions(perms)` — Remove invalid ones
  - `can_manage_permission(user_perms, target_perm)` — Permission escalation check

### Integration Points
1. **deps.py** — Add filter in `_user_permissions()` return
2. **auth/router.py** — Validate perms on role assignment
3. **rbac/router.py** — Enforce before granting permissions

### Tests
```python
def test_admin_permission_validation():
    assert AdminPermissionControl.validate_permission_string("admin.*") == True
    assert AdminPermissionControl.validate_permission_string("admin.manage_roles") == True
    assert AdminPermissionControl.validate_permission_string("admin.super_bypass") == False
    
def test_cannot_escalate():
    user_perms = {"admin.manage_permissions"}  # Limited admin
    assert not AdminPermissionControl.can_manage_permission(user_perms, "admin.*")
```

---

## Fix #6: Gateway Internal Key Rotation

**File:** `/backend/app/domains/gateway/key_rotation.py`

### Problem
`GATEWAY_INTERNAL_KEY` is static, long-lived, no rotation mechanism. Single point of failure if compromised.

### Solution
Key rotation manager with versioning:

#### Features
1. **Generate** — Cryptographically secure new keys (gw_*)
2. **Rotate** — New version, keep recent in history
3. **Verify** — Check against current + recent versions (grace period)
4. **Status** — Key age, rotation schedule recommendations

#### Key Rotation Schedule
```
Age ≤ 72 days:   "fresh" — no action
Age 72-90 days:  "aging" — schedule rotation
Age > 90 days:   "overdue" — rotate immediately
```

#### Key Versioning (In-Memory)
```python
_key_history = {
    1: {"key": "gw_...", "created_at": datetime, "key_hash": "sha256(...)"},
    2: {"key": "gw_...", "created_at": datetime, "key_hash": "sha256(...)"},
    # Keep last 5 versions for migration grace period
}
```

#### Key Classes
- `GatewayKeyRotation` — Manages lifecycle
  - `generate_key()` → secure random key
  - `rotate_key(old_key)` → new version, return tuple (key, version)
  - `verify_key(provided_key)` → check current + recent
  - `get_key_status()` → age, rotation schedule
  - `validate_rotation_schedule()` → recommend action

### Integration Points
1. **gateway/init.py** — Call on startup to load current key
2. **AI Gateway** — Verify provided key against current + history
3. **Admin endpoint** — POST /admin/gateway/rotate-key
4. **Cron job** — Check age, alert if overdue

### Deployment
```bash
# Generate new key
python -c "from app.domains.gateway.key_rotation import GatewayKeyRotation; print(GatewayKeyRotation.generate_key())"
# Output: gw_SecureRandomString...

# Set environment
export GATEWAY_INTERNAL_KEY=gw_...

# In app init:
new_key, version = GatewayKeyRotation.rotate_key(os.getenv("GATEWAY_INTERNAL_KEY"))
print(f"Gateway key version {version} deployed")
```

### Tests
```python
def test_gateway_key_rotation():
    key1 = GatewayKeyRotation.generate_key()
    key2, v2 = GatewayKeyRotation.rotate_key(key1)
    
    assert GatewayKeyRotation.verify_key(key2) == True
    assert GatewayKeyRotation.verify_key(key1) == True  # Still valid (grace)
    assert GatewayKeyRotation.get_current_key_version() == 2

def test_gateway_key_expiry():
    status = GatewayKeyRotation.validate_rotation_schedule()
    assert status["status"] in ("fresh", "aging", "overdue")
```

---

## Implementation Roadmap

### Phase 1: Core (Immediate)
- [x] Review workflow state machine
- [x] Defect retest RBAC
- [x] Admin permission control

### Phase 2: Security & Audit (Next Sprint)
- [x] API key rotation lifecycle
- [x] Gateway key rotation
- [x] Products real telemetry

### Phase 3: Integration
- [ ] Database migration for api_keys table
- [ ] Router registry updates
- [ ] Endpoint testing (Unit + Integration)
- [ ] E2E test scenarios

### Phase 4: Deployment
- [ ] Key generation scripts
- [ ] Environment variable setup
- [ ] Monitoring & alerts
- [ ] Runbooks for key rotation

---

## Testing Strategy

### Unit Tests
```bash
cd backend
pytest tests/unit/test_review_workflow.py
pytest tests/unit/test_defect_retest_rbac.py
pytest tests/unit/test_admin_permission_control.py
pytest tests/unit/test_api_key_service.py
pytest tests/unit/test_gateway_key_rotation.py
pytest tests/unit/test_products_telemetry.py
```

### Integration Tests
```bash
pytest tests/integration/test_defect_retest_flow.py
pytest tests/integration/test_api_key_endpoints.py
pytest tests/integration/test_admin_permission_enforcement.py
```

### E2E Test Scenarios
1. **Review Workflow** — Create case → request review → approve → re-review
2. **Defect Retest** — Open defect → mark ready → execute → verify
3. **API Key Lifecycle** — Create → use → rotate → revoke
4. **Gateway Key** — Deploy → verify → age check → rotate

---

## Summary

| Component | Files | LOC | Tests | Risk |
|-----------|-------|-----|-------|------|
| Review Workflow | 1 | ~60 | 8 | Low |
| Defect Retest RBAC | 1 | ~80 | 10 | Low |
| Products Telemetry | 1 | ~150 | 6 | Medium (DB queries) |
| API Key Rotation | 4 | ~350 | 12 | Low |
| Admin Permission | 1 | ~100 | 8 | High (security) |
| Gateway Key Rotation | 1 | ~120 | 6 | High (security) |
| **Total** | **9** | **~860** | **50+** | **Medium** |

---

## Verification Checklist

- [ ] All 6 modules implemented and reviewed
- [ ] State machines documented with diagrams
- [ ] RBAC matrices validated
- [ ] Security controls in place (hashing, validation, grace periods)
- [ ] Database migration created and tested
- [ ] Router registry updated
- [ ] All unit tests passing (50+ tests)
- [ ] Integration tests passing
- [ ] E2E scenarios verified
- [ ] Documentation complete
- [ ] Deployment runbooks prepared

---

**Status:** Ready for code review → Testing → Integration → Deployment
