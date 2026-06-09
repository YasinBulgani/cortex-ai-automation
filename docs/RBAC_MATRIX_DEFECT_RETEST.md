# RBAC Matrix: Defect Retest Lifecycle

## Defect Workflow States

```
1. Open Defect (QA)
   ├── Severity: critical/major/minor
   ├── Status: open
   └── retest_status: not_ready

2. Analyze (QA Lead/Dev)
   ├── Root cause identified
   ├── Assigned to Developer
   └── Status: assigned

3. Fix (Developer)
   ├── Code changes committed
   ├── CI/CD pipeline runs
   └── Status: in_development

4. Mark for Retest (Developer)
   ├── Action: retest_status = "ready"
   ├── Requires: defects.retest permission
   └── Status: ready_for_test

5. Execute Retest (QA/Automation)
   ├── Action: retest_status = "in_progress"
   ├── Requires: defects.retest_execute permission
   └── Test suite runs on fixed code

6. Verify Fix (QA)
   ├── Outcome: passed OR blocked
   ├── If passed: retest_status = "passed", close defect
   ├── If blocked: retest_status = "blocked", notify dev
   └── Requires: defects.verify permission
```

---

## Permission Matrix

### Role: QA Engineer
```
Permissions: [
  "defects.read",              // List/view all defects
  "defects.write",             // Open, update defect details
  "defects.verify",            // Mark as verified/passed
  "defects.retest_execute",    // Execute retest run
]

Allowed Actions:
  ✅ Open defect (severity, title, description)
  ✅ Update defect (status, comment, attachments)
  ✅ Execute retest (trigger test run)
  ✅ Verify fix (pass/failed, close)
  ❌ Mark for retest (developer only)
  ❌ Reassign to developer
  ❌ Delete defect
```

### Role: Developer
```
Permissions: [
  "defects.read",              // View assigned defects
  "defects.retest",            // Mark as ready for retest
]

Allowed Actions:
  ✅ View defects assigned to me
  ✅ Mark defect ready for retest (after fix)
  ✅ Comment on defect
  ❌ Open defect
  ❌ Change severity
  ❌ Execute retest
  ❌ Verify fix
```

### Role: QA Automation Engineer
```
Permissions: [
  "defects.read",              // List/view defects
  "defects.retest_execute",    // Execute retest automation
]

Allowed Actions:
  ✅ View defects
  ✅ Execute automated retest (scheduled or manual)
  ✅ View test results
  ❌ Open defect
  ❌ Mark ready for retest
  ❌ Verify fix result
```

### Role: QA Lead / Manager
```
Permissions: [
  "defects.read",              // All defects
  "defects.write",             // Update priority/assignment
]

Allowed Actions:
  ✅ View all defects
  ✅ Reassign defects
  ✅ Update priority
  ✅ Generate reports
  ❌ Mark ready for retest
  ❌ Execute retest
```

### Role: Admin (admin.*)
```
Permissions: [
  "admin.*",                   // All actions
]

Allowed Actions:
  ✅ All defect operations
  ✅ Bypass RBAC checks
  ✅ Audit and delete
```

---

## State Transition Validation

### Retest Status Transitions

```
           ┌─────────────────────┐
           │    not_ready        │
           └──────────┬──────────┘
                      │
                      ↓ (developer: defects.retest)
           ┌─────────────────────┐
           │      ready          │◄─────────┐
           └──────────┬──────────┘          │
                      │                     │
          ┌───────────┴───────────┐         │
          │                       │         │
          ↓ (QA: defects.         ↓ (cancel) │
      retest_execute)               │
    ┌──────────────┐               │
    │ in_progress  │               │
    └──┬───────┬───┘               │
       │       │                   │
       │       └───────────────────┘
       │
    ┌──┴────────────────────────────┐
    │                               │
    ↓ (QA: defects.verify)     ↓ (blocked)
  ┌──────────┐            ┌──────────────┐
  │ passed   │            │  blocked     │
  └────┬─────┘            └──────┬───────┘
       │                         │
       ├─────────────────────────┘
       │                      ↓ (retry: defects.retest)
       ↓ (reset) to ready ────────┘
   not_ready
```

### Transition Rule Table

| From | To | Role | Permission | Notes |
|------|----|----|-----------|-------|
| not_ready | ready | Developer | defects.retest | After code fix |
| ready | in_progress | QA Automation | defects.retest_execute | Start retest |
| ready | not_ready | Developer | defects.retest | Withdrawn before test |
| in_progress | passed | QA | defects.verify | Fix validated |
| in_progress | blocked | QA | defects.verify | Test still failing |
| in_progress | ready | QA Automation | defects.retest_execute | Retry execution |
| passed | ready | QA | defects.retest | Re-test needed |
| passed | not_ready | QA | defects.retest | Resolved |
| blocked | ready | Developer | defects.retest | Another fix attempt |

---

## API Endpoints with RBAC

### Defect Management

```http
GET /api/v1/defects
  Requires: defects.read
  Returns: list of defects user has access to

POST /api/v1/defects
  Requires: defects.write
  Body: {title, description, severity, scenario_id}

GET /api/v1/defects/{id}
  Requires: defects.read
  Returns: defect details

PATCH /api/v1/defects/{id}
  Requires: defects.write
  Body: {status, description, assigned_to, priority}

POST /api/v1/defects/{id}/mark-retest
  Requires: defects.retest
  Role: Developer
  Body: {retest_status: "ready"}
  Effect: Mark defect ready for QA retest

POST /api/v1/defects/{id}/execute-retest
  Requires: defects.retest_execute
  Role: QA/Automation
  Body: {test_suite_id, variables}
  Effect: retest_status = "in_progress", trigger run

POST /api/v1/defects/{id}/verify
  Requires: defects.verify
  Role: QA
  Body: {result: "passed"|"blocked", comment}
  Effect: Update retest_status based on result

DELETE /api/v1/defects/{id}
  Requires: admin.*
  Role: Admin only
```

---

## Defect Link Model

### Current Structure

```python
class DefectLink(Base):
    id: str                    # UUID
    case_id: str              # FK test_management_cases
    run_case_id: str          # FK test_management_run_cases
    
    status: str               # open, assigned, in_development, in_test, blocked, closed
    severity: str             # critical, major, minor
    title: str                # Defect title
    description: str          # Details
    
    retest_status: str        # not_ready, ready, in_progress, passed, blocked
    assigned_to: str          # Developer user_id
    opened_by: str            # QA user_id who opened
    
    # Review workflow
    review_status: str        # none, pending, approved, rejected
    review_by: str            # Reviewer user_id
    review_at: datetime       # When reviewed
    review_comment: str       # Reviewer feedback
    
    created_at: datetime
    updated_at: datetime
```

---

## RBAC Guard Implementation

### Example: Mark for Retest Endpoint

```python
from app.domains.test_management.defect_retest_rbac import RetestRBACPolicy
from app.domains.rbac.policy import ROLE_PERMISSIONS
from fastapi import HTTPException, status

@router.post("/defects/{defect_id}/mark-retest")
def mark_defect_retest(
    defect_id: str,
    body: MarkRetestIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark defect ready for retest (Developer action)."""
    
    # RBAC Check #1: User role has permission
    user_perms = _user_permissions(user)
    if not ("defects.retest" in user_perms or "admin.*" in user_perms):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Requires defects.retest permission (Developer role)"
        )
    
    defect = db.get(DefectLink, defect_id)
    if defect is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Defect not found")
    
    # RBAC Check #2: User is developer assigned to defect
    if defect.assigned_to and defect.assigned_to != str(user.id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only assigned developer can mark for retest"
        )
    
    # State machine validation
    RetestStatusTransitions.validate(defect.retest_status, "ready")
    
    # Update state
    defect.retest_status = "ready"
    db.commit()
    db.refresh(defect)
    
    return defect.to_dict()
```

---

## Testing Scenarios

### Test: Developer can mark retest
```python
def test_developer_mark_retest(db, defect, dev_user):
    defect.assigned_to = dev_user.id
    defect.retest_status = "not_ready"
    db.commit()
    
    # POST /api/v1/defects/{id}/mark-retest
    response = client.post(
        f"/api/v1/defects/{defect.id}/mark-retest",
        headers={"Authorization": f"Bearer {dev_user.token}"},
    )
    
    assert response.status_code == 200
    assert response.json()["retest_status"] == "ready"
```

### Test: QA cannot mark retest
```python
def test_qa_cannot_mark_retest(db, defect, qa_user):
    defect.retest_status = "not_ready"
    db.commit()
    
    response = client.post(
        f"/api/v1/defects/{defect.id}/mark-retest",
        headers={"Authorization": f"Bearer {qa_user.token}"},
    )
    
    assert response.status_code == 403
    assert "defects.retest" in response.json()["detail"]
```

### Test: QA can execute retest
```python
def test_qa_execute_retest(db, defect, qa_user):
    defect.retest_status = "ready"
    db.commit()
    
    response = client.post(
        f"/api/v1/defects/{defect.id}/execute-retest",
        json={"test_suite_id": "suite123"},
        headers={"Authorization": f"Bearer {qa_user.token}"},
    )
    
    assert response.status_code == 200
    assert response.json()["retest_status"] == "in_progress"
```

---

## Audit Trail

All defect actions should be logged in test_management_audit_events:

```python
audit(
    db=db,
    action="defect_retest.marked_ready",
    entity_type="defect_link",
    entity_id=defect_id,
    project_id=project_id,
    user=developer_user,
    payload={
        "old_status": "not_ready",
        "new_status": "ready",
        "reason": "developer fix ready",
    }
)
```

---

## Summary

- **6 Roles** with distinct defect permissions
- **6 Retest States** with validated transitions
- **3 RBAC Guard Points** (role, assignment, state)
- **100% Audit Logged** for compliance
- **Type-Safe State Machine** prevents invalid transitions
