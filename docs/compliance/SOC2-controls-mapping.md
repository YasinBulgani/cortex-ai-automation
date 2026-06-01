# SOC 2 Type II Controls Mapping

**Product:** Cortex AI Automation  
**Trust Service Criteria:** Security (CC), Availability (A), Confidentiality (C)  
**Evidence Snapshot:** 2026-05-24  
**Branch:** `feature/qa-system-bootstrap`

---

## Common Criteria (CC) — Security

### CC1 — Control Environment

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| CC1.1 | COSO principles | Role-based access control (RBAC) with `viewer/editor/admin` roles | `backend/app/core/rbac.py` | ✅ Implemented |
| CC1.2 | Board oversight | Security ADRs and architecture review process | `docs/adr/` | ✅ Documented |
| CC1.3 | Organizational structure | Domain-driven design with bounded contexts | `docs/adr/0003-ddd-bounded-contexts.md` | ✅ Documented |

### CC2 — Communication and Information

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| CC2.1 | Information quality | Pydantic schema validation on all API inputs | `backend/app/domains/*/schemas.py` | ✅ Implemented |
| CC2.2 | Internal communication | Audit log chain with HMAC-SHA256 integrity | `backend/app/domains/audit/chain.py` | ✅ Implemented |
| CC2.3 | External communication | TLS 1.3, HttpOnly cookies, HSTS headers | `backend/app/core/security_middleware.py` | ✅ Implemented |

### CC3 — Risk Assessment

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| CC3.1 | Risk identification | SAST scanning (semgrep), dependency vulnerability scan | `.github/workflows/security-sast.yml` | ✅ Implemented |
| CC3.2 | Risk analysis | Threat model documented in security ADRs | `docs/adr/0002-httponly-cookie-auth.md` | ✅ Documented |
| CC3.3 | Risk mitigation | MFA enforcement, session expiry, rate limiting | `backend/app/domains/auth/` | ✅ Implemented |

### CC6 — Logical and Physical Access Controls

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| CC6.1 | Logical access | JWT + refresh token auth, HttpOnly cookies | `backend/app/core/security.py` | ✅ Implemented |
| CC6.2 | New user access | Role-based onboarding, admin-only user creation | `backend/app/domains/auth/router.py` | ✅ Implemented |
| CC6.3 | Access removal | User deactivation (`is_active=False`) | `backend/app/infra/models.py` | ✅ Implemented |
| CC6.6 | Logical access threats | TOTP MFA (RFC 6238), backup codes, brute-force protection | `backend/app/domains/auth/mfa_service.py` | ✅ Implemented |
| CC6.7 | Data transmission | TLS 1.3 in transit, AES-256-GCM at rest | `backend/app/core/` | ✅ Implemented |
| CC6.8 | Malicious software | Input validation, no eval(), parameterized queries | `backend/app/` (all endpoints) | ✅ Implemented |

### CC7 — System Operations

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| CC7.1 | Vulnerability detection | Automated SAST, dependency scanning | `.github/workflows/` | ✅ Implemented |
| CC7.2 | Anomaly monitoring | Audit event logging for all sensitive actions | `backend/app/domains/audit/service.py` | ✅ Implemented |
| CC7.3 | Incident evaluation | Audit chain integrity verification | `backend/app/domains/audit/chain.py` | ✅ Implemented |
| CC7.4 | Incident response | 72h notification SLA, breach logging | `docs/compliance/DPA-template-EN.md` | ✅ Documented |
| CC7.5 | Recovery | DB migration rollback procedures | `backend/alembic/` | ✅ Implemented |

### CC8 — Change Management

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| CC8.1 | Infrastructure changes | Alembic versioned migrations, ADRs for arch decisions | `backend/alembic/versions/`, `docs/adr/` | ✅ Implemented |

### CC9 — Risk Mitigation

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| CC9.1 | Vendor risk | Sub-processor list in DPA, AWS compliance certs | `docs/compliance/DPA-template-EN.md` | ✅ Documented |
| CC9.2 | Business disruption | Row-Level Security, multi-tenant isolation | `docs/adr/0007-test-management-rls-strategy.md` | ✅ Implemented |

---

## Availability (A)

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| A1.1 | Performance monitoring | Health check endpoints (`/health`, `/automation-suite/health`) | `backend/app/domains/automation/` | ✅ Implemented |
| A1.2 | Environmental threats | DB connection pooling, retry logic | `backend/app/infra/database.py` | ✅ Implemented |
| A1.3 | Recovery time | Alembic migration rollback | `backend/alembic/` | ✅ Implemented |

---

## Confidentiality (C)

| Control ID | Criterion | Implementation | Evidence Location | Status |
|---|---|---|---|---|
| C1.1 | Confidential information | RLS policies per tenant/project | `backend/alembic/versions/20260524_0003*` | ✅ Implemented |
| C1.2 | Disposal | User deletion API, backup purge procedure | `backend/app/domains/auth/router.py` | ✅ Implemented |

---

## Audit Log Export Procedures

For SOC 2 audit evidence collection, use the following API endpoints:

### 1. Full Export (JSON)
```bash
curl -H "Authorization: Bearer <admin-token>" \
  "https://your-instance/api/v1/audit/export/json?date_from=2026-01-01T00:00:00Z&date_to=2026-12-31T23:59:59Z" \
  -o cortex_audit_2026.json
```

### 2. Filtered CSV Export
```bash
curl -H "Authorization: Bearer <admin-token>" \
  "https://your-instance/api/v1/audit/export/csv?resource_type=user&date_from=2026-01-01Z" \
  -o cortex_audit_user_events.csv
```

### 3. Export Summary (event count)
```bash
curl -H "Authorization: Bearer <admin-token>" \
  "https://your-instance/api/v1/audit/export/summary?date_from=2026-01-01Z"
```

### Audit Event Schema
Each exported event includes:
- `id` — UUID
- `ts` — ISO 8601 timestamp
- `actor_email` / `actor_name` — human-readable identity
- `action` — event type (e.g., `user.login`, `mfa.enabled`, `test_run.created`)
- `resource_type` / `resource_id` — affected resource
- `ip` — client IP address
- `seq` — sequence number in hash chain
- `prev_hash` / `hash` — HMAC-SHA256 chain for tamper evidence

---

## Evidence Collection Checklist (Annual SOC 2 Review)

- [ ] Export full audit log for review period (`GET /audit/export/json`)
- [ ] Verify hash chain integrity (all `hash` values match HMAC of prior + event)
- [ ] Export user access list (admin panel → user management)
- [ ] Confirm MFA adoption rate (>80% of users should have MFA enabled)
- [ ] Review access removal events (`action=user.deactivated`)
- [ ] Confirm sub-processor DPAs are current (`docs/compliance/DPA-template-EN.md`)
- [ ] Review security scanning results (`docs/semgrep-secrets-runbook.md`)
- [ ] Confirm TLS certificate validity
- [ ] Review failed login attempts (audit events with `action=auth.login_failed`)
- [ ] Verify RLS policies are active (`backend/alembic/versions/20260524_0003*`)

---

*Prepared for internal audit readiness. Engage a qualified SOC 2 auditor for formal Type II certification.*
