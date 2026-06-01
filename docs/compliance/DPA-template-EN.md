# Data Processing Agreement (DPA) — Template

**Document Type:** Data Processing Agreement (DPA) — English Template  
**Version:** 1.0  
**Applicable Law:** GDPR Article 28 / KVKK Article 12  
**Last Updated:** 2026-05-24

---

## 1. Parties

| Party | Role | Description |
|---|---|---|
| **Data Controller** | Controller | Customer organization using the Cortex AI Automation platform |
| **Data Processor** | Processor | Company providing the Cortex AI Automation service |

---

## 2. Purpose

This Agreement sets out the terms governing the processing of personal data by the Data Processor on behalf of the Data Controller in connection with the use of the Cortex AI Automation platform ("the Service").

---

## 3. Personal Data Processed

### 3.1 Data Categories

| Category | Examples | Retention Period |
|---|---|---|
| Identity Data | Name, email address, user ID | Account active + 90 days |
| Access Data | IP address, session tokens, browser fingerprint | 30 days |
| Transaction Data | Test run history, action logs | 365 days |
| Security Data | MFA status, login attempts, audit trail | 730 days (regulatory requirement) |
| Content Data | Test scenarios, configuration files | Account deletion + 30 days |

### 3.2 Special Category Data

The platform does not process special category personal data as defined under GDPR Article 9.

### 3.3 Data Subjects

- Customer employees (platform users)
- Project managers and QA engineers
- Auditor-role users (read-only access)

---

## 4. Processing Purposes and Legal Basis

| Purpose | Legal Basis (GDPR) | Legal Basis (KVKK) |
|---|---|---|
| Service delivery | Article 6(1)(b) — performance of contract | Article 5/1(c) |
| Security and authentication | Article 6(1)(f) — legitimate interests | Article 5/1(ç) |
| Audit record keeping | Article 6(1)(c) — legal obligation | Article 5/1(ç) |
| Service improvement (anonymized) | Article 6(1)(f) — legitimate interests | Article 5/1(ç) |

---

## 5. Obligations of the Data Processor

### 5.1 Technical and Organisational Measures

The Data Processor implements and maintains the following security measures:

**Technical Measures:**
- [ ] AES-256-GCM encryption at rest
- [ ] TLS 1.3 encryption in transit
- [ ] TOTP-based multi-factor authentication (RFC 6238)
- [ ] Row-Level Security (RLS) for multi-tenant data isolation
- [ ] HMAC-SHA256 integrity chain for tamper-evident audit logs
- [ ] Regular vulnerability scanning (SAST/DAST)
- [ ] Automated session management and token expiry

**Organisational Measures:**
- [ ] Least-privilege access control (role-based)
- [ ] Staff confidentiality agreements
- [ ] Annual security awareness training
- [ ] Incident response procedure (max. 72-hour notification SLA)

### 5.2 Sub-processors

| Sub-processor | Service | Country | Safeguards |
|---|---|---|---|
| AWS (Amazon Web Services) | Infrastructure hosting | EU (Frankfurt) | AWS DPA, SCCs |
| PostgreSQL (self-hosted) | Database | Customer infrastructure | — |
| Anthropic API | AI model (optional) | USA | Anthropic DPA |

> **Note:** The Data Controller will be notified at least 30 days before any changes to sub-processors.

### 5.3 International Transfers

For transfers outside the EEA:
- EU Standard Contractual Clauses (SCCs) are applied
- For transfers to Turkey: KVKK Article 9 adequacy decision or explicit consent

---

## 6. Data Subject Rights Assistance

The Data Processor shall assist the Data Controller in responding to data subject requests:

| Right | Support Mechanism | SLA |
|---|---|---|
| Right of access | Admin panel → user report export | 5 business days |
| Right to rectification | Admin panel → profile update | Immediate |
| Right to erasure | Admin panel → account deletion API | 30 days (including backup purge) |
| Data portability | Audit log JSON/CSV export endpoint | 5 business days |
| Right to restriction | User account deactivation | Immediate |

---

## 7. Personal Data Breach Notification

Upon detection of a personal data breach:

1. **Within 24 hours:** Internal incident record created
2. **Within 72 hours:** Data Controller notified in writing
3. **Notification content:** Breach type, affected data categories, measures taken, recommendations
4. **Audit trail:** All breaches logged in `sd_audit_events` with `action=security.breach`

---

## 8. Audit Rights

The Data Controller has the right, upon 30 days' written notice, to:
- Request audit log exports (`GET /api/v1/audit/export/json` or `/csv`)
- Review security documentation and certifications
- Request third-party penetration test reports

---

## 9. Term and Termination

- This Agreement enters into force with the Master Service Agreement (MSA)
- Upon termination, data will be returned or securely deleted within 30 days
- Certificate of destruction provided upon request

---

## 10. Governing Law

- For controllers in the EU: **GDPR** and applicable member state law
- For controllers in Türkiye: **KVKK (Law No. 6698)** and Turkish law
- Disputes: [To be specified by the parties]

---

## 11. Signatures

| | Data Controller | Data Processor |
|---|---|---|
| Organization | `________________________` | Cortex AI Automation |
| Authorized Signatory | `________________________` | `________________________` |
| Title | `________________________` | `________________________` |
| Date | `________________________` | `________________________` |
| Signature | `________________________` | `________________________` |

---

*This template does not constitute legal advice. Please consult your legal counsel before finalizing.*
